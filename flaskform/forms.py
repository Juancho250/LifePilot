from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, DateField, SelectField
from wtforms.validators import DataRequired

class MovimientoForm(FlaskForm):
    fecha = DateField('Fecha', validators=[DataRequired()])
    frecuencia = SelectField('Frecuencia', choices=[
        ('una_vez', 'Una vez'),
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual')
    ], validators=[DataRequired()])
    descripcion = StringField('Descripción', validators=[DataRequired()])
    valor = DecimalField('Valor', places=2, validators=[DataRequired()])
    categoria_id = StringField('Categoría')

class PrestamoForm(FlaskForm):
    fecha = DateField('Fecha', validators=[DataRequired()])
    frecuencia = SelectField('Frecuencia', choices=[
        ('una_vez', 'Una vez'),
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual')
    ], validators=[DataRequired()])
    persona = StringField('Persona', validators=[DataRequired()])
    descripcion = StringField('Descripción', validators=[DataRequired()])
    valor = DecimalField('Valor', places=2, validators=[DataRequired()])

class DeudaForm(FlaskForm):
    fecha = DateField('Fecha', validators=[DataRequired()])
    frecuencia = SelectField('Frecuencia', choices=[
        ('una_vez', 'Una vez'),
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual')
    ], validators=[DataRequired()])
    persona = StringField('Persona', validators=[DataRequired()])
    descripcion = StringField('Descripción', validators=[DataRequired()])
    valor = DecimalField('Valor', places=2, validators=[DataRequired()])

class ListaForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    submit = SubmitField('+')

class LoginForm(FlaskForm):
    usuario = StringField('Nombre de usuario', validators=[DataRequired()])
    clave = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Entrar')


class DummyForm(FlaskForm):
    pass
