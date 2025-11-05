import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Cronograma
from werkzeug.utils import secure_filename
from datetime import datetime

cronogramas_bp = Blueprint('cronogramas', __name__, template_folder='../templates')

@cronogramas_bp.route('/', methods=['GET'])
@login_required
def index():
    cronogramas = Cronograma.query.order_by(Cronograma.fecha.asc()).all()
    return render_template('cronogramas.html', cronogramas=cronogramas)

@cronogramas_bp.route('/subir', methods=['GET','POST'])
@login_required
def subir_cronograma():
    if request.method == 'POST':
        nombre = request.form.get('nombre') or 'Cronograma'
        fecha_evento = request.form.get('fecha_evento')
        file = request.files.get('archivo')
        filename = None
        if file and file.filename:
            safe = secure_filename(file.filename)
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe)
            file.save(path)
            filename = safe
        try:
            fecha_dt = datetime.fromisoformat(fecha_evento) if fecha_evento else None
        except:
            fecha_dt = None
        c = Cronograma(nombre=nombre, archivo=filename, fecha=fecha_dt, subido_por=current_user.id)
        db.session.add(c)
        db.session.commit()
        flash('Cronograma guardado', 'success')
        return redirect(url_for('cronogramas.subir_cronograma'))
    return render_template('subir_cronograma.html')

@cronogramas_bp.route('/<int:id>/editar', methods=['GET','POST'])
@login_required
def editar(id):
    c = Cronograma.query.get_or_404(id)
    if current_user.role != 'admin' and current_user.id != c.subido_por:
        flash('Acceso denegado', 'danger')
        return redirect(url_for('cronogramas.index'))
    if request.method == 'POST':
        c.nombre = request.form.get('nombre') or c.nombre
        fecha_evento = request.form.get('fecha_evento')
        try:
            c.fecha = datetime.fromisoformat(fecha_evento) if fecha_evento else c.fecha
        except:
            pass
        file = request.files.get('archivo')
        if file and file.filename:
            safe = secure_filename(file.filename)
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe)
            file.save(path)
            if c.archivo:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], c.archivo))
                except:
                    pass
            c.archivo = safe
        db.session.commit()
        flash('Cronograma actualizado', 'success')
        return redirect(url_for('cronogramas.index'))
    return render_template('editar_cronograma.html', cronograma=c)

@cronogramas_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar(id):
    if current_user.role != 'admin':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('cronogramas.index'))
    c = Cronograma.query.get_or_404(id)
    if c.archivo:
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], c.archivo))
        except:
            pass
    db.session.delete(c)
    db.session.commit()
    flash('Cronograma eliminado', 'success')
    return redirect(url_for('cronogramas.index'))

@cronogramas_bp.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory('uploads/cronogramas', filename)

@cronogramas_bp.route('/descargar/<int:cronograma_id>')
@login_required
def descargar_cronograma(cronograma_id):
    c = Cronograma.query.get_or_404(cronograma_id)
    if not c.archivo:
        flash('No hay archivo para este cronograma', 'warning')
        return redirect(url_for('cronogramas.index'))
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        c.archivo,
        as_attachment=True
    )

@cronogramas_bp.route('/ver/<int:cronograma_id>')
@login_required
def ver_cronograma(cronograma_id):
    c = Cronograma.query.get_or_404(cronograma_id)
    if not c.archivo:
        flash('No hay archivo disponible para este cronograma', 'warning')
        return redirect(url_for('cronogramas.index'))

    # Mostrar el PDF directamente desde la carpeta correcta
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        c.archivo,
        as_attachment=False
    )