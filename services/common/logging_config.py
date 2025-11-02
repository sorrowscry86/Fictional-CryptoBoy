"""
Logging Configuration for CryptoBoy Microservices
Provides consistent logging setup across all services
"""

import logging
import os
import sys


def setup_logging(service_name: str, level: str = None, log_format: str = None) -> logging.Logger:
    """
    Setup logging for a microservice

    Args:
        service_name: Name of the service (used in log messages)
        level: Log level (defaults to env LOG_LEVEL or 'INFO')
        log_format: Custom log format (optional)

    Returns:
        Configured logger instance
    """
    # Get log level from environment or default
    level = level or os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Default format with service name
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - [%(levelname)s] - " f"{service_name} - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=log_level, format=log_format, datefmt="%Y-%m-%d %H:%M:%S", handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Get logger for this service
    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)

    # Reduce verbosity of external libraries
    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    logger.info(f"{service_name} logging initialized at {level} level")

    return logger
