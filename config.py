import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:password@localhost/ldn_portal'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # AWS Cognito Configuration
    AWS_REGION = os.environ.get('AWS_REGION') or 'us-east-1'
    COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID') or ''
    COGNITO_CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID') or ''
    COGNITO_CLIENT_SECRET = os.environ.get('COGNITO_CLIENT_SECRET') or ''
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # InventoryBase Integration
    INVENTORYBASE_CLIENT_ID = os.environ.get('INVENTORYBASE_CLIENT_ID') or ''
    INVENTORYBASE_CLIENT_SECRET = os.environ.get('INVENTORYBASE_CLIENT_SECRET') or ''
    INVENTORYBASE_API_URL = os.environ.get('INVENTORYBASE_API_URL') or 'https://api.inventorybase.com'
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    
    # Pagination
    POSTS_PER_PAGE = 20
    
    # CORS Configuration
    # Comma-separated list of allowed origins, or '*' for all origins
    # Example: 'http://localhost:5173,http://localhost:3000,https://yourdomain.com'
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '*').split(',')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/ldn_portal_test'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

