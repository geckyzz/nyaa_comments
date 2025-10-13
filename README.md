# Nyaa Comments Scraper

A modular Python application that monitors Nyaa.si torrents for new comments and sends
real-time notifications to Discord. Supports both listing pages and individual
torrent monitoring with advanced features like encrypted backups and remote cookies support.

> [!NOTE]
>
> This project was developed with AI assistance. All code and functionality
> have been thoroughly tested and inspected to ensure reliability and correctness.

## Features

- **Dual Mode Support**: Monitor entire listing pages or specific torrent pages
- **Discord Notifications**: Rich embed notifications with user avatars and roles
  (Trusted/Uploader)
- **Smart Tracking**: Only notifies about new comments, stores history in local JSON database
- **Rate Limit Handling**: Automatic Discord API rate limit management
- **Advanced Cookie Support**: Local files, remote URLs, and encrypted remote cookies
- **Encrypted Backups**: Upload encrypted database backups to Catbox Litterbox
- **Max Pages Limit**: Control scraping scope with `--max-pages` parameter
- **GitHub Actions**: Automated monitoring with scheduled workflow (every 10 minutes)
- **Progress Bars**: Real-time progress indicators for scraping operations
- **Modular Architecture**: Clean separation of concerns for better maintainability

## Installation

### Requirements

- Python 3.10+
- Dependencies managed via `pip`

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nyaa_comments.git
   cd nyaa_comments
   ```

2. Install dependencies:
   ```bash
   pip install .
   # or
   pip install -r requirements.txt
   ```

## Usage

### Command Line

Basic usage with Discord webhook:

```bash
python nyaa_scraper.py "https://nyaa.si/?f=0&c=0_0&q=anime" --webhook "YOUR_DISCORD_WEBHOOK_URL"
```

Monitor a specific torrent:

```bash
python nyaa_scraper.py "https://nyaa.si/view/2008634"
```

Initialize database without notifications:

```bash
python nyaa_scraper.py "https://nyaa.si/?f=0&c=0_0&q=anime" --dump-comments
```

Limit scraping to first 5 pages:

```bash
python nyaa_scraper.py "https://nyaa.si/?q=anime" --max-pages 5
```

Upload encrypted database backup:

```bash
python nyaa_scraper.py "https://nyaa.si/?q=anime" --upload-db --db-expiry 24h
```

With local cookies file:

```bash
python nyaa_scraper.py "https://nyaa.si/?q=anime" --cookies "/path/to/cookies.txt"
```

### Configuration Options

#### **Discord Webhook** (priority order)

1. `--webhook` CLI argument
2. `.secrets.json` file: `{"discord_webhook_url": "..."}`
3. `DISCORD_WEBHOOK_URL` environment variable

#### **Secret Discord Webhook for Sensitive Data** (priority order)

For database uploads with sensitive encryption keys, use a separate webhook:

1. `--secret-webhook` CLI argument
2. `.secrets.json` file: `{"discord_secret_webhook_url": "..."}`
3. `DISCORD_SECRET_WEBHOOK_URL` environment variable

> [!IMPORTANT]
> When running in GitHub Actions with `--upload-db`, you **must** provide
> `DISCORD_SECRET_WEBHOOK_URL` to prevent exposing sensitive backup information
> (download URLs and decryption keys) to public logs.

#### **Cookies** (priority order)

1. `--cookies` CLI argument (local file path)
2. `.secrets.json` file with `cookies_path` (local) or `cookies_url` (remote)
3. Environment variables: `COOKIES_PATH`, `COOKIES_URL`, `COOKIES_KEY`

**Example `.secrets.json` with remote encrypted cookies:**
```json
{
  "discord_webhook_url": "https://discord.com/api/webhooks/...",
  "cookies_url": "https://example.com/cookies.tar.gz",
  "cookies_key": "your_encryption_key_here"
}
```

#### **Arguments**

- `base_url` (required): Nyaa.si URL to scrape (listing or torrent page)

#### **Options**

- `--webhook TEXT`: Discord webhook URL
- `--secret-webhook TEXT`: Discord webhook URL for sensitive data (database backups)
- `--dump-comments`: Initialize database without sending notifications
- `--cookies PATH`: Path to local Netscape-format cookies file
- `--cookies-key TEXT`: Decryption key for encrypted remote cookies
- `--max-pages INTEGER`: Maximum number of pages to scrape
- `--upload-db`: Upload encrypted database to Catbox Litterbox
- `--db-expiry TEXT`: Expiry time for database upload (1h, 12h, 24h, 72h)
- `--help`: Show help message

## Encryption/Decryption Utility

The included `decrypt_database.py` utility supports both encryption and decryption:

### Encrypt a file

```bash
python decrypt_database.py encrypt cookies.txt -o backup
# Creates: backup.tar.gz and outputs encryption key
```

### Decrypt a file

```bash
python decrypt_database.py decrypt backup.tar.gz "ENCRYPTION_KEY" -o cookies.txt
```

## GitHub Actions Setup

This repository includes a workflow that automatically monitors Nyaa.si every 10 minutes.

### Setup Instructions

1. Go to your repository **Settings** → **Secrets and variables** → **Actions**

2. Add the following **secrets**:
   - `DISCORD_WEBHOOK_URL`: Your Discord webhook URL for comment notifications
   - `DISCORD_SECRET_WEBHOOK_URL`: Your Discord webhook URL for sensitive data (required for database uploads)
   - `NYAA_URL`: The Nyaa.si URL to monitor

3. The workflow will:
   - Run automatically every 10 minutes
   - Can be triggered manually from Actions tab with options
   - Caches database privately (not committed to repo)
   - Prevents concurrent runs

> [!WARNING]
> If you plan to use the database upload feature (`upload_db`), you **must** configure
> `DISCORD_SECRET_WEBHOOK_URL` to avoid exposing sensitive backup information in workflow logs.

### Manual Workflow Trigger

You can manually trigger the workflow with options:
- **dump_comments**: Initialize database without sending notifications
- **upload_db**: Upload encrypted database backup to Catbox Litterbox
- **db_expiry**: Choose expiry time (1h, 12h, 24h, 72h)

## How It Works

1. **Scraping**: Fetches torrent listings or individual torrent pages from Nyaa.si
2. **Comment Detection**: Identifies torrents with comments and their counts
3. **Comparison**: Compares current comments with stored database
4. **Notification**: Sends Discord embeds for new comments only
5. **Storage**: Updates local `database.json` with all comments
6. **Backup** (optional): Encrypts and uploads database to Catbox Litterbox

## Project Structure

```
nyaa_comments/
├── classes/                    # Class definitions
│   ├── comment_models.py       # Comment and user models
│   ├── database_manager.py     # Database operations
│   ├── database_uploader.py    # Catbox Litterbox uploader
│   ├── discord_webhook.py      # Discord notifications
│   ├── nyaa_scraper.py         # Web scraping logic
│   ├── secrets.py              # Configuration management
│   └── user_role.py            # User role enumeration
├── modules/                    # Utility modules
│   └── crypto_utils.py         # Encryption/decryption utilities
├── nyaa_scraper.py             # Main application entry point
├── decrypt_database.py         # Encryption/decryption utility
└── .github/workflows/          # CI/CD workflows
    └── scrape.yml              # Automated scraping workflow
