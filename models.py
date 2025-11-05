from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ---------------------------
# MODELO USUARIO
# ---------------------------
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(50), default='user')

    # Relaciones
    actas_subidas = db.relationship('Acta', back_populates='uploader')
    sugerencias = db.relationship('Sugerencia', back_populates='usuario')
    lecturas = db.relationship('Lectura', back_populates='usuario')
    cronogramas_subidos = db.relationship('Cronograma', back_populates='uploader')
    verificaciones_hechas = db.relationship('VerificacionActa', back_populates='usuario')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ---------------------------
# MODELO ACTA
# ---------------------------
class Acta(db.Model):
    __tablename__ = 'actas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120))
    archivo = db.Column(db.String(200))
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)
    subido_por = db.Column(db.Integer, db.ForeignKey('users.id'))

    uploader = db.relationship('User', back_populates='actas_subidas')
    lecturas = db.relationship('Lectura', back_populates='acta')
    sugerencias = db.relationship('Sugerencia', back_populates='acta')
    verificaciones_recibidas = db.relationship('VerificacionActa', back_populates='acta')

    # 🔹 Nueva propiedad para saber si el acta fue verificada
    @property
    def verificada(self):
        return len(self.verificaciones_recibidas) > 0

# ---------------------------
# MODELO LECTURA
# ---------------------------
class Lectura(db.Model):
    __tablename__ = 'lecturas'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    acta_id = db.Column(db.Integer, db.ForeignKey('actas.id'))
    fecha_lectura = db.Column(db.DateTime, default=datetime.utcnow)
    conforme = db.Column(db.Boolean, default=False)
    firma = db.Column(db.String(200))

    usuario = db.relationship('User', back_populates='lecturas')
    acta = db.relationship('Acta', back_populates='lecturas')

# ---------------------------
# MODELO SUGERENCIA
# ---------------------------
class Sugerencia(db.Model):
    __tablename__ = 'sugerencias'
    id = db.Column(db.Integer, primary_key=True)
    acta_id = db.Column(db.Integer, db.ForeignKey('actas.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comentario = db.Column(db.Text)
    respuesta_admin = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('User', back_populates='sugerencias')
    acta = db.relationship('Acta', back_populates='sugerencias')

# ---------------------------
# MODELO CRONOGRAMA
# ---------------------------
class Cronograma(db.Model):
    __tablename__ = 'cronogramas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200))
    archivo = db.Column(db.String(200))
    fecha = db.Column(db.DateTime)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)
    subido_por = db.Column(db.Integer, db.ForeignKey('users.id'))

    uploader = db.relationship('User', back_populates='cronogramas_subidos')

# ---------------------------
# MODELO VERIFICACIÓN DE ACTA
# ---------------------------
class VerificacionActa(db.Model):
    __tablename__ = 'verificaciones_actas'
    id = db.Column(db.Integer, primary_key=True)
    acta_id = db.Column(db.Integer, db.ForeignKey('actas.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fecha_verificacion = db.Column(db.DateTime, default=datetime.utcnow)

    acta = db.relationship('Acta', back_populates='verificaciones_recibidas')
    usuario = db.relationship('User', back_populates='verificaciones_hechas')

# ---------------------------
# FUNCIONES DE INICIALIZACIÓN
# ---------------------------
def init_db():
    db.create_all()

def create_admin():
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()