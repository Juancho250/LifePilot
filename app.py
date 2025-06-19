from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from flask_cors import CORS
from io import BytesIO
from xhtml2pdf import pisa
from collections import defaultdict
from decimal import Decimal
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from google.generativeai import GenerativeModel, configure
from PIL import Image
import base64
import mimetypes
import google.generativeai as genai
import pymysql
import base64
import MySQLdb.cursors
import MySQLdb
import asyncio
import os

# Inicializar Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'd16f2bfa7491b82b8f9e30cf60eac02c82c648b1a93f7d9c671a3973d7eb69e5'

# Middleware
CORS(app)
csrf = CSRFProtect(app)

# Cargar entorno local si aplica
env = os.getenv("ENV", "local")
if env == "local":
    load_dotenv(".env.local")

# Configuración MySQL
app.config['MYSQL_HOST'] = os.environ.get("MYSQLHOST") or os.environ.get("DB_HOST")
app.config['MYSQL_USER'] = os.environ.get("MYSQLUSER") or os.environ.get("DB_USER")
app.config['MYSQL_PASSWORD'] = os.environ.get("MYSQLPASSWORD") or os.environ.get("DB_PASS")
app.config['MYSQL_DB'] = os.environ.get("MYSQLDATABASE") or os.environ.get("DB_NAME")
app.config['MYSQL_PORT'] = int(os.environ.get("MYSQLPORT") or os.environ.get("DB_PORT", 3306))

mysql = MySQL(app)

# Conexión pymysql adicional si es necesario
conn = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    port=app.config['MYSQL_PORT'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB']
)

print("✅ Conectado a la base de datos correctamente.")

# Configuración Gemini
genai.configure(api_key="AIzaSyDGCXwlcMTPtdBOKHwszEuuV4cFh-mfc18")
modelo = genai.GenerativeModel("gemini-1.5-flash")