```

## Database Structure

The script maintains a `database.json` file:

```json
{
  "1234567": [
    {
      "id": 123,
      "pos": 1,
      "timestamp": 1697123456,
      "user": {
        "username": "user123",
        "image": "https://example.com/avatar.jpg"
      },
      "message": "Thanks for the upload!"
    }
  ]
}
```

Where `1234567` is the Nyaa torrent ID.

## Discord Embed Features

Each notification includes:
- Torrent title with link
- Comment text
- Username with avatar
- User role badge (Trusted/Uploader)
- Timestamp
- Direct link to comment

## Security Notes

- The `database.json` is excluded from git via `.gitignore`
- In GitHub Actions, database is cached privately
- Secrets are stored in GitHub Secrets, not in code
- Cookie files are never committed to repository
- Encrypted backups use Fernet symmetric encryption
- Sensitive information is hidden from GitHub Actions logs

## Advanced Examples

### Full-featured scraping with all options

```bash
python nyaa_scraper.py "https://nyaa.si/?q=anime" \
  --max-pages 10 \
  --upload-db \
  --db-expiry 24h \
  --cookies "/path/to/cookies.txt" \
  --webhook "https://discord.com/api/webhooks/..."
```

### Using environment variables

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export COOKIES_PATH="/path/to/cookies.txt"
python nyaa_scraper.py "https://nyaa.si/?q=anime" --max-pages 5
```

### Remote encrypted cookies

Create `.secrets.json`:
```json
{
  "discord_webhook_url": "https://discord.com/api/webhooks/...",
  "cookies_url": "https://example.com/cookies.tar.gz",
  "cookies_key": "encryption_key_from_encrypt_command"
}
```

Run normally:
```bash
python nyaa_scraper.py "https://nyaa.si/?q=anime"
```

## License

See [LICENSE](LICENSE) file for details.
