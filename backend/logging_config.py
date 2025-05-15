import logging
import os

def setup_logging():
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', None)
    log_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

def get_logger(name=None):
    return logging.getLogger(name) 