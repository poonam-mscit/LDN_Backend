from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

class ChatMessage(db.Model):
    """Chat message model matching database_schema.sql SECTION 7"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = db.Column(UUID(as_uuid=True), db.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    sender_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'))
    content = db.Column(db.Text)
    attachment_url = db.Column(db.Text)
    sent_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_system_message = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'job_id': str(self.job_id),
            'sender_id': str(self.sender_id) if self.sender_id else None,
            'content': self.content,
            'attachment_url': self.attachment_url,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'is_system_message': self.is_system_message
        }
    
    def __repr__(self):
        return f'<ChatMessage {self.id}>'

class ChatParticipant(db.Model):
    """Chat participant model for tracking read status"""
    __tablename__ = 'chat_participants'
    
    job_id = db.Column(UUID(as_uuid=True), db.ForeignKey('jobs.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    last_read_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'job_id': str(self.job_id),
            'user_id': str(self.user_id),
            'last_read_at': self.last_read_at.isoformat() if self.last_read_at else None
        }
    
    def __repr__(self):
        return f'<ChatParticipant job={self.job_id} user={self.user_id}>'

