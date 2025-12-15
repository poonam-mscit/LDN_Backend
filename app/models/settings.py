from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class GeneralSettings(db.Model):
    """General settings model matching database_schema.sql SECTION 10"""
    __tablename__ = 'general_settings'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Company Details
    company_name = db.Column(db.String(255), nullable=False, default='LDN Portal Ltd')
    email = db.Column(db.String(255), nullable=False, default='admin@ldnportal.com')
    telephone = db.Column(db.String(20))
    website = db.Column(db.String(255))
    
    # Address
    address_line_1 = db.Column(db.String(255))
    address_line_2 = db.Column(db.String(255))
    city = db.Column(db.String(100))
    postcode = db.Column(db.String(20))
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'company_name': self.company_name,
            'email': self.email,
            'telephone': self.telephone,
            'website': self.website,
            'address_line_1': self.address_line_1,
            'address_line_2': self.address_line_2,
            'city': self.city,
            'postcode': self.postcode,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<GeneralSettings {self.company_name}>'

