from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, current_app
from io import BytesIO
from xhtml2pdf import pisa
import base64
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import MySQLdb.cursors
from datetime import datetime
from collections import defaultdict
from decimal import Decimal

import os

app = Flask(__name__)

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

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'HnvPhkdaVeZ4pD'
app.config['MYSQL_DB'] = 'oryon_db'

mysql = MySQL(app)

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

        if cuenta and check_password_hash(cuenta['contraseña'], clave):
            session['logueado'] = True
            session['usuario_id'] = cuenta['id']  # ✅ Usa SIEMPRE 'usuario_id'
            session['usuario'] = cuenta['nombre_usuario']
            return redirect(url_for('panel'))  # o 'movimientos'
        else:
            flash('Nombre de usuario o contraseña incorrectos')

    return render_template('iniciar_sesion.html')


@app.route('/panel')
def panel():
    if 'logueado' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT foto FROM usuarios WHERE id = %s', (session['usuario_id'],))
        resultado = cursor.fetchone()
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
        cursor.execute('INSERT INTO tareas (titulo, estado, usuario_id, fecha_limite) VALUES (%s, %s, %s, %s)', 
                       (titulo, estado, usuario_id, fecha_limite))
        mysql.connection.commit()
        return redirect(url_for('tareas'))

    cursor.execute('SELECT * FROM tareas WHERE usuario_id = %s', (session['usuario_id'],))
    tareas_usuario = cursor.fetchall()
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
        cursor.close()

        if cursor.rowcount == 0:
            return jsonify({'exito': False, 'error': 'Tarea no encontrada'})

        return jsonify({'exito': True})
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)})




#---------------------------------------#
#----Funciones de la seccion movimientos-----#
#---------------------------------------#

