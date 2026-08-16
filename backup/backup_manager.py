import sqlite3
import os
import time
from datetime import datetime
import logging
import boto3
from botocore.exceptions import ClientError
import schedule
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/data.db")
    BACKUP_DIR = os.getenv("BACKUP_DIR", "/backup")
    S3_BUCKET = os.getenv("S3_BUCKET")
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL") # For R2/Minio
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    DAILY_RETENTION = int(os.getenv("DAILY_RETENTION", 7))
    WEEKLY_RETENTION = int(os.getenv("WEEKLY_RETENTION", 4))

class BackupManager:
    def __init__(self, config: Config):
        self.config = config
        self._init_directories()
        self.s3_client = self._init_s3_client()

    def _init_directories(self):
        os.makedirs(self.config.BACKUP_DIR, exist_ok=True)
        os.makedirs(os.path.join(self.config.BACKUP_DIR, "daily"), exist_ok=True)
        os.makedirs(os.path.join(self.config.BACKUP_DIR, "weekly"), exist_ok=True)

    def _init_s3_client(self):
        if not self.config.S3_BUCKET:
            logger.info("S3_BUCKET not configured. S3 upload will be disabled.")
            return None
        
        try:
            return boto3.client(
                's3',
                endpoint_url=self.config.S3_ENDPOINT_URL,
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            return None

    def create_backup(self, backup_type="daily"):
        if not os.path.exists(self.config.DATABASE_PATH):
            logger.error(f"Database not found at {self.config.DATABASE_PATH}")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{backup_type}_{timestamp}.db"
        backup_path = os.path.join(self.config.BACKUP_DIR, backup_type, backup_filename)

        logger.info(f"Starting {backup_type} backup: {backup_path}")
        
        try:
            # 0.1 Script de backup con VACUUM INTO
            with sqlite3.connect(self.config.DATABASE_PATH) as conn:
                conn.execute(f"VACUUM INTO '{backup_path}'")
            logger.info(f"Successfully created local backup at {backup_path}")
            
            # 0.6 Copia fuera del host (S3/R2/rsync)
            self._upload_to_s3(backup_path, f"{backup_type}/{backup_filename}")
            
            # 0.3 Retención automática
            self._enforce_retention(backup_type)

        except sqlite3.OperationalError as e:
            logger.error(f"Database lock or vacuum error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")

    def _upload_to_s3(self, local_file: str, s3_key: str):
        if not self.s3_client:
            return
            
        logger.info(f"Uploading {local_file} to S3 bucket {self.config.S3_BUCKET} as {s3_key}")
        try:
            self.s3_client.upload_file(local_file, self.config.S3_BUCKET, s3_key)
            logger.info("Upload successful.")
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")

    def _enforce_retention(self, backup_type: str):
        dir_path = os.path.join(self.config.BACKUP_DIR, backup_type)
        files = []
        for f in os.listdir(dir_path):
            full_path = os.path.join(dir_path, f)
            if os.path.isfile(full_path) and f.endswith(".db"):
                files.append(full_path)
        
        # Sort files by modification time (oldest first)
        files.sort(key=os.path.getmtime)
        
        max_files = self.config.DAILY_RETENTION if backup_type == "daily" else self.config.WEEKLY_RETENTION
        
        if len(files) > max_files:
            files_to_delete = files[:-max_files]
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted old backup to maintain retention: {file_path}")
                    # Also delete from S3 to match retention, optional but good
                    self._delete_from_s3(f"{backup_type}/{os.path.basename(file_path)}")
                except Exception as e:
                    logger.error(f"Failed to delete old backup {file_path}: {e}")
                    
    def _delete_from_s3(self, s3_key: str):
        if not self.s3_client:
            return
        try:
            self.s3_client.delete_object(Bucket=self.config.S3_BUCKET, Key=s3_key)
            logger.info(f"Deleted {s3_key} from S3.")
        except Exception as e:
            logger.error(f"Failed to delete {s3_key} from S3: {e}")

def run_daily_backup(manager):
    manager.create_backup("daily")

def run_weekly_backup(manager):
    manager.create_backup("weekly")

if __name__ == "__main__":
    config = Config()
    manager = BackupManager(config)
    
    logger.info("Backup service started.")
    
    # Run a backup immediately on startup
    manager.create_backup("daily")
    
    # Schedule backups
    schedule.every().day.at("03:00").do(run_daily_backup, manager)
    schedule.every().sunday.at("04:00").do(run_weekly_backup, manager)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
