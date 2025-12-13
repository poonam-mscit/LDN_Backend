"""
Database Initialization Utility

This module handles automatic creation of:
- PostgreSQL extensions
- Custom ENUM types
- All database tables

All operations are idempotent - they won't fail if objects already exist.
"""

from app import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def create_postgres_extensions():
    """Create PostgreSQL extensions if they don't exist"""
    try:
        # Create uuid-ossp extension for UUID generation
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        db.session.commit()
        logger.info("PostgreSQL extensions created/verified successfully")
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Could not create PostgreSQL extensions (may already exist): {e}")


def create_enums():
    """Create PostgreSQL ENUM types if they don't exist"""
    enums = [
        {
            'name': 'user_role_enum',
            'values': ['admin', 'clerk', 'agent']
        },
        {
            'name': 'priority_enum',
            'values': ['low', 'normal', 'high', 'emergency']
        },
        {
            'name': 'job_status_enum',
            'values': ['pending_assignment', 'assigned', 'on_route', 'in_progress', 'completed', 'cancelled']
        },
        {
            'name': 'notification_channel_enum',
            'values': ['in_app', 'email', 'sms']
        }
    ]
    
    for enum_def in enums:
        try:
            enum_name = enum_def['name']
            enum_values = "', '".join(enum_def['values'])
            
            # Use DO block to handle "already exists" gracefully
            query = f"""
            DO $$ BEGIN
                CREATE TYPE {enum_name} AS ENUM ('{enum_values}');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
            db.session.execute(text(query))
            db.session.commit()
            logger.info(f"ENUM {enum_name} created/verified successfully")
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Could not create ENUM {enum_def['name']} (may already exist): {e}")


def create_all_tables():
    """Create all database tables if they don't exist"""
    try:
        # Import all models to ensure SQLAlchemy knows about them
        from app.models import (
            User, Property, Job, AssignmentLog,
            ClerkAvailability, ClerkInvoice,
            ChatMessage, ChatParticipant, Notification,
            IntegrationSettings
        )
        
        # Create all tables (idempotent - won't recreate existing tables)
        db.create_all()
        logger.info("All database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise


def initialize_database():
    """
    Main initialization function that sets up the entire database.
    This function is idempotent and safe to call multiple times.
    """
    try:
        logger.info("Starting database initialization...")
        
        # Step 1: Create PostgreSQL extensions
        create_postgres_extensions()
        
        # Step 2: Create ENUM types
        create_enums()
        
        # Step 3: Create all tables
        create_all_tables()
        
        logger.info("Database initialization completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        db.session.rollback()
        return False

