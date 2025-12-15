from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

class IntegrationSettings(db.Model):
    """Integration settings model matching database_schema.sql SECTION 3"""
    __tablename__ = 'integration_settings'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = db.Column(db.String(50), default='inventorybase', unique=True)
    
    # OAuth Credentials
    client_id = db.Column(db.String(255), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    token_expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    
    # Scopes
    scope = db.Column(db.Text, default='properties.read')
    
    # Meta
    last_synced_at = db.Column(db.DateTime(timezone=True))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'service_name': self.service_name,
            'client_id': self.client_id,
            'access_token': self.access_token,  # In production, consider masking this
            'refresh_token': self.refresh_token,  # In production, consider masking this
            'token_expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'scope': self.scope,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<IntegrationSettings {self.service_name}>'

