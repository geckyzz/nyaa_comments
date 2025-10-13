# Recent Changes

## New Features

### 1. Max Pages Parameter (`--max-pages`)

Limit the number of pages to scrape from Nyaa.si listing pages. Useful for testing or limiting the scope of scraping.

**Usage:**
```bash
python nyaa_comments.py "https://nyaa.si/?q=anime" --max-pages 5
```

This will scrape only the first 5 pages instead of all available pages.

### 2. Database Upload to Catbox Litterbox (`--upload-db`)

Upload an encrypted backup of your database to Catbox Litterbox and receive the download URL and decryption key via Discord webhook.

**Features:**
- Database is encrypted using Fernet (symmetric encryption)
- Encrypted file is compressed into a tar.gz archive
- Uploaded to Catbox Litterbox with configurable expiry time
- Download URL and decryption key sent to Discord webhook
- Sensitive information is NOT printed in GitHub Actions logs (only sent to Discord)

**Usage:**
```bash
# Upload with default 12h expiry
python nyaa_comments.py "https://nyaa.si/?q=anime" --upload-db

# Upload with custom expiry (1h, 12h, 24h, or 72h)
python nyaa_comments.py "https://nyaa.si/?q=anime" --upload-db --db-expiry 24h
```

**Security Note:** 
- When running in GitHub Actions, the decryption key and download URL are only sent to the Discord webhook and NOT printed in the workflow logs.
- When running locally, both are displayed in the terminal output.

### 3. GitHub Actions Workflow Enhancement

The workflow now supports manual triggers with database upload options:

**Manual Workflow Inputs:**
- `dump_comments`: Initialize database without sending notifications (boolean)
- `upload_db`: Upload encrypted database to Catbox Litterbox (boolean)
- `db_expiry`: Expiry time for database upload (choice: 1h, 12h, 24h, 72h)

**How to trigger manually:**
1. Go to your repository's Actions tab
2. Select "Nyaa Comments Scraper" workflow
3. Click "Run workflow"
4. Configure the options:
   - Check "Upload encrypted database" to enable upload
   - Select expiry time (default: 12h)
5. Click "Run workflow"

## Technical Details

### Dependencies Added
- `cryptography>=41.0.0` - For database encryption

### New Classes
- `DatabaseUploader`: Handles database encryption, compression, and upload to Catbox Litterbox

### Modified Classes
- `NyaaScraper`: Now accepts `max_pages` parameter to limit page scraping
- `DiscordWebhook`: Added `send_database_upload_notification()` method

## How to Decrypt and Extract the Database

If you receive an encrypted database backup:

1. Download the file from the Litterbox URL
2. Extract the tarball:
   ```bash
   tar -xzf database.json.encrypted.tar.gz
   ```
3. Decrypt using Python:
   ```python
   from cryptography.fernet import Fernet
   
   # Your decryption key from Discord
   key = b'YOUR_KEY_HERE'
   
   fernet = Fernet(key)
   
   with open('database.json.encrypted', 'rb') as f:
       encrypted_data = f.read()
   
   decrypted_data = fernet.decrypt(encrypted_data)
   
   with open('database.json', 'wb') as f:
       f.write(decrypted_data)
   ```

## Examples

### Example 1: Scrape with max pages and upload backup
```bash
python nyaa_comments.py "https://nyaa.si/?q=anime" \
  --max-pages 10 \
  --upload-db \
  --db-expiry 24h \
  --webhook "https://discord.com/api/webhooks/..."
```

### Example 2: GitHub Actions manual trigger
Navigate to Actions → Nyaa Comments Scraper → Run workflow
- Select branch
- Check "Upload encrypted database to Catbox Litterbox"
- Select "24h" for expiry
- Run workflow

The Discord webhook will receive:
- Regular comment notifications (if any)
- Database backup notification with download URL and decryption key
