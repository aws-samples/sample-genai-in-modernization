"""
Logging configuration for agent workflow
"""
import logging
import os
from datetime import datetime
from config import output_folder_dir_path

def setup_logging():
    """
    Configure logging to both console and file
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(output_folder_dir_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'agent_execution_{timestamp}.log')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # Also print to console
        ]
    )
    
    logger = logging.getLogger('AgentWorkflow')
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger, log_file
