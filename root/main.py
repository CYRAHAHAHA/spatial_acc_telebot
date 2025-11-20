from app import app
import logging
from pathlib import Path

if __name__ == "__main__":
    # Set up logging
    log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "flask_webapp.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    # Set Flask app logger
    app.logger.setLevel(logging.INFO)
    
    app.logger.info("Flask app starting on port 8080...")
    app.run(port=8080, debug=False)
