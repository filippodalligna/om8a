from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models.models import ClimbingBlock, User, ALLOWED_BLOCK_STATUSES, BlockProposal, ALLOWED_PROPOSAL_STATUSES # Added BlockProposal and its statuses
from app.utils.decorators import admin_required
from datetime import datetime # Added for reviewed_at timestamp

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Helper to serialize proposal for admin responses, can be adapted from proposals.py
def serialize_proposal_for_admin(proposal):
    return {
        'id': proposal.id,
        'proposer_id': proposal.proposer_id,
        'proposer_username': proposal.proposer.username if proposal.proposer else "Unknown",
        'location_description': proposal.location_description,
        'climb_description': proposal.climb_description,
        'proposed_grade': proposal.proposed_grade,
        'photo_filename_proposal': proposal.photo_filename_proposal,
        'photo_url_proposal': f'/proposals/uploads/{proposal.photo_filename_proposal}' if proposal.photo_filename_proposal else None, # Assuming /proposals/uploads route exists
        'status': proposal.status,
        'admin_reviewer_id': proposal.admin_reviewer_id,
        'admin_reviewer_username': proposal.admin_reviewer.username if proposal.admin_reviewer else None,
        'admin_notes': proposal.admin_notes,
        'created_at': proposal.created_at.isoformat() + 'Z',
        'reviewed_at': proposal.reviewed_at.isoformat() + 'Z' if proposal.reviewed_at else None,
    }

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
            'updated_at': block.updated_at.isoformat(),
            'status': block.status # Added status to the response
        })

    return jsonify({
        'blocks': blocks_data,
        'total_blocks': blocks_pagination.total,
        'current_page': blocks_pagination.page,
        'total_pages': blocks_pagination.pages,
        'per_page': blocks_pagination.per_page
    }), 200


# --- Block Proposal Admin Endpoints ---

@admin_bp.route('/proposals/pending', methods=['GET'])
@admin_required
def list_pending_proposals():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int) # Default 10 proposals per page

    proposals_pagination = BlockProposal.query.filter_by(status='pending')\
                                       .order_by(BlockProposal.created_at.asc())\
                                       .paginate(page=page, per_page=per_page, error_out=False)

    proposals_data = [serialize_proposal_for_admin(p) for p in proposals_pagination.items]

    return jsonify({
        'proposals': proposals_data,
        'total_proposals': proposals_pagination.total,
        'current_page': proposals_pagination.page,
        'total_pages': proposals_pagination.pages,
        'per_page': proposals_pagination.per_page,
        'has_next': proposals_pagination.has_next,
        'has_prev': proposals_pagination.has_prev
    }), 200

@admin_bp.route('/proposals/<int:proposal_id>/review', methods=['PUT'])
@admin_required
def review_block_proposal(proposal_id):
    proposal = BlockProposal.query.get_or_404(proposal_id)
    data = request.json

    if not data or 'status' not in data:
        return jsonify({'error': _('Status field is required.')}), 400

    new_status = data['status'].strip().lower()
    admin_notes = data.get('admin_notes', '').strip() or None

    if new_status not in ALLOWED_PROPOSAL_STATUSES:
        return jsonify({'error': _('Invalid status value. Allowed: %(values)s', values=", ".join(ALLOWED_PROPOSAL_STATUSES))}), 400

    if proposal.status != 'pending' and new_status == 'pending':
         return jsonify({'error': _('Cannot revert a reviewed proposal to pending via this endpoint.')}), 400
    if proposal.status != 'pending' and new_status != proposal.status :
         # Potentially allow changing between approved/rejected if needed, or restrict further.
         # For now, let's assume only changing notes on already reviewed items is fine, or changing status from pending.
         pass # Allow changing notes or status if it's not from pending to pending.

    proposal.status = new_status
    proposal.admin_notes = admin_notes
    proposal.admin_reviewer_id = current_user.id
    proposal.reviewed_at = datetime.utcnow()

    # Note: If status is 'approved', creating the actual ClimbingBlock is deferred.
    # This would involve creating a new ClimbingBlock entry, copying relevant data,
    # potentially linking the proposal to the new block, etc.

    try:
        db.session.commit()
        return jsonify({'message': _('Block proposal reviewed successfully.'), 'proposal': serialize_proposal_for_admin(proposal)}), 200
    except Exception as e:
        db.session.rollback()
        # Log e for debugging
        return jsonify({'error': _('Failed to review block proposal.')}), 500

