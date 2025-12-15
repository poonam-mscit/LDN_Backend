from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app import db
from app.models.user import User
from app.utils.auth import require_auth, require_role
import os
import uuid
from datetime import datetime, timezone

bp = Blueprint('users', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/', methods=['GET'])
@require_auth
def get_users():
    """Get all users"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    role = request.args.get('role')
    
    query = User.query
    if role:
        query = query.filter_by(role=role)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    return jsonify({
        'users': [user.to_dict() for user in users],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@bp.route('/<user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """Get user by ID"""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200

@bp.route('/<user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    """Update user (self-service or admin)"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed fields (self-service)
        if 'full_name' in data:
            user.full_name = data['full_name'].strip() if data['full_name'] else None
        
        if 'phone_number' in data:
            user.phone_number = data['phone_number'].strip() if data['phone_number'] else None
        
        # Admin-only fields (check role in decorator would be better, but keeping simple for now)
        # For now, allow is_active if provided (should be admin-only in production)
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        # Update address fields
        if 'address_line_1' in data:
            user.address_line_1 = data['address_line_1'].strip() if data['address_line_1'] else None
        if 'address_line_2' in data:
            user.address_line_2 = data['address_line_2'].strip() if data['address_line_2'] else None
        if 'city' in data:
            user.city = data['city'].strip() if data['city'] else None
        if 'postcode' in data:
            user.postcode = data['postcode'].strip() if data['postcode'] else None
        if 'address_file_url' in data:
            user.address_file_url = data['address_file_url'] if data['address_file_url'] else None
        
        # Validate address before allowing shift toggle for clerks
        if 'is_on_shift' in data:
            if data['is_on_shift'] and user.role == 'clerk':
                # Check if address is complete
                if not user.address_line_1 or not user.city or not user.postcode:
                    return jsonify({
                        'error': 'Address verification required',
                        'message': 'Please complete your address information (Address Line 1, City, and Postcode) before going on shift. Address verification is mandatory for clerks.'
                    }), 400
                # Also check for address file if available
                if not user.address_file_url:
                    return jsonify({
                        'error': 'Address file required',
                        'message': 'Please upload proof of address before going on shift. Address verification is mandatory for clerks.'
                    }), 400
            user.is_on_shift = data['is_on_shift']
        
        if 'current_lat' in data and 'current_lng' in data:
            user.current_lat = data['current_lat']
            user.current_lng = data['current_lng']
            user.last_location_update = datetime.now(timezone.utc)
        
        # Commit changes
        db.session.commit()
        
        # Refresh the user object to get the latest data including updated_at
        db.session.refresh(user)
        
        return jsonify(user.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating user {user_id}: {str(e)}')
        return jsonify({'error': 'Failed to update user', 'message': str(e)}), 500

@bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current authenticated user"""
    # TODO: Extract user from token
    return jsonify({'message': 'Get current user endpoint'}), 200

@bp.route('/<user_id>/location', methods=['PUT'])
@require_auth
def update_location(user_id):
    """Update user location (for mobile app)"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    user.current_lat = data.get('lat')
    user.current_lng = data.get('lng')
    user.last_location_update = datetime.utcnow()
    
    db.session.commit()
    return jsonify(user.to_dict()), 200

@bp.route('/<user_id>/upload-address', methods=['POST'])
@require_auth
def upload_address_file(user_id):
    """Upload address verification file"""
    user = User.query.get_or_404(user_id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PDF, JPG, JPEG, PNG'}), 400
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    
    # Create upload directory if it doesn't exist
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    address_folder = os.path.join(upload_folder, 'addresses')
    os.makedirs(address_folder, exist_ok=True)
    
    # Save file
    file_path = os.path.join(address_folder, unique_filename)
    file.save(file_path)
    
    # Generate URL (in production, this would be an S3 URL)
    file_url = f"/uploads/addresses/{unique_filename}"
    
    # Update user's address file URL
    user.address_file_url = file_url
    db.session.commit()
    
    return jsonify({
        'message': 'Address file uploaded successfully',
        'file_url': file_url,
        'user': user.to_dict()
    }), 200

@bp.route('/<user_id>', methods=['DELETE'])
@require_auth
@require_role('admin')
def delete_user(user_id):
    """Delete user (admin only)"""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200