def obtener_movimientos_mes_actual(usuario_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    hoy = datetime.today()
    primer_dia = hoy.replace(day=1).strftime('%Y-%m-%d')
    ultimo_dia = hoy.strftime('%Y-%m-%d')

    cursor.execute("""
        SELECT * FROM movimientos
        WHERE usuario_id = %s AND fecha BETWEEN %s AND %s
        ORDER BY fecha DESC
    """, (usuario_id, primer_dia, ultimo_dia))

    movimientos = cursor.fetchall()
    cursor.close()
    return movimientos


@app.route('/movimientos', methods=['GET', 'POST'])
def movimientos():
    if 'logueado' not in session or 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    usuario_id = session['usuario_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        if request.method == 'POST':
            fecha = request.form['fecha']
            descripcion = request.form['descripcion']
            valor = Decimal(request.form['valor'])
            tipo = request.form['tipo']
            deuda_id = request.form.get('deuda_id')

            if tipo in ['abono_deuda', 'abono_a_recibir']:
                if not deuda_id:
                    flash('Debes seleccionar una deuda o dinero a recibir para abonar')
                    return redirect(url_for('movimientos'))

                cursor.execute("""
                    SELECT saldo, tipo FROM deudas
                    WHERE id = %s AND usuario_id = %s
                """, (deuda_id, usuario_id))
                deuda = cursor.fetchone()
                if not deuda:
                    flash('Deuda o dinero a recibir no encontrado')
                    return redirect(url_for('movimientos'))

                if valor > deuda['saldo']:
                    flash('El abono no puede ser mayor que el saldo pendiente')
                    return redirect(url_for('movimientos'))

                # Insertar movimiento con deuda_id
                cursor.execute("""
                    INSERT INTO movimientos (fecha, descripcion, valor, tipo, usuario_id, deuda_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (fecha, descripcion, valor, tipo, usuario_id, deuda_id))

                # Actualizar saldo en tabla deudas restando abono
                nuevo_saldo = deuda['saldo'] - valor
                cursor.execute("""
                    UPDATE deudas SET saldo = %s WHERE id = %s AND usuario_id = %s
                """, (nuevo_saldo, deuda_id, usuario_id))

            elif tipo in ['deuda', 'a_recibir']:
                # Insertar nueva deuda sin modificar saldo extra
                cursor.execute("""
                    INSERT INTO deudas (descripcion, usuario_id, monto_inicial, saldo, tipo)
                    VALUES (%s, %s, %s, %s, %s)
                """, (descripcion, usuario_id, valor, valor, tipo))
                deuda_nueva_id = cursor.lastrowid

                # Insertar movimiento asociado con deuda_id recién creado
                cursor.execute("""
                    INSERT INTO movimientos (fecha, descripcion, valor, tipo, usuario_id, deuda_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (fecha, descripcion, valor, tipo, usuario_id, deuda_nueva_id))

            else:
                # Otros tipos, sin deuda_id
                cursor.execute("""
                    INSERT INTO movimientos (fecha, descripcion, valor, tipo, usuario_id, deuda_id)
                    VALUES (%s, %s, %s, %s, %s, NULL)
                """, (fecha, descripcion, valor, tipo, usuario_id))

            mysql.connection.commit()

            # Redirigir tras POST para evitar repost en refresh
            return redirect(url_for('movimientos'))

        # --- Código GET para mostrar movimientos y datos ---

                # --- Código GET para mostrar movimientos y datos ---

        # Filtros desde URL
        primer_dia = datetime.today().replace(day=1).strftime('%Y-%m-%d')
        hoy = datetime.today().strftime('%Y-%m-%d')

        fecha_desde = request.args.get('fecha_desde') or primer_dia
        fecha_hasta = request.args.get('fecha_hasta') or hoy
        ordenar = request.args.get('ordenar') or 'fecha_desc'
        seccion = request.args.get('seccion') or 'deudas'

        # Ordenamiento dinámico
        ordenes = {
            'fecha_desc': 'fecha DESC',
            'fecha_asc': 'fecha ASC',
            'valor_desc': 'valor DESC',
            'valor_asc': 'valor ASC',
        }
        orden_sql = ordenes.get(ordenar, 'fecha DESC')

        # Consulta de movimientos filtrada
        cursor.execute(f"""
            SELECT * FROM movimientos
            WHERE usuario_id = %s AND fecha BETWEEN %s AND %s
            ORDER BY {orden_sql}
        """, (usuario_id, fecha_desde, fecha_hasta))
        movimientos_list = cursor.fetchall()

        # Cargar deudas con saldo
        cursor.execute("""
            SELECT id, descripcion, saldo, tipo
            FROM deudas
            WHERE usuario_id = %s AND saldo > 0
        """, (usuario_id,))
        deudas_pendientes = cursor.fetchall()

        # Asociar saldo a movimientos si aplica
        for mov in movimientos_list:
            if mov['tipo'] in ['deuda', 'a_recibir']:
                deuda_rel = next((d for d in deudas_pendientes if d['id'] == mov.get('deuda_id')), None)
                mov['saldo'] = deuda_rel['saldo'] if deuda_rel else 0.00
            else:
                mov['saldo'] = None

        # Calcular saldo actual general
        cursor.execute("""
            SELECT 
                COALESCE(SUM(
                    CASE 
                        WHEN tipo IN ('ingreso', 'deuda', 'abono_a_recibir') THEN valor
                        WHEN tipo IN ('gasto', 'a_recibir', 'abono_deuda') THEN -valor
                        ELSE 0
                    END
                ), 0) AS saldo
            FROM movimientos
            WHERE usuario_id = %s
        """, (usuario_id,))
        saldo_actual = cursor.fetchone()['saldo']

        return render_template('movimientos.html',
                               movimientos=movimientos_list,
                               deudas=deudas_pendientes,
                               saldo_actual=saldo_actual,
                               fecha_desde=fecha_desde,
                               fecha_hasta=fecha_hasta,
                               ordenar=ordenar,
                               seccion=seccion)


    finally:
        cursor.close()



@app.route('/movimientos/editar/<int:movimiento_id>', methods=['POST'])
def editar_movimiento(movimiento_id):
    if 'logueado' not in session or 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    usuario_id = session['usuario_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM movimientos WHERE id=%s AND usuario_id=%s", (movimiento_id, usuario_id))
    mov_original = cursor.fetchone()
    if not mov_original:
        flash('Movimiento no encontrado o sin permiso para editar')
        cursor.close()
        return redirect(url_for('movimientos'))

    descripcion = request.form['descripcion']

    cursor.execute("""
        UPDATE movimientos
        SET descripcion = %s
        WHERE id = %s AND usuario_id = %s
    """, (descripcion, movimiento_id, usuario_id))

    mysql.connection.commit()
    cursor.close()

    flash('Descripción actualizada correctamente.')
    return redirect(url_for('movimientos'))




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
