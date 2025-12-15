from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

class ClerkInvoice(db.Model):
    """Clerk invoice model matching database_schema.sql SECTION 9"""
    __tablename__ = 'clerk_invoices'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Month period (e.g., '2024-11-01' represents November 2024)
    month_period = db.Column(db.Date, nullable=False)
    
    # Submission tracking
    submitted_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(50), default='submitted')  # 'submitted', 'paid', 'rejected'
    
    # Optional fields
    invoice_url = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('clerk_id', 'month_period', name='_clerk_month_uc'),)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'clerk_id': str(self.clerk_id),
            'month_period': self.month_period.isoformat() if self.month_period else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'status': self.status,
            'invoice_url': self.invoice_url,
            'admin_notes': self.admin_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ClerkInvoice {self.id}>'

