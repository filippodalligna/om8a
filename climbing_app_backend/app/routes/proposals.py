import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from flask_babel import gettext as _
from app import db
from app.models.models import BlockProposal, User # User might be needed for proposer details if not using backref effectively

# Define the blueprint
proposals_bp = Blueprint('proposals', __name__, url_prefix='/proposals')

ALLOWED_PROPOSAL_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_proposal_photo(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_PROPOSAL_PHOTO_EXTENSIONS

def serialize_proposal(proposal):
    """Helper function to serialize a BlockProposal object."""
    return {
        'id': proposal.id,
        'proposer_id': proposal.proposer_id,
        'proposer_username': proposal.proposer.username, # Assuming proposer relationship is loaded
        'location_description': proposal.location_description,
        'climb_description': proposal.climb_description,
        'proposed_grade': proposal.proposed_grade,
        'photo_filename_proposal': proposal.photo_filename_proposal,
        'photo_url_proposal': f'/proposals/uploads/{proposal.photo_filename_proposal}' if proposal.photo_filename_proposal else None,
        'status': proposal.status,
        'admin_reviewer_id': proposal.admin_reviewer_id,
        'admin_reviewer_username': proposal.admin_reviewer.username if proposal.admin_reviewer else None,
        'admin_notes': proposal.admin_notes,
        'created_at': proposal.created_at.isoformat() + 'Z',
        'reviewed_at': proposal.reviewed_at.isoformat() + 'Z' if proposal.reviewed_at else None,
    }

@proposals_bp.route('/', methods=['POST'])
@login_required
def submit_block_proposal():
    if 'location_description' not in request.form or not request.form['location_description'].strip():
        return jsonify({'error': _('Location description is required.')}), 400

    location_description = request.form['location_description'].strip()
    climb_description = request.form.get('climb_description', '').strip() or None
    proposed_grade = request.form.get('proposed_grade', '').strip() or None

    photo_file = None
    final_filename = None

    if 'photo_proposal' in request.files:
        photo_file = request.files['photo_proposal']
        if photo_file.filename and photo_file.filename != '':
            if allowed_proposal_photo(photo_file.filename):
                original_filename = secure_filename(photo_file.filename)
                unique_prefix = str(uuid.uuid4())
                extension = original_filename.rsplit('.', 1)[1].lower()
                final_filename = f"{unique_prefix}.{extension}"

                # Ensure 'PROPOSAL_UPLOAD_FOLDER' is defined in config and folder exists
                # Folder creation logic will be in app/__init__.py
                proposal_upload_folder_config = current_app.config.get('PROPOSAL_UPLOAD_FOLDER', 'proposal_uploads')
                upload_folder_abs = os.path.join(current_app.instance_path, proposal_upload_folder_config)

                try:
                    if not os.path.exists(upload_folder_abs):
                         os.makedirs(upload_folder_abs, exist_ok=True) # Create if doesn't exist
                    photo_file.save(os.path.join(upload_folder_abs, final_filename))
                except Exception as e:
                    current_app.logger.error(f"Could not save proposal photo: {str(e)}")
                    return jsonify({'error': _('Could not save proposal photo.')}), 500
            else:
                return jsonify({'error': _('Invalid file type for proposal photo.')}), 400

    new_proposal = BlockProposal(
        proposer_id=current_user.id,
        location_description=location_description,
        climb_description=climb_description,
        proposed_grade=proposed_grade,
        photo_filename_proposal=final_filename,
        status='pending' # Default status
    )

    try:
        db.session.add(new_proposal)
        db.session.commit()
        return jsonify({'message': _('Block proposal submitted successfully.'), 'proposal': serialize_proposal(new_proposal)}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error submitting proposal: {str(e)}")
        return jsonify({'error': _('Failed to submit block proposal due to a server error.')}), 500

@proposals_bp.route('/me', methods=['GET'])
@login_required
def get_my_proposals():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    proposals_pagination = BlockProposal.query.filter_by(proposer_id=current_user.id)\
                                       .order_by(BlockProposal.created_at.desc())\
                                       .paginate(page=page, per_page=per_page, error_out=False)

    proposals_data = [serialize_proposal(p) for p in proposals_pagination.items]

    return jsonify({
        'proposals': proposals_data,
        'total_proposals': proposals_pagination.total,
        'current_page': proposals_pagination.page,
        'total_pages': proposals_pagination.pages,
        'per_page': proposals_pagination.per_page,
        'has_next': proposals_pagination.has_next,
        'has_prev': proposals_pagination.has_prev
    }), 200

# Endpoint to serve proposal photos (similar to block photos)
@proposals_bp.route('/uploads/<filename>', methods=['GET'])
def serve_proposal_uploaded_file(filename):
    proposal_upload_folder_config = current_app.config.get('PROPOSAL_UPLOAD_FOLDER', 'proposal_uploads')
    upload_folder_abs = os.path.join(current_app.instance_path, proposal_upload_folder_config)
    return send_from_directory(upload_folder_abs, filename)
