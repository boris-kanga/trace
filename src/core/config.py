import os

import dotenv

from src.tools.local_path import LocalPath


WORK_DIR: LocalPath = LocalPath(__file__) - 3


dotenv.load_dotenv(
    WORK_DIR + "config" + '.env'
)


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", 5432)),

    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD",),
    "database_name": os.getenv("DB_NAME", "db")
}

CONFIG = os.environ.copy()

S3_CONFIG = {
    "endpoint": os.environ.get(f"S3_ENDPOINT", "http://s3:9000"),
    "access_key": os.getenv("MINIO_ROOT_USER"),
    "secret_key": os.getenv("MINIO_ROOT_PASSWORD"),
    "public_url": os.getenv(
        "S3_PUBLIC_URL", "http://localhost:9000"
    )
}