@admin_bp.route('/blocks/<int:block_id>/status', methods=['PUT'])
@admin_required
def update_block_status_by_admin(block_id):
    block = ClimbingBlock.query.get_or_404(block_id)
    data = request.json

    if not data or 'status' not in data:
        return jsonify({'error': _('Status field is required in the request body.')}), 400

    new_status = data.get('status')
    if not new_status or new_status.strip() == "":
        return jsonify({'error': _('Status field cannot be empty.')}), 400

    new_status = new_status.strip().lower()
    if new_status not in ALLOWED_BLOCK_STATUSES:
        return jsonify({'error': _('Invalid status value. Allowed values are: %(values)s', values=", ".join(ALLOWED_BLOCK_STATUSES))}), 400

    block.status = new_status
    # block.updated_at should be handled by onupdate=datetime.utcnow in the model

    try:
        db.session.commit()
        # Consistent serialization with other admin block responses
        uploader_username = block.uploader.username if block.uploader else None
        block_tags_data = [{'id': tag.id, 'name': tag.name} for tag in block.tags]

        block_data = {
           'id': block.id,
           'uuid': block.uuid,
           'name': block.name,
           'difficulty': block.difficulty,
           'status': block.status, # Included new status
           'photo_filename': block.photo_filename,
           'photo_url': f"/blocks/uploads/{block.photo_filename}" if block.photo_filename else None,
           'highlight_data': block.highlight_data,
           'uploader_id': block.uploader_id,
           'uploader_username': uploader_username,
           'created_at': block.created_at.isoformat() + 'Z', # Added Z for consistency
           'updated_at': block.updated_at.isoformat() + 'Z', # Added Z for consistency
           'tags': block_tags_data
        }
        return jsonify({'message': _('Block status updated successfully.'), 'block': block_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': _('Failed to update block status.'), 'details': str(e)}), 500

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

@admin_bp.route('/users/<int:user_id>/status', methods=['PUT'])
@admin_required
def update_user_status_by_admin(user_id):
    user_to_update = User.query.get_or_404(user_id)
    data = request.json

    if not data:
        return jsonify({'error': _('Request body cannot be empty.')}), 400

    updated_fields = []
    if 'is_admin' in data and isinstance(data['is_admin'], bool):
        if user_to_update.id == current_user.id and not data['is_admin']:
            return jsonify({'error': _('Admins cannot remove their own admin status.')}), 400
        user_to_update.is_admin = data['is_admin']
        updated_fields.append('is_admin')

    if 'is_active' in data and isinstance(data['is_active'], bool):
        if user_to_update.id == current_user.id and not data['is_active']:
            return jsonify({'error': _('Admins cannot deactivate their own account.')}), 400
        user_to_update.is_active = data['is_active']
        updated_fields.append('is_active')

    if not updated_fields:
        return jsonify({'message': _('No valid fields provided for update or no changes made.')}), 400

    try:
        db.session.commit()
        user_data = {
            'id': user_to_update.id,
            'username': user_to_update.username,
            'is_admin': user_to_update.is_admin,
            'is_active': user_to_update.is_active,
            'created_at': user_to_update.created_at.isoformat() + 'Z' if user_to_update.created_at else None
        }
        return jsonify({'message': _('User status updated successfully.'), 'user': user_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': _('Failed to update user status.'), 'details': str(e)}), 500

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
            'updated_at': block.updated_at.isoformat(),
            'status': block.status # Added status to the response for consistency
        })

    return jsonify({
        'blocks': blocks_data,
        'total_blocks': blocks_pagination.total,
        'current_page': blocks_pagination.page,
        'total_pages': blocks_pagination.pages,
        'per_page': blocks_pagination.per_page
    }), 200
