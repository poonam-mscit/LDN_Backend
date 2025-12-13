"""
SQLAlchemy Models Package

This package contains all database models organized by domain:
- Core Models: User, Property, Job
- Job-Related: AssignmentLog
- User-Related: ClerkAvailability, ClerkInvoice
- Communication: ChatMessage, ChatParticipant, Notification
- System: IntegrationSettings
"""

# Core Models
from app.models.user import User
from app.models.property import Property
from app.models.job import Job

# Job-Related Models
from app.models.assignment_log import AssignmentLog

# User-Related Models
from app.models.availability import ClerkAvailability
from app.models.invoice import ClerkInvoice

# Communication Models
from app.models.chat import ChatMessage, ChatParticipant
from app.models.notification import Notification

# System Models
from app.models.integration import IntegrationSettings

__all__ = [
    # Core Models
    'User',
    'Property',
    'Job',
    # Job-Related
    'AssignmentLog',
    # User-Related
    'ClerkAvailability',
    'ClerkInvoice',
    # Communication
    'ChatMessage',
    'ChatParticipant',
    'Notification',
    # System
    'IntegrationSettings',
]

