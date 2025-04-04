# run.py
from app import create_app
import os
import logging
from dotenv import load_dotenv

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create the Flask application
logger.info("Initializing Flask application")
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Get host and port from environment or use defaults
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    
    logger.info(f"Starting Flask app on http://{host}:{port}")
    logger.info(f"Debug mode: {app.debug}")
    
    app.run(host=host, port=port)