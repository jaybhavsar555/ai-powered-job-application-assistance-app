import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Adjust Uvicorn log levels to avoid duplicate/spammy logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("ai_job_assistant")
