from app import app
import logging
import os
from pathlib import Path

if __name__ == "__main__":
    # Set up logging
    log_dir = Path(__file__).resolve().parents[1] / "logs"
    
    # Configure logging handlers based on environment
    handlers = [logging.StreamHandler()]  # Always log to stdout for Railway
    
    # Add file logging for local development only
    if not os.getenv("RAILWAY_ENVIRONMENT"):
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "flask_webapp.log"
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Set Flask app logger
    app.logger.setLevel(logging.INFO)
    
    # Get port from environment (Railway sets PORT automatically)
    port = int(os.environ.get("PORT", 8080))
    host = "0.0.0.0"  # Bind to all interfaces for Railway
    
    app.logger.info(f"Flask app starting on {host}:{port}...")
    app.logger.info(f"Environment: {'Railway' if os.getenv('RAILWAY_ENVIRONMENT') else 'Local'}")
    
    app.run(host=host, port=port, debug=True)
