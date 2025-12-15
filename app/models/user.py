from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

class User(db.Model):
    """User model matching database_schema.sql SECTION 2"""
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication (SOW 3.1)
    cognito_sub = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    # Profile Info
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20))
    role = db.Column(db.Enum('admin', 'clerk', 'agent', name='user_role_enum'), nullable=False)
    
    # Address Information (Required for clerks to go on shift)
    address_line_1 = db.Column(db.String(255))
    address_line_2 = db.Column(db.String(255))
    city = db.Column(db.String(100))
    postcode = db.Column(db.String(20))
    address_file_url = db.Column(db.Text)
    
    # System Access & Availability (SOW 3.2)
    is_active = db.Column(db.Boolean, default=True)
    is_on_shift = db.Column(db.Boolean, default=False)
    
    # Live Location (SOW 3.2)
    current_lat = db.Column(db.Numeric(10, 8))
    current_lng = db.Column(db.Numeric(11, 8))
    last_location_update = db.Column(db.DateTime(timezone=True))
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    assigned_jobs = db.relationship('Job', foreign_keys='Job.assigned_clerk_id', backref='assigned_clerk', lazy='dynamic')
    created_jobs = db.relationship('Job', foreign_keys='Job.created_by_user_id', backref='created_by', lazy='dynamic')
    agent_jobs = db.relationship('Job', foreign_keys='Job.assigned_agent_id', backref='assigned_agent', lazy='dynamic')
    availability_records = db.relationship('ClerkAvailability', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('ClerkInvoice', backref='clerk', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    chat_messages = db.relationship('ChatMessage', backref='sender', lazy='dynamic')
    chat_participations = db.relationship('ChatParticipant', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'cognito_sub': self.cognito_sub,
            'email': self.email,
            'full_name': self.full_name,
            'phone_number': self.phone_number,
            'role': self.role,
            'is_active': self.is_active,
            'is_on_shift': self.is_on_shift,
            'address_line_1': self.address_line_1,
            'address_line_2': self.address_line_2,
            'city': self.city,
            'postcode': self.postcode,
            'address_file_url': self.address_file_url,
            'current_lat': float(self.current_lat) if self.current_lat else None,
            'current_lng': float(self.current_lng) if self.current_lng else None,
            'last_location_update': self.last_location_update.isoformat() if self.last_location_update else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<User {self.email}>'

