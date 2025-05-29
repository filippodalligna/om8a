import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from flask_babel import gettext as _ # Added
from app import db
from app.models.models import ClimbingBlock, User, Tag, Comment 
from app.services.badge_service import award_badge, BADGE_FIRST_COMMENT, BADGE_BLOCK_UPLOADER
from app.services.notification_service import send_notification # Added

# Define the blueprint
# url_prefix is /blocks, so routes defined here will be /blocks/..., /blocks/uploads/...
bp = Blueprint('blocks', __name__) # This is blocks_bp. blocks_bp is registered with /blocks prefix.

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
        'uuid': new_block.uuid, 
        'name': new_block.name,
        'difficulty': new_block.difficulty,
        'photo_filename': new_block.photo_filename,
        'photo_url': f'/blocks/uploads/{new_block.photo_filename}' if new_block.photo_filename else None,
        'highlight_data': new_block.highlight_data,
        'uploader_id': new_block.uploader_id,
        'uploader_username': current_user.username, 
        'created_at': new_block.created_at.isoformat()
    }
    
    # Award "Route Setter" badge if it's the user's first block with a photo
    if new_block.photo_filename: # Check if photo was actually uploaded
        if ClimbingBlock.query.filter_by(uploader_id=current_user.id).filter(ClimbingBlock.photo_filename.isnot(None)).count() == 1:
            award_badge(current_user.id, BADGE_BLOCK_UPLOADER)
    
    # Notify followers about the new block
    try:
        uploader = current_user # User who uploaded the block
        # uploader.followers is a dynamic query because of lazy='dynamic'
        for follower in uploader.followers: # Iterating directly should work for dynamic queries
            if follower.id != uploader.id: # Don't notify self (though not expected in followers)
                payload = {
                    "title": _("New Block Alert!"),
                    "body": _("%(uploader_name)s just added a new block: %(block_name)s", 
                              uploader_name=uploader.username, 
                              block_name=new_block.name),
                    "url": f"/blocks/{new_block.id}" # Example URL
                }
                send_notification(follower, payload)
    except Exception as e:
        # Log error, but don't let notification failure break the main operation
        print(f"Error trying to send new block notification to followers of user {uploader.id}: {e}")
            
    return jsonify({'message': 'Climbing block created successfully', 'block': block_data}), 201

@bp.route('/', methods=['GET'])
def get_blocks():
    query = ClimbingBlock.query

    # Tag filtering
    tags_str = request.args.get('tags')
    if tags_str:
        tag_names = [name.strip().lower() for name in tags_str.split(',') if name.strip()]
        if tag_names:
            for tag_name in tag_names:
                # This ensures the block has an associated tag with the given name.
                # Chaining these acts as an AND condition.
                query = query.filter(ClimbingBlock.tags.any(Tag.name == tag_name))
    
    # Add other filters here if needed, e.g., difficulty
    # difficulty = request.args.get('difficulty')
    # if difficulty:
    #     query = query.filter(ClimbingBlock.difficulty == difficulty)

    blocks = query.order_by(ClimbingBlock.created_at.desc()).all() # Example ordering
    
    blocks_data = []
    for block in blocks:
        block_tags_data = [{'id': tag.id, 'name': tag.name} for tag in block.tags]
        blocks_data.append({
            'id': block.id,
            'uuid': block.uuid, # Added UUID here too for consistency
            'name': block.name,
            'difficulty': block.difficulty,
            'photo_url': f'/blocks/uploads/{block.photo_filename}' if block.photo_filename else None,
            'uploader_id': block.uploader_id,
            'created_at': block.created_at.isoformat(),
            'tags': block_tags_data
        })
    return jsonify(blocks_data), 200

