from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class Notification(db.Model):
    """Notification model matching database_schema.sql SECTION 8"""
    __tablename__ = 'notifications'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    related_job_id = db.Column(UUID(as_uuid=True), db.ForeignKey('jobs.id'))
    
    # Content
    type = db.Column(db.String(50))  # 'JOB_ASSIGNED', 'OVERDUE', etc.
    title = db.Column(db.String(255))
    body = db.Column(db.Text)
    
    # Channel & Delivery Tracking (SOW 3.4 Compliance)
    channel = db.Column(db.Enum('in_app', 'email', 'sms', name='notification_channel_enum'), default='in_app')
    delivery_status = db.Column(db.String(50), default='sent')  # 'sent', 'failed', 'delivered'
    
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'related_job_id': str(self.related_job_id) if self.related_job_id else None,
            'type': self.type,
            'title': self.title,
            'body': self.body,
            'channel': self.channel,
            'delivery_status': self.delivery_status,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Notification {self.id}>'

