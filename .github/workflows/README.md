# GitHub Actions Workflows

## Workflows

### 1. `scrape.yml` - Nyaa.si Comments Scraper
Monitors Nyaa.si for new comments.

**Schedule**: Every 10 minutes  
**Database**: `database.json`

**Secrets Required**:
- `DISCORD_WEBHOOK_URL` - Discord webhook for notifications
- `DISCORD_SECRET_WEBHOOK_URL` - Separate webhook for sensitive data (optional, required for `upload_db` in Actions)
- `NYAA_URL` - Nyaa.si URL to monitor

**Manual Trigger Inputs**:
- `dump_comments` (boolean) - Initialize database without notifications
- `upload_db` (boolean) - Upload encrypted database backup
- `db_expiry` (choice) - Backup expiry: 1h, 12h, 24h, 72h

### 2. `scrape_animetosho.yml` - AnimeTosho Comments Scraper
Monitors AnimeTosho for new comments with keyword filtering.

**Schedule**: Every 10 minutes  
**Database**: `database.at.json`

**Secrets Required**:
- `DISCORD_WEBHOOK_URL` - Discord webhook for notifications
- `DISCORD_SECRET_WEBHOOK_URL` - Separate webhook for sensitive data (optional)
- `AT_KEYWORDS` - Comma-separated keywords to filter (e.g., `[ToonsHub],[EMBER]`)
- `AT_MAX_PAGES` - Maximum pages to scrape (default: 5, 0 = unlimited)

**Manual Trigger Inputs**:
- `keywords` (string) - Keywords to filter (comma-separated, overrides secret)
- `max_pages` (number) - Maximum pages to scrape (overrides secret)
- `dump_comments` (boolean) - Initialize database without notifications
- `upload_db` (boolean) - Upload encrypted database backup
- `db_expiry` (choice) - Backup expiry: 1h, 12h, 24h, 72h

## Setup Instructions

### For Nyaa.si Scraper

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add the following secrets:
   ```
   DISCORD_WEBHOOK_URL: https://discord.com/api/webhooks/...
   DISCORD_SECRET_WEBHOOK_URL: https://discord.com/api/webhooks/... (optional)
   NYAA_URL: https://nyaa.si/?q=your-search
   ```

### For AnimeTosho Scraper

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add the following secrets:
   ```
   DISCORD_WEBHOOK_URL: https://discord.com/api/webhooks/...
   DISCORD_SECRET_WEBHOOK_URL: https://discord.com/api/webhooks/... (optional)
   AT_KEYWORDS: [ToonsHub],[EMBER],[SubsPlease]
   AT_MAX_PAGES: 5
   ```

## Keywords Format

Keywords should be comma-separated without spaces (spaces within keywords are preserved):

**Correct**:
```
[ToonsHub],[EMBER],[SubsPlease]
Blue Orchestra,Witch Watch
```

**Incorrect**:
```
[ToonsHub], [EMBER], [SubsPlease]  ❌ (spaces after commas)
```

## Manual Trigger Examples

### AnimeTosho - Monitor Specific Release Groups
1. Go to **Actions** tab
2. Select **AnimeTosho Comments Scraper**
3. Click **Run workflow**
4. Fill in inputs:
   - Keywords: `[ToonsHub],[EMBER]`
   - Max pages: `10`
5. Click **Run workflow**

### AnimeTosho - Initialize Database
1. Go to **Actions** tab
2. Select **AnimeTosho Comments Scraper**
3. Click **Run workflow**
4. Fill in inputs:
   - Dump comments: `☑ true`
   - Max pages: `20`
5. Click **Run workflow**

### Upload Database Backup
1. Go to **Actions** tab
2. Select either workflow
3. Click **Run workflow**
4. Fill in inputs:
   - Upload db: `☑ true`
   - DB expiry: `24h`
5. Click **Run workflow**

## Workflow Behavior

### Scheduled Runs
Both workflows run automatically every 10 minutes:
- Use secrets for configuration
- Cache database between runs
- Send Discord notifications for new comments

### Manual Runs
- Inputs override secrets
- Useful for testing or one-time operations
- Can initialize database or upload backups

### Concurrency
Each workflow has its own concurrency group to prevent multiple runs:
- `nyaa-scraper` - Only one Nyaa scraper runs at a time
- `animetosho-scraper` - Only one AnimeTosho scraper runs at a time
- Both can run simultaneously (different groups)

## Database Caching

Both workflows use GitHub Actions cache to persist databases:
- **Nyaa**: `database.json`
- **AnimeTosho**: `database.at.json`

Cache keys include `${{ github.run_id }}` to ensure each run has a unique key while maintaining restore capability through `restore-keys`.

## Troubleshooting

### No Notifications Sent
- Check if `DISCORD_WEBHOOK_URL` secret is set correctly
- Verify the webhook URL is valid and not expired
- Check workflow logs for errors

### Keywords Not Filtering
- Ensure keywords are comma-separated without extra spaces
- Keywords are case-insensitive
- Check if keywords match torrent titles (not comment content)

### Database Not Persisting
- Cache may have been evicted (GitHub keeps caches for 7 days)
- Run with `dump_comments: true` to reinitialize
- Check workflow logs for cache restoration messages

### Workflow Not Running
- Check if workflow file has correct YAML syntax
- Verify cron schedule is correct
- Check repository settings to ensure Actions are enabled
