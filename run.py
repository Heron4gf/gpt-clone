# run.py
from app import create_app
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create the Flask application
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Get host and port from environment or use defaults
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    
    print(f" * Starting Flask app on http://{host}:{port}")
    print(f" * Debug mode: {app.debug}")
    
    app.run(host=host, port=port)
