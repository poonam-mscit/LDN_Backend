from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, time, timezone

class ClerkAvailability(db.Model):
    """Clerk availability model matching database_schema.sql SECTION 2.5"""
    __tablename__ = 'clerk_availability'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # The specific date the clerk is available/unavailable
    available_date = db.Column(db.Date, nullable=False, index=True)
    
    # TRUE = Clerk can work this day, FALSE = Blocked off
    is_available = db.Column(db.Boolean, default=True, index=True)
    
    # Optional: Specific hours (defaults to full day 08:00-18:00)
    start_time = db.Column(db.Time, default=time(8, 0))
    end_time = db.Column(db.Time, default=time(18, 0))
    
    # Postcode for this availability date (used for location-based job matching)
    # Pre-filled from user profile but can be edited per date
    postcode = db.Column(db.String(20))
    
    # Notes
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'available_date', name='_user_date_uc'),)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'available_date': self.available_date.isoformat() if self.available_date else None,
            'is_available': self.is_available,
            'start_time': self.start_time.strftime('%H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M:%S') if self.end_time else None,
            'postcode': self.postcode,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ClerkAvailability {self.id}>'

