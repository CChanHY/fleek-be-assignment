import logging
import sys
from typing import Optional
from app.core.config import settings


def setup_logging(log_level: Optional[str] = None) -> None:
    level = getattr(logging, (log_level or settings.log_level).upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("tortoise").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    if settings.debug:
        logging.getLogger("app").setLevel(logging.DEBUG)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at {level} level")