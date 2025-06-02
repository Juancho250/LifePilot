from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import MySQLdb.cursors
from datetime import datetime
from collections import defaultdict
import os

app = Flask(__name__)
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
            session['id_usuario'] = cuenta['id']
            session['usuario'] = cuenta['nombre_usuario']
            return redirect(url_for('panel'))
        else:
            flash('Nombre de usuario o contraseña incorrectos')

    return render_template('iniciar_sesion.html')

@app.route('/panel')
def panel():
    if 'logueado' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT foto FROM usuarios WHERE id = %s', (session['id_usuario'],))
        resultado = cursor.fetchone()
        foto = resultado['foto'] if resultado and resultado['foto'] else None
        return render_template('panel.html', usuario=session['usuario'], usuario_foto=foto)
    return redirect(url_for('iniciar_sesion'))

@app.route('/tareas', methods=['GET', 'POST'])
def tareas():
    if 'logueado' not in session:
        return redirect(url_for('iniciar_sesion'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        titulo = request.form['titulo']
        estado = 'todo'
        fecha_limite = request.form.get('fecha_limite')
        id_usuario = session['id_usuario']
        cursor.execute('INSERT INTO tareas (titulo, estado, id_usuario, fecha_limite) VALUES (%s, %s, %s, %s)', 
                       (titulo, estado, id_usuario, fecha_limite))
        mysql.connection.commit()
        return redirect(url_for('tareas'))

    cursor.execute('SELECT * FROM tareas WHERE id_usuario = %s', (session['id_usuario'],))
    tareas_usuario = cursor.fetchall()
    return render_template('tareas.html', usuario=session['usuario'], tareas=tareas_usuario)

# Función para obtener gastos del mes actual
def obtener_gastos_mes_actual():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        hoy = datetime.today()
        primer_dia = hoy.replace(day=1)
        # Calcular el primer día del siguiente mes
        if hoy.month == 12:
            siguiente_mes = hoy.replace(year=hoy.year + 1, month=1, day=1)
        else:
            siguiente_mes = hoy.replace(month=hoy.month + 1, day=1)
        cursor.execute("""
            SELECT * FROM gastos 
            WHERE fecha >= %s AND fecha < %s
            ORDER BY fecha ASC
        """, (primer_dia, siguiente_mes))
        gastos = cursor.fetchall()
    finally:
        cursor.close()
    return gastos

# Ruta para registrar y mostrar gastos e ingresos
@app.route('/gastos', methods=['GET', 'POST'])
def gastos():
    if 'logueado' not in session:
        return redirect(url_for('iniciar_sesion'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        if request.method == 'POST':
            fecha = request.form['fecha']
            descripcion = request.form['descripcion']
            valor = float(request.form['valor'])
            tipo = request.form['tipo']
            cursor.execute("""
                INSERT INTO gastos (fecha, descripcion, valor, tipo)
                VALUES (%s, %s, %s, %s)
            """, (fecha, descripcion, valor, tipo))
            mysql.connection.commit()

        gastos_list = obtener_gastos_mes_actual()

        ingresos = defaultdict(float)
        egresos = defaultdict(float)

        for g in gastos_list:
            dia = g['fecha'].day
            if g['tipo'] == 'ingreso':
                ingresos[dia] += g['valor']
            else:
                egresos[dia] += g['valor']

        dias = sorted(set(ingresos.keys()).union(egresos.keys()))
        etiquetas = [str(dia) for dia in dias]
        datos_ingresos = [ingresos[d] for d in dias]
        datos_egresos = [egresos[d] for d in dias]

        return render_template('gastos.html',
                               gastos=gastos_list,
                               etiquetas=etiquetas,
                               ingresos=datos_ingresos,
                               egresos=datos_egresos)
    finally:
        cursor.close()

@app.route('/ideas')
def ideas():
    if 'logueado' in session:
        return render_template('ideas.html', usuario=session['usuario'])
    else:
        return redirect(url_for('iniciar_sesion'))

@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    return redirect(url_for('inicio'))

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
            WHERE titulo = %s AND id_usuario = %s
        ''', (nueva_fecha, titulo, session['id_usuario']))
        mysql.connection.commit()
        cursor.close()

        if cursor.rowcount == 0:
            return jsonify({'exito': False, 'error': 'Tarea no encontrada'})

        return jsonify({'exito': True})
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
