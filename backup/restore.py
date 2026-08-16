import sqlite3
import os
import shutil
import logging
import argparse
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_database(db_path: str) -> bool:
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            if result and result[0] == "ok":
                return True
            else:
                logger.error(f"Integrity check failed. Result: {result}")
                return False
    except Exception as e:
        logger.error(f"Error during integrity check: {e}")
        return False

def get_s3_client():
    try:
        return boto3.client(
            's3',
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {e}")
        return None

def download_from_s3(s3_key: str, download_path: str) -> bool:
    s3_client = get_s3_client()
    bucket = os.getenv("S3_BUCKET")
    if not s3_client or not bucket:
        logger.error("S3 client or bucket not configured.")
        return False

    logger.info(f"Downloading {s3_key} from bucket {bucket}...")
    try:
        s3_client.download_file(bucket, s3_key, download_path)
        logger.info("Download successful.")
        return True
    except ClientError as e:
        logger.error(f"Failed to download from S3: {e}")
        return False

def restore_backup(backup_file: str, target_db: str, from_s3: bool = False):
    temp_db_path = "/tmp/restore_temp.db"
    
    if from_s3:
        success = download_from_s3(backup_file, temp_db_path)
        if not success:
            return
    else:
        if not os.path.exists(backup_file):
            logger.error(f"Backup file not found: {backup_file}")
            return
        shutil.copy2(backup_file, temp_db_path)

    logger.info("Verifying backup integrity...")
    if verify_database(temp_db_path):
        logger.info("Integrity check passed. Restoring database...")
        # Create a backup of current just in case
        if os.path.exists(target_db):
            backup_of_current = f"{target_db}.pre-restore.bak"
            shutil.copy2(target_db, backup_of_current)
            logger.info(f"Created a backup of current database at {backup_of_current}")

        shutil.move(temp_db_path, target_db)
        logger.info(f"Database successfully restored to {target_db}!")
        logger.info("Please restart the main application container to load the new database.")
    else:
        logger.error("Integrity check failed. Aborting restore.")
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore ForgerBot database from a backup.")
    parser.add_argument("source", help="Path to the local backup file, or S3 key if --s3 is used.")
    parser.add_argument("--s3", action="store_true", help="Flag to indicate the source is an S3 key.")
    
    args = parser.parse_args()
    target_db_path = os.getenv("DATABASE_PATH", "/data/data.db")
    
    restore_backup(args.source, target_db_path, args.s3)
