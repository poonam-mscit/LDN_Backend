from app import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime, timezone

class Property(db.Model):
    """Property model matching database_schema.sql SECTION 4"""
    __tablename__ = 'properties'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # External Identifiers (InventoryBase API)
    inventorybase_id = db.Column(db.Integer, unique=True, nullable=False)
    reference_number = db.Column(db.String(100))
    uprn = db.Column(db.String(100))
    parent_property_id = db.Column(db.Integer)
    
    # Address Details
    address_line_1 = db.Column(db.String(255))
    address_line_2 = db.Column(db.String(255))
    city = db.Column(db.String(100))
    postcode = db.Column(db.String(20), nullable=False, index=True)
    
    # Geo-location (Critical for SOW 3.2)
    latitude = db.Column(db.Numeric(10, 8), index=True)
    longitude = db.Column(db.Numeric(11, 8), index=True)
    
    # Attributes
    property_type = db.Column(db.String(50))
    bedrooms = db.Column(db.Integer, default=0)
    bathrooms = db.Column(db.Integer, default=0)
    has_parking = db.Column(db.Boolean, default=False)
    client_name = db.Column(db.String(255))
    
    # Flexible Data (JSONB)
    tags = db.Column(JSONB, default=[])
    custom_fields = db.Column(JSONB, default={})
    notes = db.Column(db.Text)
    
    # Meter Location
    meter_location_notes = db.Column(db.Text)
    
    # Meta
    status = db.Column(db.String(50), default='active')
    is_active = db.Column(db.Boolean, default=True)
    last_synced_at = db.Column(db.DateTime(timezone=True))
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    jobs = db.relationship('Job', backref='property', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'inventorybase_id': self.inventorybase_id,
            'reference_number': self.reference_number,
            'uprn': self.uprn,
            'parent_property_id': self.parent_property_id,
            'address_line_1': self.address_line_1,
            'address_line_2': self.address_line_2,
            'city': self.city,
            'postcode': self.postcode,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'property_type': self.property_type,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'has_parking': self.has_parking,
            'client_name': self.client_name,
            'tags': self.tags,
            'custom_fields': self.custom_fields,
            'notes': self.notes,
            'meter_location_notes': self.meter_location_notes,
            'status': self.status,
            'is_active': self.is_active,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Property {self.reference_number or self.id}>'

