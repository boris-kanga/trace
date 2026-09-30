import logging
import logging.config

import os


def get_logger(name):
    logger = logging.getLogger(name)
    return logger


def set_up_logging(log_dir: str):
    os.makedirs(str(log_dir), exist_ok=True)
    log_dir = str(log_dir)
    log_dir = os.path.join(log_dir, "app.log")

    conf = {
        'version': 1,
        'formatters': {
            'console': {
                'format': '[%(name)s] [%(levelname)s] %(message)s',
            },
            "file": {
                "format": "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'console',
                "level": "INFO",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "file",
                "level": "INFO",
                "filename": log_dir,
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 5,
                "encoding": "utf-8",

            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": "INFO",
            }
        }
    }
    logging.config.dictConfig(conf)