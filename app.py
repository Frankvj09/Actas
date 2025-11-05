from flask import Flask
from flask_login import LoginManager
import os
from extensions import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ClaveSegura123'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'data', 'actas_y_cronograma.db').replace('\\', '/')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

from models import User
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    from models import init_db, create_admin
    init_db()
    create_admin()

from routes.auth_routes import auth_bp
from routes.actas_routes import actas_bp
from routes.cronogramas_routes import cronogramas_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(actas_bp, url_prefix='')
app.register_blueprint(cronogramas_bp, url_prefix='/cronogramas')

if __name__ == '__main__':
    app.run(debug=True, port=5500)
