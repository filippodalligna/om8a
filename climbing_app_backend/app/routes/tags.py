from flask import Blueprint, request, jsonify
from flask_login import login_required # current_user is not used here anymore
from flask_babel import gettext as _
from app import db
from app.models.models import Tag # ClimbingBlock is not used here anymore

# Define the blueprint
tags_bp = Blueprint('tags', __name__, url_prefix='/tags')

@tags_bp.route('/', methods=['POST'])
@login_required # Assuming only logged-in users can create tags for now
def create_tag():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'message': _('Tag name is required')}), 400

    tag_name = data['name'].strip().lower() # Normalize tag name
    if not tag_name:
        return jsonify({'message': _('Tag name cannot be empty')}), 400

    existing_tag = Tag.query.filter_by(name=tag_name).first()
    if existing_tag:
        return jsonify({'message': _('Tag already exists'), 'tag': {'id': existing_tag.id, 'name': existing_tag.name}}), 409

    new_tag = Tag(name=tag_name)
    db.session.add(new_tag)
    db.session.commit()

    return jsonify({'message': _('Tag created successfully'), 'tag': {'id': new_tag.id, 'name': new_tag.name}}), 201

@tags_bp.route('/', methods=['GET'])
def list_tags():
    tags = Tag.query.order_by(Tag.name).all()
    tags_data = [{'id': tag.id, 'name': tag.name} for tag in tags]
    return jsonify(tags_data), 200

# The endpoints for adding/removing tags from blocks have been moved to routes/blocks.py
