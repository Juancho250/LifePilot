from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import MySQLdb.cursors
import os

app = Flask(__name__)

# Configuración de la clave secreta para sesiones
app.config['SECRET_KEY'] = 'd16f2bfa7491b82b8f9e30cf60eac02c82c648b1a93f7d9c671a3973d7eb69e5'

# Configuración de la base de datos MySQL local
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'HnvPhkdaVeZ4pD'  # Asegúrate de poner tu contraseña de MySQL si tiene
app.config['MYSQL_DB'] = 'oryon_db'

mysql = MySQL(app)

# Ruta de inicio
@app.route('/')
def inicio():
    return render_template('inicio.html')


# Carpeta donde guardarás las fotos subidas
CARPETA_FOTOS = 'static/uploads'
if not os.path.exists(CARPETA_FOTOS):
    os.makedirs(CARPETA_FOTOS)

app.config['CARPETA_FOTOS'] = CARPETA_FOTOS
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Max 2MB (opcional)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def archivo_permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Registro de usuario
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
            nombre_foto = f"{usuario}_{filename_seguro}"  # evitar colisiones
            ruta_completa = os.path.join(app.config['CARPETA_FOTOS'], nombre_foto)
            foto.save(ruta_completa)
        # Si no suben foto, nombre_foto queda None

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

# Inicio de sesión
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
        fecha_limite = request.form.get('fecha_limite')  # puede venir vacía
        id_usuario = session['id_usuario']
        cursor.execute('INSERT INTO tareas (titulo, estado, id_usuario, fecha_limite) VALUES (%s, %s, %s, %s)', 
                       (titulo, estado, id_usuario, fecha_limite))
        mysql.connection.commit()
        return redirect(url_for('tareas'))

    cursor.execute('SELECT * FROM tareas WHERE id_usuario = %s', (session['id_usuario'],))
    tareas_usuario = cursor.fetchall()
    return render_template('tareas.html', usuario=session['usuario'], tareas=tareas_usuario)


@app.route('/gastos')
def gastos():
    if 'logueado' in session:
        # Aquí puedes obtener datos de gastos si usas base de datos
        return render_template('gastos.html', usuario=session['usuario'])
    else:
        return redirect(url_for('iniciar_sesion'))

@app.route('/ideas')
def ideas():
    if 'logueado' in session:
        # Aquí puedes obtener datos de ideas si usas base de datos
        return render_template('ideas.html', usuario=session['usuario'])
    else:
        return redirect(url_for('iniciar_sesion'))


# Cierre de sesión
@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    return redirect(url_for('inicio'))

if __name__ == '__main__':
    app.run(debug=True)
