import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

GB = 1024 * 1024 * 1024


def setup_loggers():

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    # ==========================
    # TECHNICAL LOGGER
    # ==========================
    tech_logger = logging.getLogger("technical")
    tech_logger.setLevel(logging.DEBUG)

    if not tech_logger.handlers:
        tech_handler = RotatingFileHandler(
            "logs/technical.log",
            maxBytes=100 * GB,
            backupCount=3
        )
        tech_handler.setFormatter(formatter)
        tech_logger.addHandler(tech_handler)

    # ==========================
    # PRODUCTION LOGGER
    # ==========================
    prod_logger = logging.getLogger("production")
    prod_logger.setLevel(logging.INFO)

    if not prod_logger.handlers:
        prod_handler = RotatingFileHandler(
            "logs/production.log",
            maxBytes=200 * GB,
            backupCount=2
        )
        prod_handler.setFormatter(formatter)
        prod_logger.addHandler(prod_handler)

    return tech_logger, prod_logger