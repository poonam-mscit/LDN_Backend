from flask import Blueprint, request, jsonify
from app import db
from app.models.chat import ChatMessage, ChatParticipant
from app.models.job import Job
from app.utils.auth import require_auth
from datetime import datetime

bp = Blueprint('chat', __name__)

@bp.route('/jobs/<job_id>/messages', methods=['GET'])
@require_auth
def get_messages(job_id):
    """Get all messages for a job"""
    job = Job.query.get_or_404(job_id)
    messages = ChatMessage.query.filter_by(job_id=job_id).order_by(ChatMessage.sent_at).all()
    return jsonify([msg.to_dict() for msg in messages]), 200

@bp.route('/jobs/<job_id>/messages', methods=['POST'])
@require_auth
def send_message(job_id):
    """Send a message in job chat"""
    job = Job.query.get_or_404(job_id)
    data = request.get_json()
    
    # TODO: Get sender_id from authenticated user
    message = ChatMessage(
        job_id=job_id,
        sender_id=data.get('sender_id'),  # Should come from auth token
        content=data.get('content'),
        attachment_url=data.get('attachment_url'),
        is_system_message=data.get('is_system_message', False)
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify(message.to_dict()), 201

@bp.route('/jobs/<job_id>/read', methods=['POST'])
@require_auth
def mark_read(job_id):
    """Mark messages as read for current user"""
    job = Job.query.get_or_404(job_id)
    # TODO: Get user_id from authenticated user
    user_id = request.get_json().get('user_id')
    
    participant = ChatParticipant.query.filter_by(job_id=job_id, user_id=user_id).first()
    if not participant:
        participant = ChatParticipant(job_id=job_id, user_id=user_id)
        db.session.add(participant)
    
    participant.last_read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(participant.to_dict()), 200

@bp.route('/jobs/<job_id>/unread-count', methods=['GET'])
@require_auth
def get_unread_count(job_id):
    """Get unread message count for current user"""
    # TODO: Get user_id from authenticated user
    user_id = request.args.get('user_id')
    
    participant = ChatParticipant.query.filter_by(job_id=job_id, user_id=user_id).first()
    last_read = participant.last_read_at if participant else None
    
    query = ChatMessage.query.filter_by(job_id=job_id)
    if last_read:
        query = query.filter(ChatMessage.sent_at > last_read)
    
    unread_count = query.count()
    return jsonify({'unread_count': unread_count}), 200

