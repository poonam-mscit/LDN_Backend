from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=None):
    """Application factory pattern"""
    if config_class is None:
        from config import Config
        config_class = Config
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configure CORS with allowed origins from config
    # If '*' is in the list, allow all origins (development)
    # Otherwise, use the specific origins (production)
    cors_origins = app.config.get('CORS_ALLOWED_ORIGINS', ['*'])
    if '*' in cors_origins:
        CORS(app, resources={r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": True
        }})
    else:
        CORS(app, resources={r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": True
        }})
    
    # Register blueprints - Clean resource-based structure
    from app.routes import auth, users, jobs, properties, invoices, availability, chat, notifications, settings
    
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(users.bp, url_prefix='/api/users')
    app.register_blueprint(jobs.bp, url_prefix='/api/jobs')
    app.register_blueprint(properties.bp, url_prefix='/api/properties')
    app.register_blueprint(invoices.bp, url_prefix='/api/invoices')
    app.register_blueprint(availability.bp, url_prefix='/api/availability')
    app.register_blueprint(chat.bp, url_prefix='/api/chat')
    app.register_blueprint(notifications.bp, url_prefix='/api/notifications')
    app.register_blueprint(settings.bp, url_prefix='/api/settings')
    
    return app

