from flask import Blueprint, request, jsonify
from app import db
from app.models.chat import ChatMessage, ChatParticipant
from app.models.job import Job
from app.models.user import User
from app.utils.auth import require_auth
from app.utils.helpers import create_notification
from datetime import datetime, timezone

bp = Blueprint('chat', __name__)

@bp.route('/jobs/<job_id>/messages', methods=['GET'])
@require_auth
def get_messages(job_id):
    """
    Get all messages for a job
    ---
    tags:
      - Chat
    parameters:
      - in: path
        name: job_id
        required: true
        schema:
          type: string
        description: Job ID
    security:
      - Bearer: []
    responses:
      200:
        description: List of messages
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
      404:
        description: Job not found
      401:
        description: Unauthorized
    """
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
    """
    Send a message in job chat
    ---
    tags:
      - Chat
    parameters:
      - in: path
        name: job_id
        required: true
        schema:
          type: string
        description: Job ID
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - content
            properties:
              content:
                type: string
              attachment_url:
                type: string
              is_system_message:
                type: boolean
    responses:
      201:
        description: Message sent successfully
        content:
          application/json:
            schema:
              type: object
      404:
        description: Job or user not found
      401:
        description: Unauthorized
    """
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
    db.session.flush()  # Get message.id before commit
    
    # Only create notifications for non-system messages
    is_system_message = data.get('is_system_message', False)
    
    if not is_system_message:
        # Get sender info for notification
        sender_name = user.full_name if user else 'Someone'
        property_address = job.property.address_line_1 if job.property else 'Property'
        if job.property and job.property.address_line_2:
            property_address += f", {job.property.address_line_2}"
        
        # Determine who should receive notifications (all job participants except sender)
        notification_recipients = []
        
        # Add assigned clerk (if not the sender)
        if job.assigned_clerk_id and job.assigned_clerk_id != user.id:
            notification_recipients.append(job.assigned_clerk_id)
        
        # Add assigned agent (if not the sender)
        if job.assigned_agent_id and job.assigned_agent_id != user.id:
            notification_recipients.append(job.assigned_agent_id)
        
        # Add all admin users (admins can see all jobs)
        admin_users = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admin_users:
            if admin.id != user.id and admin.id not in notification_recipients:
                notification_recipients.append(admin.id)
        
        # Create notifications for all recipients
        message_content = data.get('content', '')
        message_preview = message_content[:100]  # First 100 characters
        if len(message_content) > 100:
            message_preview += '...'
        
        for recipient_id in notification_recipients:
            create_notification(
                user_id=recipient_id,
                notification_type='CHAT_MESSAGE',
                title=f'New Message from {sender_name}',
                body=f'New message in job chat for {property_address}: {message_preview}',
                job_id=job_id,
                channel='in_app'
            )
    
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
    """
    Mark messages as read for current user
    ---
    tags:
      - Chat
    parameters:
      - in: path
        name: job_id
        required: true
        schema:
          type: string
        description: Job ID
    security:
      - Bearer: []
    responses:
      200:
        description: Messages marked as read
        content:
          application/json:
            schema:
              type: object
      404:
        description: Job or user not found
      401:
        description: Unauthorized
    """
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
    
    participant.last_read_at = datetime.now(timezone.utc)
    db.session.commit()
    
    return jsonify(participant.to_dict()), 200

@bp.route('/jobs/<job_id>/unread-count', methods=['GET'])
@require_auth
def get_unread_count(job_id):
    """
    Get unread message count for current user
    ---
    tags:
      - Chat
    parameters:
      - in: path
        name: job_id
        required: true
        schema:
          type: string
        description: Job ID
    security:
      - Bearer: []
    responses:
      200:
        description: Unread message count
        content:
          application/json:
            schema:
              type: object
              properties:
                unread_count:
                  type: integer
      404:
        description: User not found
      401:
        description: Unauthorized
    """
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

