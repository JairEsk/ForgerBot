# ForgerBot
Bot 4 discord

## Database Backups

The project includes an automated backup service designed to prevent data loss.

### Features
- **Zero Downtime Backups:** Uses SQLite `VACUUM INTO` to create perfectly consistent backups without locking the database or losing `-wal`/`-shm` data.
- **Separate Volume:** Backups are stored in a dedicated Docker volume (`forgerbot_backups`).
- **Retention Policy:** Automatically keeps the last 7 daily and 4 weekly backups.
- **Off-site Storage:** Uploads backups to an S3-compatible storage provider (AWS S3, Cloudflare R2, Minio, etc.).

### Configuration

You can configure the backup service using the following environment variables (pass them to the Dokploy environment or your `.env` file):

- `S3_BUCKET`: The name of your S3 bucket.
- `S3_ENDPOINT_URL`: Endpoint URL for S3/R2 (e.g., `https://<account_id>.r2.cloudflarestorage.com`).
- `AWS_ACCESS_KEY_ID`: Your S3/R2 Access Key.
- `AWS_SECRET_ACCESS_KEY`: Your S3/R2 Secret Key.
- `AWS_REGION`: S3 Region (default: `us-east-1`).
- `DAILY_RETENTION`: Number of daily backups to keep (default: 7).
- `WEEKLY_RETENTION`: Number of weekly backups to keep (default: 4).

### Restoring a Backup

Before restoring, **make sure to stop the main bot container** to prevent data corruption.

1. **Access the Backup Container:**
   ```bash
   docker compose exec backup_service bash
   ```
2. **Run the Restore Script:**
   - From a local file (in the `/backup` volume):
     ```bash
     python restore.py /backup/daily/backup_daily_20260816_120000.db
     ```
   - From S3:
     ```bash
     python restore.py daily/backup_daily_20260816_120000.db --s3
     ```
3. **Restart the Bot:**
   ```bash
   docker compose restart forgerbot
   ```

The `restore.py` script automatically verifies the integrity (`PRAGMA integrity_check;`) of the backup before applying it, ensuring you don't replace your DB with a corrupted file.