# Filtro Jinja personalizado para JS
def escapejs_filter(value):
    if not isinstance(value, str):
        value = str(value)
    replacements = {
        '\\': '\\\\',
        '"': '\\"',
        "'": "\\'",
        '\n': '\\n',
        '\r': '\\r',
        '</': '<\\/'
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value

app.jinja_env.filters['escapejs'] = escapejs_filter




CARPETA_FOTOS = 'static/uploads'
if not os.path.exists(CARPETA_FOTOS):
    os.makedirs(CARPETA_FOTOS)
app.config['CARPETA_FOTOS'] = CARPETA_FOTOS
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def archivo_permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def inicio():
    return render_template('inicio.html')

@app.route('/registrarse', methods=['GET', 'POST'])
def registrarse():
    if request.method == 'POST':
        usuario = request.form['usuario']
        correo = request.form['correo']
        clave = generate_password_hash(request.form['clave'])
        foto = request.files.get('foto')
        nombre_foto = None

        if foto and archivo_permitido(foto.filename):
            filename_seguro = secure_filename(foto.filename)
            nombre_foto = f"{usuario}_{filename_seguro}"
            ruta_completa = os.path.join(app.config['CARPETA_FOTOS'], nombre_foto)
            foto.save(ruta_completa)

        # ✅ Definir cursor aquí
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO usuarios (nombre_usuario, correo_electronico, contraseña, foto) 
            VALUES (%s, %s, %s, %s)
        ''', (usuario, correo, clave, nombre_foto))
        mysql.connection.commit()
        cursor.close()

        flash('Usuario registrado con éxito. Ahora puedes iniciar sesión.')
        return redirect(url_for('iniciar_sesion'))

    return render_template('registrarse.html')


@app.route('/iniciar_sesion', methods=['GET', 'POST'])
def iniciar_sesion():
    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE nombre_usuario = %s', (usuario,))
        cuenta = cursor.fetchone()
        cursor.close()

        if cuenta and check_password_hash(cuenta['contraseña'], clave):
            session['logueado'] = True
            session['usuario_id'] = cuenta['id']
            session['usuario'] = cuenta['nombre_usuario']
            return redirect(url_for('panel'))
        else:
            flash('Nombre de usuario o contraseña incorrectos')

    return render_template('iniciar_sesion.html')





login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM usuarios WHERE id = %s', (user_id,))
    cuenta = cursor.fetchone()
    cursor.close()
    if cuenta:
        return Usuario(cuenta['id'], cuenta['nombre_usuario'])
    return None

@app.route('/panel')
def panel():
    if 'logueado' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT foto FROM usuarios WHERE id = %s', (session['usuario_id'],))
        resultado = cursor.fetchone()
        cursor.close()  # ✅ Siempre cerrar el cursor
        foto = resultado['foto'] if resultado and resultado['foto'] else None
        return render_template('panel.html', usuario=session['usuario'], usuario_foto=foto)

    return redirect(url_for('iniciar_sesion'))



#---------------------------------------#
#----Funciones de la seccion tareas-----#
#---------------------------------------#
# Mostrar y crear tareas
# Mostrar y crear tareas
@app.route('/tareas', methods=['GET', 'POST'])
def tareas():
    if 'logueado' not in session:
        return redirect(url_for('iniciar_sesion'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        titulo = request.form['titulo']
        estado = 'todo'
        fecha_limite = request.form.get('fecha_limite')
        usuario_id = session['usuario_id']

        # Insertar tarea asociada al usuario actual
        cursor.execute('''
            INSERT INTO tareas (titulo, estado, usuario_id, fecha_limite) 
            VALUES (%s, %s, %s, %s)
        ''', (titulo, estado, usuario_id, fecha_limite))

        mysql.connection.commit()

    # Obtener tareas del usuario actual
    cursor.execute('SELECT * FROM tareas WHERE usuario_id = %s', (session['usuario_id'],))
    tareas_usuario = cursor.fetchall()
    cursor.close()

    return render_template('tareas.html', usuario=session['usuario'], tareas=tareas_usuario)



@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    if 'logueado' not in session:
        return jsonify({'exito': False, 'error': 'No autorizado'})

    data = request.get_json()
    tarea_id = data.get('id')
    nuevo_estado = data.get('nuevo_estado')

    if not tarea_id or not nuevo_estado:
        return jsonify({'exito': False, 'error': 'Datos incompletos'})

    try:
        cursor = mysql.connection.cursor()
        cursor.execute('''
            UPDATE tareas 
            SET estado = %s 
            WHERE id = %s AND usuario_id = %s
        ''', (nuevo_estado, tarea_id, session['usuario_id']))
        mysql.connection.commit()
        actualizado = cursor.rowcount
        cursor.close()

        if actualizado == 0:
            return jsonify({'exito': False, 'error': 'Tarea no encontrada'})
        return jsonify({'exito': True})
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)})


@app.route('/actualizar_tarea', methods=['POST'])
def actualizar_tarea():
    if 'logueado' not in session:
        return jsonify({'exito': False, 'error': 'No autorizado'})

    data = request.get_json()
    tarea_id = data.get('id')
    nueva_fecha = data.get('nueva_fecha')

    if not tarea_id or not nueva_fecha:
        return jsonify({'exito': False, 'error': 'Datos incompletos'})

    try:
        cursor = mysql.connection.cursor()
        cursor.execute('''
            UPDATE tareas 
            SET fecha_limite = %s 
            WHERE id = %s AND usuario_id = %s
        ''', (nueva_fecha, tarea_id, session['usuario_id']))
        mysql.connection.commit()
        actualizado = cursor.rowcount
        cursor.close()

        if actualizado == 0:
            return jsonify({'exito': False, 'error': 'Tarea no encontrada'})
        return jsonify({'exito': True})
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)})



#---------------------------------------#
#----Funciones de la seccion movimientos-----#
#---------------------------------------#

def obtener_movimientos_mes_actual(usuario_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        hoy = datetime.today()
        primer_dia = hoy.replace(day=1).strftime('%Y-%m-%d')
        ultimo_dia = hoy.strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT * FROM movimientos
            WHERE usuario_id = %s AND fecha BETWEEN %s AND %s
            ORDER BY fecha DESC
        """, (usuario_id, primer_dia, ultimo_dia))

        movimientos = cursor.fetchall()
        return movimientos
    finally:
        cursor.close()




def formatear_fecha_humana(fecha):
    hoy = date.today()

    # Convertir string a date si es necesario
    if isinstance(fecha, str):
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    elif isinstance(fecha, datetime):
        fecha_obj = fecha.date()
    elif isinstance(fecha, date):
        fecha_obj = fecha
    else:
        raise ValueError("Tipo de fecha no soportado")

    if fecha_obj == hoy:
        return "Hoy"
    elif fecha_obj == hoy - timedelta(days=1):
        return "Ayer"
    elif 0 < (hoy - fecha_obj).days < 7:
        return fecha_obj.strftime("%A").capitalize()
    else:
        return fecha_obj.strftime("%d/%m/%Y")
    



@app.route('/movimientos', methods=['GET', 'POST'])
def movimientos():
    if 'logueado' not in session or 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    usuario_id = session['usuario_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        # 📸 Consultar la foto del usuario
        cursor.execute('SELECT foto FROM usuarios WHERE id = %s', (usuario_id,))
        resultado_foto = cursor.fetchone()
        usuario_foto = resultado_foto['foto'] if resultado_foto and resultado_foto['foto'] else None

        # POST: Registrar ingreso o gasto
        if request.method == 'POST':
            fecha = request.form['fecha']
            descripcion = request.form['descripcion']
            valor = Decimal(request.form['valor'])
            tipo = request.form['tipo']
            categoria_id = request.form.get('categoria_id') or None

            if tipo not in ['ingreso', 'gasto']:
                flash('Tipo de movimiento inválido para esta sección')
                return redirect(url_for('movimientos'))

            cursor.execute("""
                INSERT INTO movimientos (fecha, descripcion, valor, tipo, usuario_id, categoria_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (fecha, descripcion, valor, tipo, usuario_id, categoria_id))
            mysql.connection.commit()
            return redirect(url_for('movimientos'))

        # Calcular saldo actual
        cursor.execute("""
            SELECT COALESCE(SUM(
                CASE 
                    WHEN tipo = 'ingreso' THEN valor
                    WHEN tipo = 'gasto' THEN -valor
                    ELSE 0
                END
            ), 0) AS saldo
            FROM movimientos
            WHERE usuario_id = %s AND tipo IN ('ingreso', 'gasto')
        """, (usuario_id,))
        saldo_actual = cursor.fetchone()['saldo']

        # Cargar categorías del usuario
        cursor.execute("SELECT id, nombre, icono FROM categorias WHERE usuario_id = %s", (usuario_id,))
        categorias = cursor.fetchall()

        return render_template(
            'movimientos.html',
            saldo_actual=saldo_actual,
            categorias=categorias,
            usuario=session.get('usuario'),
            usuario_foto=usuario_foto
        )

    finally:
        cursor.close()






@app.route('/crear_categoria', methods=['POST'])
def crear_categoria():
    nombre = request.form.get('nombre')
    icono = request.form.get('icono')
    usuario_id = session.get('usuario_id')

    if not nombre or not icono or not usuario_id:
        return jsonify(success=False, message="Datos incompletos")

    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO categorias (nombre, icono, usuario_id) VALUES (%s, %s, %s)", 
                   (nombre, icono, usuario_id))
    mysql.connection.commit()
    categoria_id = cursor.lastrowid
    cursor.close()

    return jsonify(success=True, message="Categoría creada correctamente", categoria={
        "id": categoria_id,
        "nombre": nombre,
        "icono": icono
    })




@app.route('/prestamos/registrar', methods=['POST'])
def registrar_prestamo():
    if 'logueado' not in session or 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    usuario_id = session['usuario_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        fecha = request.form['fecha']
        frecuencia = request.form['frecuencia']
        persona = request.form['persona']
        descripcion = request.form['descripcion']
        valor = Decimal(request.form['valor'])
        estado = 'pendiente'
        fecha_creacion = datetime.now()

        cursor.execute("""
            INSERT INTO prestamos (descripcion, persona, usuario_id, monto_inicial, saldo, fecha, frecuencia, estado, fecha_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (descripcion, persona, usuario_id, valor, valor, fecha, frecuencia, estado, fecha_creacion))
        mysql.connection.commit()

    except Exception as e:
        # Aquí puedes loguear el error si quieres, o manejarlo
        pass

    finally:
        cursor.close()

    # Recoger filtros actuales para mantenerlos al recargar
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    ordenar = request.args.get('ordenar', 'fecha_desc')

    # Redirigir a movimientos con sección 'prestamos' y filtros
    return redirect(url_for('movimientos', 
                            seccion='prestamos', 
                            fecha_desde=fecha_desde, 
                            fecha_hasta=fecha_hasta, 
                            ordenar=ordenar
                            ))


@app.route('/prestamos/abonar', methods=['POST'])
def abonar_prestamo():
    if 'logueado' not in session:
        return redirect(url_for('iniciar_sesion'))

    prestamo_id = request.form['prestamo_id']
    monto_abono = Decimal(request.form['monto_abono'])

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        # Obtener saldo actual
        cursor.execute("SELECT saldo FROM prestamos WHERE id = %s AND usuario_id = %s", (prestamo_id, session['usuario_id']))
        prestamo = cursor.fetchone()

        if prestamo:
            nuevo_saldo = prestamo['saldo'] - monto_abono
            estado = 'pagado' if nuevo_saldo <= 0 else 'pendiente'

            cursor.execute("""
                UPDATE prestamos 
                SET saldo = %s, estado = %s 
                WHERE id = %s AND usuario_id = %s
            """, (max(nuevo_saldo, 0), estado, prestamo_id, session['usuario_id']))
            mysql.connection.commit()
    finally:
        cursor.close()

    return redirect(url_for('registros'))




@app.route('/deuda/registrar', methods=['GET', 'POST'])
def registrar_deuda():
    # código para registrar deuda
    return render_template('registrar_deuda.html')




#---------------------------------------#
#----Funciones de Registros-----#
#---------------------------------------#
@app.route('/registros')
def registros():
    if 'logueado' not in session or 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    usuario_id = session['usuario_id']
    mostrar_todo = request.args.get('ver_todo', '0') == '1'
    dias_mostrar = int(request.args.get('dias', 1)) if not mostrar_todo else 9999  # Muestra 1 día por defecto, o todos si ver_todo=1

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Movimientos
        cursor.execute("""
            SELECT m.*, c.nombre AS categoria_nombre, c.icono AS categoria_icono
            FROM movimientos m
            LEFT JOIN categorias c ON m.categoria_id = c.id
            WHERE m.usuario_id = %s
            ORDER BY m.fecha DESC
        """, (usuario_id,))
        movimientos = cursor.fetchall()

        # Préstamos
        cursor.execute("""
            SELECT id, fecha, descripcion, monto_inicial, estado, saldo
            FROM prestamos
            WHERE usuario_id = %s
            ORDER BY fecha DESC
        """, (usuario_id,))
        prestamos = cursor.fetchall()

        hoy = date.today()
        limite_fecha = hoy - timedelta(days=dias_mostrar - 1)

        # Agrupar movimientos por fecha legible
        movimientos_agrupados = defaultdict(list)
        for m in movimientos:
            fecha_obj = m['fecha']
            if isinstance(fecha_obj, datetime):
                fecha_obj = fecha_obj.date()
            if fecha_obj >= limite_fecha:
                fecha_legible = formatear_fecha_humana(fecha_obj)
                movimientos_agrupados[fecha_legible].append(m)

        # Agrupar préstamos por fecha legible
        prestamos_agrupados = defaultdict(list)
        for p in prestamos:
            fecha_obj = p['fecha']
            if isinstance(fecha_obj, datetime):
                fecha_obj = fecha_obj.date()
            if fecha_obj >= limite_fecha:
                fecha_legible = formatear_fecha_humana(fecha_obj)
                prestamos_agrupados[fecha_legible].append(p)

        # ¿Hay más elementos fuera del rango de fecha?
        hay_mas_mov = any(
            (m['fecha'].date() if isinstance(m['fecha'], datetime) else m['fecha']) < limite_fecha
            for m in movimientos
        )
        hay_mas_prest = any(
            (p['fecha'].date() if isinstance(p['fecha'], datetime) else p['fecha']) < limite_fecha
            for p in prestamos
        )

        seccion = request.args.get('seccion', 'ingresos')  # valores: 'ingresos' o 'prestamos'

        return render_template(
            'registros.html',
            movimientos_agrupados=movimientos_agrupados,
            prestamos_agrupados=prestamos_agrupados,
            mostrar_todo=mostrar_todo,
            dias_mostrar=dias_mostrar,
            mostrar_mas_movimientos=hay_mas_mov,
            mostrar_mas_prestamos=hay_mas_prest,
            seccion=seccion
        )

    finally:
        cursor.close()



@app.route('/exportar_pdf', methods=['GET'])
def exportar_pdf():
    if 'logueado' not in session:
        return redirect(url_for('iniciar_sesion'))

    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    ordenar = request.args.get('ordenar')
    seccion = request.args.get('seccion', 'deudas')
    usuario_id = session['usuario_id']

    # Construir consulta SQL con filtros y seccion
    query = '''
        SELECT * FROM movimientos
        WHERE usuario_id = %s
    '''
    params = [usuario_id]

    if fecha_desde:
        query += ' AND fecha >= %s'
        params.append(fecha_desde)
    if fecha_hasta:
        query += ' AND fecha <= %s'
        params.append(fecha_hasta)

    if seccion == 'ingresos':
        query += " AND tipo IN ('ingreso', 'gasto')"
    else:
        query += " AND tipo IN ('deuda', 'a_recibir', 'abono_a_recibir', 'abono_deuda')"

    if ordenar == 'fecha_asc':
        query += ' ORDER BY fecha ASC'
    elif ordenar == 'fecha_desc':
        query += ' ORDER BY fecha DESC'
    elif ordenar == 'valor_asc':
        query += ' ORDER BY valor ASC'
    elif ordenar == 'valor_desc':
        query += ' ORDER BY valor DESC'

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query, tuple(params))
    movimientos = cursor.fetchall()
    cursor.close()

    # Leer logo y convertir a base64
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
    with open(logo_path, 'rb') as image_file:
        logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')

    rendered_html = render_template('pdf_movimientos.html',
                                    movimientos=movimientos,
                                    seccion=seccion,
                                    logo_base64=logo_base64)

    pdf_output = BytesIO()
    pisa_status = pisa.CreatePDF(rendered_html, dest=pdf_output)

    if pisa_status.err:
        return f"Error al generar PDF: {pisa_status.err}"

    pdf_output.seek(0)

    return send_file(pdf_output,
                     as_attachment=True,
                     download_name='movimientos_filtrados.pdf',
                     mimetype='application/pdf')




@app.route('/certificado_prestamo/<int:movimiento_id>')
def certificado_prestamo(movimiento_id):
    if 'logueado' not in session:
        return redirect(url_for('iniciar_sesion'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Obtenemos el préstamo
    cursor.execute("SELECT * FROM prestamos WHERE id = %s", [movimiento_id])
    prestamo = cursor.fetchone()
    cursor.close()

    if not prestamo or prestamo['usuario_id'] != session['usuario_id']:
        return "No autorizado", 403

    # Obtenemos info del prestamista
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT nombre_usuario FROM usuarios WHERE id = %s", [prestamo['usuario_id']])
    prestamista = cursor.fetchone()
    cursor.close()

    # Renderizar HTML
    rendered_html = render_template(
        'certificado_prestamo.html',
        movimiento=prestamo,
        prestamista=prestamista,
        usuario_nombre=session.get('usuario'),  # quien lo solicita
        ahora=datetime.now()
    )

    # Generar PDF
    pdf_output = BytesIO()
    pisa_status = pisa.CreatePDF(rendered_html, dest=pdf_output)

    if pisa_status.err:
        return f"Error al generar PDF: {pisa_status.err}"

    pdf_output.seek(0)

    # Elegir nombre del archivo dinámicamente
    nombre_archivo = 'paz_y_salvo_deuda.pdf' if prestamo['saldo'] == 0 else 'certificado_prestamo.pdf'

    return send_file(
        pdf_output,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype='application/pdf'
    )



#---------------------------------------#
#----Funciones de la seccion Cartera-----#
#---------------------------------------#


def generar_url_wompi(monto, referencia):
    monto_centavos = int(Decimal(monto) * 100)

    return f"https://checkout.wompi.co/p/?public-key={os.environ['WOMPI_PUBLIC_KEY']}&currency=COP&amount-in-cents={monto_centavos}&reference={referencia}&redirect-url=https://tusitio.com/confirmacion_wompi"


@app.route('/cartera')
def cartera():
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT saldo_wallet FROM usuarios WHERE id=%s", (session['usuario_id'],))
    saldo = cur.fetchone()['saldo_wallet']
    cur.close()
    return render_template('cartera.html', saldo=saldo)



@app.route('/iniciar_paypal', methods=['POST'])
def iniciar_paypal():
    usuario_id = session.get('usuario_id')
    monto = request.form.get('monto')
    if not usuario_id or not monto:
        flash("Usuario o monto faltante", "danger")
        return redirect(url_for('cartera'))

    # Crear orden con PayPal (simulado o real)
    transaccion_id = f"PAYPAL-{usuario_id}-{int(datetime.now().timestamp())}"

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO recargas (usuario_id, metodo, transaccion_id, monto)
        VALUES (%s,'paypal',%s,%s)
    """, (usuario_id, transaccion_id, monto))
    mysql.connection.commit()
    cur.close()

    return render_template('paypal_checkout.html', transaccion_id=transaccion_id, monto=monto)




@app.route('/procesar_pago_paypal', methods=['POST'])
def procesar_pago_paypal():
    # No uses Flask-WTF aquí, CSRF se usa solo en formularios HTML
    data = request.get_json()
    txid = data['orderID']
    payer = data['payerID']
    monto = data['monto']
    usuario_id = session.get('usuario_id')

    if not usuario_id:
        return jsonify(status='error', message='Sesión no válida'), 401

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE recargas
        SET estado='exitosa'
        WHERE transaccion_id=%s
    """, (txid,))
    
    cur.execute("""
        INSERT INTO wallet_movimientos(usuario_id, referencia_externa, monto, tipo, estado, descripcion, medio_pago)
        VALUES (%s, %s, %s, 'recarga', 'completado', 'Recarga PayPal', 'paypal')
    """, (usuario_id, txid, monto))

    cur.execute("""
        UPDATE usuarios
        SET saldo_wallet = saldo_wallet + %s
        WHERE id = %s
    """, (monto, usuario_id))

    mysql.connection.commit()
    cur.close()

    return jsonify(status='ok')




@app.route('/iniciar_wompi', methods=['POST'])
def iniciar_wompi():
    usuario_id = session.get('usuario_id')
    monto = Decimal(request.form.get('monto'))
    referencia = f"WOMPI-{usuario_id}-{int(datetime.utcnow().timestamp())}"
    
    url_pago = generar_url_wompi(monto, referencia)

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO recargas (usuario_id, metodo, transaccion_id, monto)
        VALUES (%s,'wompi',%s,%s)
    """, (usuario_id, referencia, monto))
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_pago)




@app.route('/webhook_wompi', methods=['POST'])
def webhook_wompi():
    tx = request.get_json()['data']['transaction']
    referencia = tx['reference']; estado = tx['status']
    monto = Decimal(tx['amount_in_cents'])/100
    
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE recargas SET estado=%s WHERE transaccion_id=%s
    """, ('exitosa' if estado=='APPROVED' else 'fallida', referencia))

    if estado == 'APPROVED':
        cur.execute("""
            INSERT IGNORE INTO wallet_movimientos(usuario_id, referencia_externa, monto, tipo, estado, descripcion, medio_pago)
            SELECT usuario_id, transaccion_id, %s, 'recarga', 'completado', 'Recarga Wompi', 'wompi'
            FROM recargas WHERE transaccion_id=%s
        """, (monto, referencia))
        cur.execute("""
            UPDATE usuarios u JOIN recargas r 
            ON u.id=r.usuario_id
            SET u.saldo_wallet=u.saldo_wallet + %s 
            WHERE r.transaccion_id=%s
        """, (monto, referencia))

    mysql.connection.commit()
    cur.close()
    return '', 200



@app.route('/confirmacion_wompi')
def confirmacion_wompi():
    flash("Tu recarga ha sido procesada. Revisa tu saldo.", "success")
    return redirect(url_for('cartera'))








#---------------------------------------#
#----Funciones de la seccion Cerrar sesion-----#
#---------------------------------------#
@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    return redirect(url_for('inicio'))




#---------------------------------------#
#----Funciones de la seccion Ideas-----#
#---------------------------------------#
@app.route("/ideas", methods=["GET", "POST"])
def ideas():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        categoria = request.form.get("categoria", "")

        cursor.execute(
            "INSERT INTO ideas (titulo, descripcion, categoria) VALUES (%s, %s, %s)",
            [titulo, descripcion, categoria]
        )
        mysql.connection.commit()
        flash("Idea registrada con éxito", "success")
        return redirect(url_for("ideas"))

    cursor.execute("SELECT * FROM ideas ORDER BY fecha_creacion DESC")
    ideas = cursor.fetchall()
    return render_template("ideas.html", ideas=ideas)

@app.route("/eliminar_idea/<int:id>")
def eliminar_idea(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM ideas WHERE id = %s", [id])
    mysql.connection.commit()
    flash("Idea eliminada", "info")
    return redirect(url_for("ideas"))

@app.route("/editar_idea/<int:id>", methods=["GET", "POST"])
def editar_idea(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":
        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        categoria = request.form["categoria"]

        cursor.execute(
            "UPDATE ideas SET titulo = %s, descripcion = %s, categoria = %s WHERE id = %s",
            [titulo, descripcion, categoria, id]
        )
        mysql.connection.commit()
        flash("Idea actualizada", "success")
        return redirect(url_for("ideas"))

    cursor.execute("SELECT * FROM ideas WHERE id = %s", [id])
    idea = cursor.fetchone()
    return render_template("editar_idea.html", idea=idea)




#---------------------------------------#
#----Funciones de la seccion Asistente-----#
#---------------------------------------#
@app.route('/asistente')
def asistente():
    if not session.get('logueado'):
        return redirect(url_for('iniciar_sesion'))  # Protege el acceso

    nombre_usuario = session.get('usuario')  # Lo guardaste así en iniciar_sesion
    return render_template('asistente.html', nombre=nombre_usuario)




@app.route('/consultar', methods=['POST'])
def consultar():
    consulta_usuario = request.form.get('consulta', '')
    imagen = request.files.get('imagen', None)

    # Verifica y limpia historial incompatible
    if 'historial' in session:
        for parte in session['historial']:
            if 'role' in parte:
                session.pop('historial', None)
                break

    # Inicializa historial si no existe
    if 'historial' not in session:
        session['historial'] = [{"text": "Responde siempre en español."}]

    try:
        partes = session['historial'][:]  # Copia del historial actual

        if imagen:
            contenido = base64.b64encode(imagen.read()).decode("utf-8")
            tipo = imagen.mimetype.split("/")[-1]
            if tipo == "jpg":
                tipo = "jpeg"

            imagen_codificada = {
                "inline_data": {
                    "mime_type": f"image/{tipo}",
                    "data": contenido
                }
            }

            partes.append(imagen_codificada)

        partes.append({"text": consulta_usuario})

        # Consulta al modelo con historial completo
        respuesta = modelo.generate_content(partes)

        texto_respuesta = respuesta.text if hasattr(respuesta, 'text') else "No se obtuvo respuesta."

        # Guarda solo partes válidas
        session['historial'].append({"text": consulta_usuario})
        session['historial'].append({"text": texto_respuesta})

        return jsonify({"mensaje": texto_respuesta})

    except Exception as e:
        return jsonify({"mensaje": f"❌ Error: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)

