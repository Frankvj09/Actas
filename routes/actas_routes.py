import os, time
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Acta, Lectura, User, Sugerencia, Cronograma
from werkzeug.utils import secure_filename
from datetime import datetime
from models import VerificacionActa
from flask import jsonify

actas_bp = Blueprint('actas', __name__, template_folder='../templates')

@actas_bp.route('/')
@login_required
def dashboard():
    actas = Acta.query.order_by(Acta.fecha_subida.desc()).all()
    lecturas = {l.acta_id: l for l in Lectura.query.filter_by(usuario_id=current_user.id).all()}
    cronogramas = Cronograma.query.order_by(Cronograma.fecha.asc()).all()
    return render_template('dashboard.html', actas=actas, lecturas=lecturas, cronogramas=cronogramas)


@actas_bp.route('/subir', methods=['GET','POST'])
@login_required
def subir_acta():
    if request.method == 'POST':
        file = request.files.get('archivo')
        title = request.form.get('title') or (file.filename if file else 'Acta sin título')
        filename = None
        if file and file.filename:
            safe = secure_filename(file.filename)
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe)
            file.save(path)
            filename = safe
        nueva = Acta(nombre=title, archivo=filename, subido_por=current_user.id)
        db.session.add(nueva)
        db.session.commit()
        flash('Acta subida correctamente', 'success')
        return redirect(url_for('actas.subir_acta'))
    return render_template('subir_acta.html')

@actas_bp.route('/ver/<int:acta_id>')
@login_required
def ver_acta(acta_id):
    acta = Acta.query.get_or_404(acta_id)

    # 🔹 Registrar lectura si no existe
    lectura = Lectura.query.filter_by(usuario_id=current_user.id, acta_id=acta.id).first()
    if not lectura:
        lectura = Lectura(usuario_id=current_user.id, acta_id=acta.id)
        db.session.add(lectura)
        db.session.commit()

    # 🔹 Obtener sugerencias del acta
    sugerencias = Sugerencia.query.filter_by(acta_id=acta.id).order_by(Sugerencia.fecha.desc()).all()

    # 🔹 🔸 NUEVA LÍNEA: usuarios que verificaron esta acta
    usuarios_verificados = [v.usuario_id for v in acta.verificaciones_recibidas]

    # 🔹 Pasamos la variable al template
    return render_template(
        'leer_acta.html',
        acta=acta,
        lectura=lectura,
        sugerencias=sugerencias,
        usuarios_verificados=usuarios_verificados  # ← esta línea es clave
    )

@actas_bp.route('/descargar/<int:acta_id>')
@login_required
def descargar_acta(acta_id):
    acta = Acta.query.get_or_404(acta_id)
    if not acta.archivo:
        flash('No hay archivo para descargar', 'warning')
        return redirect(url_for('actas.dashboard'))
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], acta.archivo, as_attachment=True)

@actas_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@actas_bp.route('/acta/<int:acta_id>/sugerir', methods=['POST'])
@login_required
def sugerir_acta(acta_id):
    texto = request.form.get('sugerencia')
    if not texto:
        flash('La sugerencia no puede estar vacía', 'warning')
        return redirect(url_for('ver_acta', acta_id=acta_id))
    s = Sugerencia(acta_id=acta_id, usuario_id=current_user.id, comentario=texto)
    db.session.add(s)
    db.session.commit()
    flash('Sugerencia enviada', 'success')
    return redirect(url_for('actas.ver_acta', acta_id=acta_id))

@actas_bp.route('/sugerencia/<int:sug_id>/responder', methods=['POST'])
@login_required
def responder_sugerencia(sug_id):
    s = Sugerencia.query.get_or_404(sug_id)
    if current_user.role != 'admin':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('actas.dashboard'))
    respuesta = request.form.get('respuesta')
    s.respuesta_admin = respuesta
    db.session.commit()
    flash('Respuesta guardada', 'success')
    return redirect(url_for('actas.ver_acta', acta_id=s.acta_id))

@actas_bp.route('/acta/<int:acta_id>/eliminar', methods=['POST'])
@login_required
def eliminar_acta(acta_id):
    if current_user.role != 'admin':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('actas.dashboard'))

    acta = Acta.query.get_or_404(acta_id)

    # Eliminar archivo físico
    if acta.archivo:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], acta.archivo)
        if os.path.exists(file_path):
            os.remove(file_path)

    # Forzar eliminación incluso si hay conflictos
    try:
        db.session.delete(acta)
        db.session.commit()
        flash('Acta eliminada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar acta antigua: {str(e)}', 'warning')

        # Si no se pudo borrar (ej. actas viejas), se borra manualmente de la tabla
        db.session.execute(db.text("DELETE FROM actas WHERE id = :id"), {"id": acta_id})
        db.session.commit()
        flash('Acta antigua eliminada forzosamente.', 'success')

    return redirect(url_for('actas.dashboard'))


@actas_bp.route('/acta/<int:acta_id>/editar', methods=['GET','POST'])
@login_required
def editar_acta(acta_id):
    a = Acta.query.get_or_404(acta_id)
    if current_user.role != 'admin' and current_user.id != a.subido_por:
        flash('Acceso denegado', 'danger')
        return redirect(url_for('actas.dashboard'))
    if request.method == 'POST':
        a.nombre = request.form.get('title') or a.nombre
        file = request.files.get('archivo')
        if file and file.filename:
            safe = secure_filename(file.filename)
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], safe)
            file.save(path)
            if a.archivo:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], a.archivo))
                except:
                    pass
            a.archivo = safe
        db.session.commit()
        flash('Acta actualizada', 'success')
        return redirect(url_for('ver_acta', acta_id=a.id))
    return render_template('editar_acta.html', acta=a)

@actas_bp.route('/acta/<int:acta_id>/verificar', methods=['POST'])
@login_required
def toggle_verificada(acta_id):
    from models import VerificacionActa  # Evita import circular

    acta = Acta.query.get_or_404(acta_id)
    verificacion = VerificacionActa.query.filter_by(
        acta_id=acta.id, usuario_id=current_user.id
    ).first()

    if verificacion:
        db.session.delete(verificacion)
        db.session.commit()
        estado = False
        mensaje = 'Has quitado la verificación del acta.'
    else:
        nueva = VerificacionActa(acta_id=acta.id, usuario_id=current_user.id)
        db.session.add(nueva)
        db.session.commit()
        estado = True
        mensaje = 'Has verificado el acta correctamente.'

    # Si la solicitud es AJAX → respondemos JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'estado': estado, 'mensaje': mensaje})

    # Si no, seguimos con el flujo normal
    flash(mensaje, 'success' if estado else 'warning')
    return redirect(url_for('actas.ver_acta', acta_id=acta.id))

