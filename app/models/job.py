from app import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime, timezone
from app.utils.helpers import convert_handover_snake_to_camel

class Job(db.Model):
    """Job model matching database_schema.sql SECTION 5"""
    __tablename__ = 'jobs'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    property_id = db.Column(UUID(as_uuid=True), db.ForeignKey('properties.id'), nullable=False)
    created_by_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    assigned_clerk_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), index=True)
    assigned_agent_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    
    # Logistics Data (SOW 3.2)
    job_type = db.Column(db.String(100), default='Logistics_Visit')
    priority = db.Column(db.Enum('low', 'normal', 'high', 'emergency', name='priority_enum'), default='normal')
    appointment_date = db.Column(db.DateTime(timezone=True), nullable=False)
    estimated_duration_minutes = db.Column(db.Integer, default=60)
    
    # Access & Instructions (SOW 2.0)
    access_instructions = db.Column(db.Text)
    key_location = db.Column(db.String(255))
    key_release_received = db.Column(db.Boolean, default=False)
    admin_attachments = db.Column(JSONB, default=[])
    admin_notes = db.Column(db.Text)
    
    # Booking Questions (Client Requirement)
    booking_questions = db.Column(JSONB, default={})
    
    # Status Workflow (SOW 3.3)
    status = db.Column(db.Enum(
        'pending_assignment',
        'assigned',
        'on_route',
        'in_progress',
        'completed',
        'cancelled',
        name='job_status_enum'
    ), default='pending_assignment', index=True)
    
    # The Logistics Tracker (SOW 3.6)
    on_route_at = db.Column(db.DateTime(timezone=True))
    check_in_at = db.Column(db.DateTime(timezone=True))
    check_in_lat = db.Column(db.Numeric(10, 8))
    check_in_lng = db.Column(db.Numeric(11, 8))
    location_warning_flag = db.Column(db.Boolean, default=False)
    
    # Handover Data (Digital Proof)
    handover_data = db.Column(JSONB, default={})
    
    # Departure
    check_out_at = db.Column(db.DateTime(timezone=True))
    check_out_lat = db.Column(db.Numeric(10, 8))
    check_out_lng = db.Column(db.Numeric(11, 8))
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    chat_messages = db.relationship('ChatMessage', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    chat_participants = db.relationship('ChatParticipant', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='job', lazy='dynamic')
    assignment_logs = db.relationship('AssignmentLog', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'property_id': str(self.property_id),
            'created_by_user_id': str(self.created_by_user_id) if self.created_by_user_id else None,
            'assigned_clerk_id': str(self.assigned_clerk_id) if self.assigned_clerk_id else None,
            'assigned_agent_id': str(self.assigned_agent_id) if self.assigned_agent_id else None,
            'job_type': self.job_type,
            'priority': self.priority,
            'appointment_date': self.appointment_date.isoformat() if self.appointment_date else None,
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'access_instructions': self.access_instructions,
            'key_location': self.key_location,
            'key_release_received': self.key_release_received,
            'admin_attachments': self.admin_attachments,
            'admin_notes': self.admin_notes,
            'booking_questions': self.booking_questions,
            'status': self.status,
            'on_route_at': self.on_route_at.isoformat() if self.on_route_at else None,
            'check_in_at': self.check_in_at.isoformat() if self.check_in_at else None,
            'check_in_lat': float(self.check_in_lat) if self.check_in_lat else None,
            'check_in_lng': float(self.check_in_lng) if self.check_in_lng else None,
            'location_warning_flag': self.location_warning_flag,
            # Convert handover_data from database snake_case to frontend camelCase
            'handover_data': convert_handover_snake_to_camel(self.handover_data) if self.handover_data else {},
            'check_out_at': self.check_out_at.isoformat() if self.check_out_at else None,
            'check_out_lat': float(self.check_out_lat) if self.check_out_lat else None,
            'check_out_lng': float(self.check_out_lng) if self.check_out_lng else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Job {self.id}>'

