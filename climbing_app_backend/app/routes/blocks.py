import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from app import db
from app.models.models import ClimbingBlock, User

# Define the blueprint
# url_prefix is /blocks, so routes defined here will be /blocks/..., /blocks/uploads/...
bp = Blueprint('blocks', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/', methods=['POST'])
@login_required
def create_block():
    if 'name' not in request.form or 'difficulty' not in request.form:
        return jsonify({'message': 'Missing name or difficulty'}), 400

    photo_file = None
    final_filename = None

    if 'photo' in request.files:
        photo_file = request.files['photo']
        if photo_file.filename == '':
            # No selected file part, but 'photo' key was present
            pass # final_filename remains None
        elif photo_file and allowed_file(photo_file.filename):
            original_filename = secure_filename(photo_file.filename)
            # Create a unique filename using UUID and keep original extension
            unique_prefix = str(uuid.uuid4())
            extension = original_filename.rsplit('.', 1)[1].lower()
            final_filename = f"{unique_prefix}.{extension}"
            
            upload_folder_abs = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER'])
            try:
                # The folder creation is already handled in app/__init__.py
                # os.makedirs(upload_folder_abs, exist_ok=True) 
                photo_file.save(os.path.join(upload_folder_abs, final_filename))
            except Exception as e:
                return jsonify({'message': f'Could not save photo: {str(e)}'}), 500
        else:
            return jsonify({'message': 'Invalid file type for photo'}), 400

    new_block = ClimbingBlock(
        name=request.form['name'],
        difficulty=request.form['difficulty'],
        photo_filename=final_filename,
        highlight_data=request.form.get('highlight_data'),
        uploader_id=current_user.id
    )
    db.session.add(new_block)
    db.session.commit()

    block_data = {
        'id': new_block.id,
        'name': new_block.name,
        'difficulty': new_block.difficulty,
        'photo_filename': new_block.photo_filename,
        'photo_url': f'/blocks/uploads/{new_block.photo_filename}' if new_block.photo_filename else None,
        'highlight_data': new_block.highlight_data,
        'uploader_id': new_block.uploader_id,
        'created_at': new_block.created_at.isoformat()
    }
    return jsonify({'message': 'Climbing block created successfully', 'block': block_data}), 201

@bp.route('/', methods=['GET'])
def get_blocks():
    blocks = ClimbingBlock.query.all()
    blocks_data = []
    for block in blocks:
        blocks_data.append({
            'id': block.id,
            'name': block.name,
            'difficulty': block.difficulty,
            'photo_url': f'/blocks/uploads/{block.photo_filename}' if block.photo_filename else None,
            'uploader_id': block.uploader_id,
            'created_at': block.created_at.isoformat()
        })
    return jsonify(blocks_data), 200

@bp.route('/<int:block_id>', methods=['GET'])
def get_block(block_id):
    block = ClimbingBlock.query.get_or_404(block_id)
    uploader = User.query.get(block.uploader_id) # Assuming User model has a simple query
    
    block_data = {
        'id': block.id,
        'name': block.name,
        'difficulty': block.difficulty,
        'photo_filename': block.photo_filename,
        'photo_url': f'/blocks/uploads/{block.photo_filename}' if block.photo_filename else None,
        'highlight_data': block.highlight_data,
        'uploader_id': block.uploader_id,
        'uploader_username': uploader.username if uploader else 'Unknown',
        'created_at': block.created_at.isoformat()
    }
    return jsonify(block_data), 200

# Route for serving uploaded files from the instance folder
@bp.route('/uploads/<filename>', methods=['GET'])
def serve_uploaded_file(filename):
    upload_folder_abs = os.path.join(current_app.instance_path, current_app.config['UPLOAD_FOLDER'])
    return send_from_directory(upload_folder_abs, filename)

# Placeholder ping route from initial setup, can be removed or kept for basic testing
@bp.route('/ping_blocks_bp', methods=['GET']) # Renamed to avoid conflict if main /ping exists
def ping():
    return jsonify({'message': 'Blocks blueprint is active'})
