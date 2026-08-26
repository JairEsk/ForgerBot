# ForgerBot
Bot 4 discord

## Leveling model

ForgerBot has exactly one level per member and server:

- Eligible text messages award 15-25 cumulative XP, subject to the configured cooldown.
- The level is always derived from total text XP with `100 * level^2` as the cumulative threshold.
- Voice activity stores elapsed minutes only. It has no separate XP, level, or level-up announcement.
- A level-up is announced only when a text XP grant crosses from a lower derived level to a higher one.

At startup, the database migration recovers the original `users` and `voice_sessions`
tables when present and repairs any cached text level that does not match its XP.

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

The startup log prints the resolved SQLite path and number of text XP records; on
Dokploy it must report `/data/data.db`. Keep the same Dokploy Compose application
and named volume across deployments: recreating the application under another name
can attach a different empty volume.

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
