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

@admin_bp.route('/blocks/<int:block_id>', methods=['PUT'])
@admin_required
def update_block_by_admin(block_id):
    block = ClimbingBlock.query.get_or_404(block_id)
    data = request.json

    if not data:
        return jsonify({'error': _('Request body cannot be empty.')}), 400

    updated = False
    if 'name' in data:
        if data['name'].strip():
            block.name = data['name'].strip()
            updated = True
        else: # Handle empty string for name if it's not allowed
            return jsonify({'error': _('Block name cannot be empty.')}), 400

    if 'difficulty' in data:
        if data['difficulty'].strip():
            block.difficulty = data['difficulty'].strip()
            updated = True
        else: # Handle empty string for difficulty if it's not allowed
            return jsonify({'error': _('Block difficulty cannot be empty.')}), 400

    if 'highlight_data' in data: # Allows setting to null or empty string
        block.highlight_data = data['highlight_data']
        updated = True

    if not updated:
        return jsonify({'message': _('No valid fields provided for update or no changes made.')}), 400

    try:
        db.session.commit()
        # Serialize and return the updated block
        uploader_username = block.uploader.username if block.uploader else None
        block_tags_data = [{'id': tag.id, 'name': tag.name} for tag in block.tags]

        block_data = {
           'id': block.id,
           'uuid': block.uuid,
           'name': block.name,
           'difficulty': block.difficulty,
           'photo_filename': block.photo_filename,
           'photo_url': f"/blocks/uploads/{block.photo_filename}" if block.photo_filename else None,
           'highlight_data': block.highlight_data,
           'uploader_id': block.uploader_id,
           'uploader_username': uploader_username,
           'created_at': block.created_at.isoformat() + 'Z',
           'updated_at': block.updated_at.isoformat() + 'Z',
           'tags': block_tags_data
        }
        return jsonify({'message': _('Block updated successfully.'), 'block': block_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': _('Failed to update block.'), 'details': str(e)}), 500

@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users_by_admin():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    users_pagination = User.query.order_by(User.id.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    users_data = []
    for user in users_pagination.items:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin,
            'created_at': user.created_at.isoformat() + 'Z' if user.created_at else None
        })

    return jsonify({
        'users': users_data,
        'total_users': users_pagination.total,
        'current_page': users_pagination.page,
        'total_pages': users_pagination.pages,
        'per_page': users_pagination.per_page
    }), 200

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_by_admin(user_id):
    user = User.query.get_or_404(user_id)
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_admin': user.is_admin,
        'created_at': user.created_at.isoformat() + 'Z' if user.created_at else None
    }
    return jsonify(user_data), 200

@admin_bp.route('/blocks/<int:block_id>', methods=['DELETE'])
@admin_required
def delete_block_by_admin(block_id):
    block = ClimbingBlock.query.get_or_404(block_id)

    try:
        # Before deleting the block, handle related UserAttempt and Comment records
        # if foreign key constraints would prevent deletion.
        # This assumes ON DELETE CASCADE is not set for these relationships,
        # or if we want to be explicit / handle other cleanup.

        # UserAttempt.query.filter_by(block_id=block.id).delete() # Example: if needed
        # Comment.query.filter_by(block_id=block.id).delete()     # Example: if needed

        # Also, remove associations in block_tags (many-to-many)
        # SQLAlchemy often handles this automatically if the relationship is set up with cascade delete-orphan,
        # but direct association table entries might need explicit handling if not.
        # For `secondary` table relationships, SQLAlchemy does NOT automatically delete rows from the association table.
        # We need to clear the `block.tags` collection.
        block.tags.clear()

        db.session.delete(block)
        db.session.commit()
        return jsonify({'message': _('Block deleted successfully.')}), 200 # 204 No Content is also an option
    except Exception as e:
        db.session.rollback()
        # A common error here would be a foreign key violation if related records exist
        # and ON DELETE RESTRICT is active and we haven't manually deleted them.
        return jsonify({'error': _('Failed to delete block.'), 'details': str(e)}), 500

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