@bp.route('/<int:block_id>', methods=['GET'])
def get_block(block_id):
    block = ClimbingBlock.query.get_or_404(block_id)
    uploader = User.query.get(block.uploader_id) # Assuming User model has a simple query
    
    block_tags_data = [{'id': tag.id, 'name': tag.name} for tag in block.tags]
    
    block_data = {
        'id': block.id,
        'uuid': block.uuid, # Added/Ensured UUID
        'name': block.name,
        'difficulty': block.difficulty,
        'photo_filename': block.photo_filename,
        'photo_url': f'/blocks/uploads/{block.photo_filename}' if block.photo_filename else None, # Corrected variable
        'highlight_data': block.highlight_data,
        'uploader_id': block.uploader_id,
        'uploader_username': uploader.username if uploader else 'Unknown',
        'created_at': block.created_at.isoformat(),
        'tags': block_tags_data
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

# --- Tag association endpoints moved from tags.py ---

@bp.route('/<int:block_id>/tags', methods=['POST'])
@login_required
def add_tag_to_block(block_id):
    data = request.get_json()
    if not data:
        return jsonify({'message': _('Missing data')}), 400

    tag_id = data.get('tag_id')
    tag_name = data.get('tag_name') # Allow creating/using tag by name

    if not tag_id and not tag_name:
        return jsonify({'message': _('Missing tag_id or tag_name')}), 400
    
    block = ClimbingBlock.query.get_or_404(block_id)
    # Optional: Check if current_user is authorized to tag this block (e.g., uploader)
    # if block.uploader_id != current_user.id:
    #     return jsonify({'message': _('Not authorized to tag this block')}), 403

    tag_to_add = None
    if tag_id:
        tag_to_add = Tag.query.get(tag_id)
        if not tag_to_add:
            return jsonify({'message': _('Tag not found by id')}), 404
    elif tag_name:
        tag_name = tag_name.strip().lower()
        if not tag_name: # Check for empty string after strip
            return jsonify({'message': _('Tag name cannot be empty')}), 400
        tag_to_add = Tag.query.filter_by(name=tag_name).first()
        if not tag_to_add: # Create tag if it doesn't exist by name
            tag_to_add = Tag(name=tag_name)
            db.session.add(tag_to_add)
            # db.session.commit() # Commit here if tag creation is atomic, or at the end. Block add will commit.

    if not tag_to_add: # Should ideally not be reached if logic above is correct
         return jsonify({'message': _('Tag could not be processed')}), 500


    if tag_to_add in block.tags:
        return jsonify({'message': _('Tag already associated with this block')}), 409

    block.tags.append(tag_to_add)
    db.session.commit() # Commit after appending and potentially adding new tag
    
    block_tags_data = [{'id': tag.id, 'name': tag.name} for tag in block.tags]
    return jsonify({'message': _('Tag added to block'), 'tags': block_tags_data}), 200


@bp.route('/<int:block_id>/tags/<int:tag_id>', methods=['DELETE'])
@login_required
def remove_tag_from_block(block_id, tag_id):
    block = ClimbingBlock.query.get_or_404(block_id)
    # Optional: Check if current_user is authorized (e.g., uploader or admin)
    # if block.uploader_id != current_user.id: # Example authorization check
    #     return jsonify({'message': _('Not authorized to modify this block')}), 403
        
    tag_to_remove = Tag.query.get(tag_id) # No need for _or_404, check existence below
    if not tag_to_remove:
        return jsonify({'message': _('Tag not found')}), 404

    if tag_to_remove not in block.tags:
        return jsonify({'message': _('Tag not associated with this block')}), 404 # Or 400 Bad Request

    block.tags.remove(tag_to_remove)
    db.session.commit()

    return jsonify({'message': _('Tag removed from block')}), 200

# --- Comment endpoints for a specific block ---

@bp.route('/<int:block_id>/comments', methods=['POST'])
@login_required
def post_comment_on_block(block_id):
    block = ClimbingBlock.query.get_or_404(block_id) # Ensures block exists
    data = request.get_json()

    if not data or not data.get('text') or not data.get('text').strip():
        return jsonify({'error': _('Comment text is required and cannot be empty')}), 400

    text = data.get('text').strip()
    
    comment = Comment(
        text=text,
        block_id=block.id, # Use block.id from the fetched block
        user_id=current_user.id
    )
    db.session.add(comment)
    db.session.commit()

    # Fetch author username for serialization (or use comment.author.username)
    # author = User.query.get(comment.user_id)

    serialized_comment = {
        'id': comment.id,
        'text': comment.text,
        'created_at': comment.created_at.isoformat() + 'Z', # ISO 8601 format with Z for UTC
        'author_username': comment.author.username, # Accessing via backref
        'block_id': comment.block_id,
        'user_id': comment.user_id
    }

    # Award "Commentator" badge if it's the user's first comment
    if Comment.query.filter_by(user_id=current_user.id).count() == 1:
        award_badge(current_user.id, BADGE_FIRST_COMMENT)
        
    return jsonify({'message': _('Comment posted successfully'), 'comment': serialized_comment}), 201

@bp.route('/<int:block_id>/comments', methods=['GET'])
def get_comments_for_block(block_id):
    block = ClimbingBlock.query.get_or_404(block_id) # Ensures block exists

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int) # Default 10 comments per page

    # Paginate comments for the specific block, ordered by most recent first
    comments_pagination = Comment.query.filter_by(block_id=block.id)\
                                   .order_by(Comment.created_at.desc())\
                                   .paginate(page=page, per_page=per_page, error_out=False)
    
    comments_data = []
    for c in comments_pagination.items:
        # author = User.query.get(c.user_id) # Fetch author for username, or use backref
        comments_data.append({
            'id': c.id,
            'text': c.text,
            'created_at': c.created_at.isoformat() + 'Z', # ISO 8601 format with Z for UTC
            'author_username': c.author.username, # Accessing via backref
            'user_id': c.user_id # Include user_id for frontend logic if needed
        })
    
    return jsonify({
        'comments': comments_data,
        'total_comments': comments_pagination.total,
        'current_page': comments_pagination.page,
        'total_pages': comments_pagination.pages,
        'per_page': comments_pagination.per_page,
        'has_next': comments_pagination.has_next,
        'has_prev': comments_pagination.has_prev
    }), 200

