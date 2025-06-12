from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, current_app
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
from io import BytesIO
from xhtml2pdf import pisa
from collections import defaultdict
from decimal import Decimal
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pymysql
import base64
import MySQLdb.cursors
import MySQLdb


import os

app = Flask(__name__)


# Configurar MySQL (Flask-MySQLdb)
app.config['MYSQL_HOST'] = os.environ.get("MYSQLHOST") or os.environ.get("DB_HOST")
app.config['MYSQL_USER'] = os.environ.get("MYSQLUSER") or os.environ.get("DB_USER")
app.config['MYSQL_PASSWORD'] = os.environ.get("MYSQLPASSWORD") or os.environ.get("DB_PASS")
app.config['MYSQL_DB'] = os.environ.get("MYSQLDATABASE") or os.environ.get("DB_NAME")
app.config['MYSQL_PORT'] = int(os.environ.get("MYSQLPORT") or os.environ.get("DB_PORT", 3306))

# Inicializar MySQL
mysql = MySQL(app)


# Filtro personalizado para escapar texto en JavaScript
def escapejs_filter(value):
    if not isinstance(value, str):
        value = str(value)
    replacements = {
        '\\': '\\\\',
        '"': '\\"',
        "'": "\\'",
        '\n': '\\n',
        '\r': '\\r',
        '</': '<\\/',
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value

# Registrar el filtro en Jinja2
app.jinja_env.filters['escapejs'] = escapejs_filter

app.config['SECRET_KEY'] = 'd16f2bfa7491b82b8f9e30cf60eac02c82c648b1a93f7d9c671a3973d7eb69e5'



# Carga el archivo .env.local si estás en local
env = os.getenv("ENV", "local")
if env == "local":
    load_dotenv(".env.local")  # solo carga localmente

# Conexión usando variables de entorno
conn = pymysql.connect(
    host=os.environ.get("MYSQLHOST") or os.environ.get("DB_HOST"),
    port=int(os.environ.get("MYSQLPORT") or os.environ.get("DB_PORT", 3306)),
    user=os.environ.get("MYSQLUSER") or os.environ.get("DB_USER"),
    password=os.environ.get("MYSQLPASSWORD") or os.environ.get("DB_PASS"),
    database=os.environ.get("MYSQLDATABASE") or os.environ.get("DB_NAME")
)


print("✅ Conectado a la base de datos correctamente.")


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

        # ✅ Definir cursor correctamente
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM usuarios WHERE nombre_usuario = %s', (usuario,))
        cuenta = cursor.fetchone()
        cursor.close()  # ✅ Cierra el cursor después de usarlo

        if cuenta and check_password_hash(cuenta['contraseña'], clave):
            session['logueado'] = True
            session['usuario_id'] = cuenta['id']  # ✅ Usa SIEMPRE 'usuario_id'
            session['usuario'] = cuenta['nombre_usuario']
            return redirect(url_for('panel'))
        else:
            flash('Nombre de usuario o contraseña incorrectos')

    return render_template('iniciar_sesion.html')



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

        cursor.execute('''
            INSERT INTO tareas (titulo, estado, usuario_id, fecha_limite) 
            VALUES (%s, %s, %s, %s)
''', (titulo, estado, usuario_id, fecha_limite))


        mysql.connection.commit()

    # Mostrar tareas
    cursor.execute('SELECT * FROM tareas WHERE usuario_id = %s', (session['usuario_id'],))
    tareas_usuario = cursor.fetchall()
    cursor.close()

    return render_template('tareas.html', usuario=session['usuario'], tareas=tareas_usuario)


#Actualizar tarea#
@app.route('/actualizar_tarea', methods=['POST'])
def actualizar_tarea():
    if 'logueado' not in session:
        return jsonify({'exito': False, 'error': 'No autorizado'})

    data = request.get_json()
    titulo = data.get('titulo')
    nueva_fecha = data.get('nueva_fecha')

    if not titulo or not nueva_fecha:
        return jsonify({'exito': False, 'error': 'Datos incompletos'})

    try:
        cursor = mysql.connection.cursor()
        cursor.execute('''
            UPDATE tareas 
            SET fecha_limite = %s 
            WHERE titulo = %s AND usuario_id = %s
        ''', (nueva_fecha, titulo, session['usuario_id']))
        mysql.connection.commit()
        modificado = cursor.rowcount
        cursor.close()

        if modificado == 0:
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

# Función para formatear fechas en formato legible
def formatear_fecha_humana(fecha_str):
    hoy = date.today()
    fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()

    if fecha_obj == hoy:
        return "Hoy"
    elif fecha_obj == hoy - timedelta(days=1):
        return "Ayer"
    else:
        return fecha_obj.strftime("%d/%m/%Y")




@app.route('/movimientos', methods=['GET', 'POST'])
def movimientos():
    if 'logueado' not in session or 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    usuario_id = session['usuario_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        # --------------------------------------------------------------------
        # POST: Registrar ingreso o gasto
        # --------------------------------------------------------------------
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
                INSERT INTO movimientos (fecha, descripcion, valor, tipo, usuario_id, categoria_id, deuda_id)
                VALUES (%s, %s, %s, %s, %s, %s, NULL)
            """, (fecha, descripcion, valor, tipo, usuario_id, categoria_id))
            mysql.connection.commit()
            return redirect(url_for('movimientos'))

        # --------------------------------------------------------------------
        # Filtros de fecha
        # --------------------------------------------------------------------
        hoy_date = datetime.today().date()
        primer_dia = hoy_date.replace(day=1).strftime('%Y-%m-%d')
        hoy_str = hoy_date.strftime('%Y-%m-%d')

        dia_param = request.args.get('dia', '').lower()
        dias_disponibles = {
            'hoy': hoy_date,
            'ayer': hoy_date - timedelta(days=1),
            'lunes': hoy_date - timedelta(days=hoy_date.weekday()),
            'martes': hoy_date - timedelta(days=hoy_date.weekday() - 1),
            'miércoles': hoy_date - timedelta(days=hoy_date.weekday() - 2),
            'jueves': hoy_date - timedelta(days=hoy_date.weekday() - 3),
            'viernes': hoy_date - timedelta(days=hoy_date.weekday() - 4),
            'sábado': hoy_date - timedelta(days=hoy_date.weekday() - 5),
            'domingo': hoy_date - timedelta(days=hoy_date.weekday() - 6),
        }

        if dia_param in dias_disponibles:
            fecha_desde = fecha_hasta = dias_disponibles[dia_param].strftime('%Y-%m-%d')
        else:
            fecha_desde = request.args.get('fecha_desde') or primer_dia
            fecha_hasta = request.args.get('fecha_hasta') or hoy_str

        # --------------------------------------------------------------------
        # Ordenamiento
        # --------------------------------------------------------------------
        ordenar = request.args.get('ordenar', 'fecha_desc')
        seccion = request.args.get('seccion', 'movimientos')

        ordenes = {
            'fecha_desc': 'm.fecha DESC',
            'fecha_asc': 'm.fecha ASC',
            'valor_desc': 'm.valor DESC',
            'valor_asc': 'm.valor ASC',
        }
        orden_sql = ordenes.get(ordenar, 'm.fecha DESC')

        # --------------------------------------------------------------------
        # Consultar movimientos con categoría
        # --------------------------------------------------------------------
        cursor.execute(f"""
            SELECT m.*, c.nombre AS categoria_nombre, c.icono AS categoria_icono
            FROM movimientos m
            LEFT JOIN categorias c ON m.categoria_id = c.id
            WHERE m.usuario_id = %s AND m.tipo IN ('ingreso', 'gasto')
              AND DATE(m.fecha) BETWEEN %s AND %s
            ORDER BY {orden_sql}
        """, (usuario_id, fecha_desde, fecha_hasta))
        movimientos_list = cursor.fetchall()

        # --------------------------------------------------------------------
        # Agrupar por fecha legible
        # --------------------------------------------------------------------
        movimientos_agrupados = defaultdict(list)
        for m in movimientos_list:
            fecha_obj = m['fecha']
            fecha_str = fecha_obj.strftime('%Y-%m-%d') if isinstance(fecha_obj, (datetime, date)) else m['fecha']
            fecha_legible = formatear_fecha_humana(fecha_str)
            movimientos_agrupados[fecha_legible].append(m)

        # --------------------------------------------------------------------
        # Calcular saldo
        # --------------------------------------------------------------------
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

        # --------------------------------------------------------------------
        # Cargar categorías del usuario
        # --------------------------------------------------------------------
        cursor.execute("SELECT id, nombre, icono FROM categorias WHERE usuario_id = %s", (usuario_id,))
        categorias = cursor.fetchall()

        # --------------------------------------------------------------------
        # Consultar préstamos (si aplica)
        # --------------------------------------------------------------------
        prestamos = []
        if seccion == 'prestamos':
            ordenes_prestamos = {
                'fecha_desc': 'fecha DESC',
                'fecha_asc': 'fecha ASC',
                'valor_desc': 'monto_inicial DESC',
                'valor_asc': 'monto_inicial ASC',
            }
            orden_prestamo_sql = ordenes_prestamos.get(ordenar, 'fecha DESC')

            cursor.execute(f"""
                SELECT id, descripcion, persona, monto_inicial, saldo, fecha, frecuencia, estado 
                FROM prestamos
                WHERE usuario_id = %s
                  AND DATE(fecha) BETWEEN %s AND %s
                ORDER BY {orden_prestamo_sql}
            """, (usuario_id, fecha_desde, fecha_hasta))
            prestamos = cursor.fetchall()

        return render_template(
            'movimientos.html',
            movimientos_agrupados=movimientos_agrupados,
            saldo_actual=saldo_actual,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            ordenar=ordenar,
            categorias=categorias,
            prestamos=prestamos,
            seccion=seccion,
            dia_actual=dia_param,
            usuario=session.get('usuario')
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

    return redirect(url_for('movimientos'))



@app.route('/deuda/registrar', methods=['GET', 'POST'])
def registrar_deuda():
    # código para registrar deuda
    return render_template('registrar_deuda.html')



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



@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    return redirect(url_for('inicio'))




    
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


if __name__ == '__main__':
    app.run(debug=True)
