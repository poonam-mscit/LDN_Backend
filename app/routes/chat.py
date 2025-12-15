from flask import Blueprint, request, jsonify
from app import db
from app.models.chat import ChatMessage, ChatParticipant
from app.models.job import Job
from app.models.user import User
from app.utils.auth import require_auth
from datetime import datetime

bp = Blueprint('chat', __name__)

@bp.route('/jobs/<job_id>/messages', methods=['GET'])
@require_auth
def get_messages(job_id):
    """Get all messages for a job"""
    job = Job.query.get_or_404(job_id)
    messages = ChatMessage.query.filter_by(job_id=job_id).order_by(ChatMessage.sent_at).all()
    
    # Include sender information for each message
    messages_data = []
    for msg in messages:
        msg_dict = msg.to_dict()
        if msg.sender_id:
            sender = User.query.get(msg.sender_id)
            if sender:
                msg_dict['sender_name'] = sender.full_name
                msg_dict['sender_role'] = sender.role
            else:
                msg_dict['sender_name'] = None
                msg_dict['sender_role'] = None
        else:
            msg_dict['sender_name'] = None
            msg_dict['sender_role'] = None
        messages_data.append(msg_dict)
    
    return jsonify(messages_data), 200

@bp.route('/jobs/<job_id>/messages', methods=['POST'])
@require_auth
def send_message(job_id):
    """Send a message in job chat"""
    job = Job.query.get_or_404(job_id)
    data = request.get_json()
    current_user = request.current_user
    
    # Get user_id from authenticated user
    user = User.query.filter_by(cognito_sub=current_user.get('cognito_sub')).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    message = ChatMessage(
        job_id=job_id,
        sender_id=user.id,
        content=data.get('content'),
        attachment_url=data.get('attachment_url'),
        is_system_message=data.get('is_system_message', False)
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Include sender information in response
    msg_dict = message.to_dict()
    if message.sender_id:
        sender = User.query.get(message.sender_id)
        if sender:
            msg_dict['sender_name'] = sender.full_name
            msg_dict['sender_role'] = sender.role
        else:
            msg_dict['sender_name'] = None
            msg_dict['sender_role'] = None
    else:
        msg_dict['sender_name'] = None
        msg_dict['sender_role'] = None
    
    return jsonify(msg_dict), 201

@bp.route('/jobs/<job_id>/read', methods=['POST'])
@require_auth
def mark_read(job_id):
    """Mark messages as read for current user"""
    job = Job.query.get_or_404(job_id)
    current_user = request.current_user
    
    # Get user_id from authenticated user
    user = User.query.filter_by(cognito_sub=current_user.get('cognito_sub')).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    participant = ChatParticipant.query.filter_by(job_id=job_id, user_id=user.id).first()
    if not participant:
        participant = ChatParticipant(job_id=job_id, user_id=user.id)
        db.session.add(participant)
    
    participant.last_read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(participant.to_dict()), 200

@bp.route('/jobs/<job_id>/unread-count', methods=['GET'])
@require_auth
def get_unread_count(job_id):
    """Get unread message count for current user"""
    current_user = request.current_user
    
    # Get user_id from authenticated user
    user = User.query.filter_by(cognito_sub=current_user.get('cognito_sub')).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    participant = ChatParticipant.query.filter_by(job_id=job_id, user_id=user.id).first()
    last_read = participant.last_read_at if participant else None
    
    query = ChatMessage.query.filter_by(job_id=job_id)
    if last_read:
        query = query.filter(ChatMessage.sent_at > last_read)
    
    unread_count = query.count()
    return jsonify({'unread_count': unread_count}), 200