@bp.route('/qr/<uuid_string>', methods=['GET'])
def get_block_by_qr_uuid(uuid_string):
    try:
        # Validate if uuid_string is a valid UUID format before querying
        # This doesn't check version, but ensures it's a valid UUID structure
        val_uuid = uuid.UUID(uuid_string, version=4) # Specify version 4 for validation
    except ValueError:
        return jsonify({'error': _('Invalid UUID format')}), 400

    # Query by the string representation of the UUID
    block = ClimbingBlock.query.filter_by(uuid=uuid_string).first() # Use .first() and check if None
    
    if not block:
        return jsonify({'error': _('Block not found with this QR code UUID')}), 404

    # Serialize block data (similar to get_block(block_id))
    uploader = User.query.get(block.uploader_id)
    block_tags_data = [{'id': tag.id, 'name': tag.name} for tag in block.tags]
    
    # Consider if comments should be included or be a separate sub-resource call
    # For now, let's keep it similar to get_block without comments for brevity in this response
    
    block_data = {
        'id': block.id,
        'uuid': block.uuid,
        'name': block.name,
        'difficulty': block.difficulty,
        'photo_url': f"/blocks/uploads/{block.photo_filename}" if block.photo_filename else None,
        'highlight_data': block.highlight_data,
        'uploader_id': block.uploader_id,
        'uploader_username': uploader.username if uploader else 'Unknown',
        'created_at': block.created_at.isoformat(),
        'tags': block_tags_data
        # Comments could be paginated and fetched via /blocks/<id>/comments
    }
    return jsonify(block_data), 200
