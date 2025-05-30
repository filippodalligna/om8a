from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models.models import Comment, User # User needed for author_username serialization

# Define the blueprint
comments_bp = Blueprint('comments', __name__, url_prefix='/comments')

@comments_bp.route('/<int:comment_id>', methods=['PUT'])
@login_required
def update_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != current_user.id:
        return jsonify({'error': _('You are not authorized to edit this comment')}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': _('Request body must be JSON')}), 400

    new_text = data.get('text')
    if not new_text or not new_text.strip():
        return jsonify({'error': _('Comment text cannot be empty')}), 400

    comment.text = new_text.strip()
    db.session.commit()

    # Fetch author username for serialization
    # author = User.query.get(comment.user_id) # Not strictly needed if using comment.author.username

    serialized_comment = {
        'id': comment.id,
        'text': comment.text,
        'created_at': comment.created_at.isoformat() + 'Z',
        'author_username': comment.author.username, # Accessing via backref
        'block_id': comment.block_id,
        'user_id': comment.user_id
    }
    return jsonify({'message': _('Comment updated successfully'), 'comment': serialized_comment}), 200

@comments_bp.route('/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != current_user.id:
        # Potentially allow admins to delete comments too in a real app
        return jsonify({'error': _('You are not authorized to delete this comment')}), 403

    db.session.delete(comment)
    db.session.commit()

    return jsonify({'message': _('Comment deleted successfully')}), 200 # Or 204 with no body
