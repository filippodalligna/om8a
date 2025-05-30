from flask import Blueprint, request, jsonify
from flask_login import login_required # Though admin_required handles auth implicitly
from flask_babel import gettext as _
from app import db
from app.models.models import ClimbingBlock, User # User needed for uploader.username
from app.utils.decorators import admin_required # Import the decorator

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/blocks/all', methods=['GET'])
@admin_required
def get_all_blocks_admin():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    blocks_pagination = ClimbingBlock.query.order_by(ClimbingBlock.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    blocks_data = []
    for block in blocks_pagination.items:
        uploader_username = User.query.get(block.uploader_id).username if block.uploader_id else None
        blocks_data.append({
            'id': block.id,
            'uuid': block.uuid,
            'name': block.name,
            'difficulty': block.difficulty,
            'uploader_id': block.uploader_id,
            'uploader_username': uploader_username,
            'photo_filename': block.photo_filename,
            'photo_url': f'/blocks/uploads/{block.photo_filename}' if block.photo_filename else None,
            'created_at': block.created_at.isoformat(),
            'updated_at': block.updated_at.isoformat()
        })
    
    return jsonify({
        'blocks': blocks_data,
        'total_blocks': blocks_pagination.total,
        'current_page': blocks_pagination.page,
        'total_pages': blocks_pagination.pages,
        'per_page': blocks_pagination.per_page
    }), 200

@admin_bp.route('/blocks/needs-photo', methods=['GET'])
@admin_required
def get_blocks_needing_photo_admin():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    blocks_pagination = ClimbingBlock.query.filter(ClimbingBlock.photo_filename.is_(None)) \
                                       .order_by(ClimbingBlock.created_at.desc()) \
                                       .paginate(page=page, per_page=per_page, error_out=False)
    
    blocks_data = []
    for block in blocks_pagination.items:
        uploader_username = User.query.get(block.uploader_id).username if block.uploader_id else None
        blocks_data.append({
            'id': block.id,
            'uuid': block.uuid,
            'name': block.name,
            'difficulty': block.difficulty,
            'uploader_id': block.uploader_id,
            'uploader_username': uploader_username,
            'photo_filename': block.photo_filename, # Will be None
            'created_at': block.created_at.isoformat(),
            'updated_at': block.updated_at.isoformat()
        })
        
    return jsonify({
        'blocks': blocks_data,
        'total_blocks': blocks_pagination.total,
        'current_page': blocks_pagination.page,
        'total_pages': blocks_pagination.pages,
        'per_page': blocks_pagination.per_page
    }), 200
