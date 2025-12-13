from dotenv import load_dotenv
load_dotenv()  # Load .env file

from app import create_app, db
from config import config
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = create_app(config.get(os.environ.get('FLASK_ENV', 'development')))

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'app': app}

if __name__ == '__main__':
    # Ensure database is initialized before running
    with app.app_context():
        try:
            from app.utils.db_init import initialize_database
            logger.info("Verifying database initialization...")
            if initialize_database():
                logger.info("✓ Database ready - starting Flask application")
            else:
                logger.warning("⚠ Database initialization had warnings - starting Flask application anyway")
        except Exception as e:
            logger.error(f"✗ Database initialization error: {e}")
            logger.info("Starting Flask application anyway (database may need manual setup)")
    
    logger.info("=" * 60)
    logger.info("Flask application starting on http://0.0.0.0:5000")
    logger.info("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)

