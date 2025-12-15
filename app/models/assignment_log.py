from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

class AssignmentLog(db.Model):
    """Assignment log model matching database_schema.sql SECTION 6"""
    __tablename__ = 'assignment_logs'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = db.Column(UUID(as_uuid=True), db.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    
    # Previous and new clerk assignments
    previous_clerk_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'))
    new_clerk_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'))
    
    # Action details
    action_type = db.Column(db.String(50))  # 'AUTO_ASSIGN', 'MANUAL_OVERRIDE'
    triggered_by_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'))
    reason = db.Column(db.Text)
    
    # Timestamp
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'job_id': str(self.job_id),
            'previous_clerk_id': str(self.previous_clerk_id) if self.previous_clerk_id else None,
            'new_clerk_id': str(self.new_clerk_id) if self.new_clerk_id else None,
            'action_type': self.action_type,
            'triggered_by_user_id': str(self.triggered_by_user_id) if self.triggered_by_user_id else None,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<AssignmentLog {self.id}>'

