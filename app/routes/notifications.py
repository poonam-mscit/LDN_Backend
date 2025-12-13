from flask import Blueprint, request, jsonify
from app import db
from app.models.notification import Notification
from app.utils.auth import require_auth

bp = Blueprint('notifications', __name__)

@bp.route('/', methods=['GET'])
@require_auth
def get_notifications():
    """Get notifications for current user"""
    # TODO: Get user_id from authenticated user
    user_id = request.args.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    query = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(is_read=False)
    
    pagination = query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    notifications = pagination.items
    
    return jsonify({
        'notifications': [notif.to_dict() for notif in notifications],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@bp.route('/<notification_id>/read', methods=['PUT'])
@require_auth
def mark_notification_read(notification_id):
    """Mark notification as read"""
    notification = Notification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()
    return jsonify(notification.to_dict()), 200

@bp.route('/read-all', methods=['PUT'])
@require_auth
def mark_all_read():
    """Mark all notifications as read for current user"""
    # TODO: Get user_id from authenticated user
    user_id = request.get_json().get('user_id')
    
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'message': 'All notifications marked as read'}), 200

@bp.route('/unread-count', methods=['GET'])
@require_auth
def get_unread_count():
    """Get unread notification count for current user"""
    # TODO: Get user_id from authenticated user
    user_id = request.args.get('user_id')
    
    count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({'unread_count': count}), 200

