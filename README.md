# Nyaa & AnimeTosho Comment Scraper

A Python script that scrapes Nyaa.si, Sukebei, and AnimeTosho for new comments and sends notifications to a Discord webhook.

## Features

- **Multi-Site Support**: Scrape comments from Nyaa.si, Sukebei.nyaa.si, and AnimeTosho.
- **Flexible Monitoring**: Monitor specific torrent pages or general listing pages.
- **Discord Notifications**: Send rich Discord webhook notifications for new comments.
- **Persistent Database**: Uses a local JSON database to keep track of posted comments and prevent duplicates.
- **Database Backups**: Automatically encrypt and upload database backups to Catbox Litterbox with a configurable expiry.
- **Cookies Support**: Use cookies to access comments on restricted or login-required torrents on Nyaa/Sukebei.
- **Keyword Filtering**: Filter AnimeTosho torrents by keywords in the title.
- **Robust Configuration**: Configure via CLI arguments, environment variables, or a `.secrets.json` file.

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/nyaa-comments-py.git
cd nyaa-comments-py

# Install dependencies
pip install -r requirements.txt
```

## Usage

The script is run from the command line using the unified `comment_scraper.py` entry point.

### Basic Commands

**Scrape a Nyaa.si or Sukebei URL:**
```bash
python comment_scraper.py "https://nyaa.si/?f=0&c=0_0&q=anime" --webhook "YOUR_WEBHOOK_URL"
```

**Scrape a single torrent page:**
```bash
python comment_scraper.py "https://sukebei.nyaa.si/view/1234567"
```

**Scrape AnimeTosho:**
```bash
python comment_scraper.py https://animetosho.org/comments --webhook "YOUR_WEBHOOK_URL"
```

### Advanced Commands

**Initialize the database without sending notifications:**
```bash
# Scrape the first 10 pages and save all comments to the database
python comment_scraper.py "https://nyaa.si/?q=anime" --dump-comments --max-pages 10
```

**Filter AnimeTosho by keyword:**
```bash
python comment_scraper.py https://animetosho.org/comments -k "[ToonsHub]" -k "[EMBER]" --webhook "URL"
```

**Upload an encrypted database backup:**
```bash
python comment_scraper.py "https://nyaa.si/?q=anime" --upload-db --db-expiry 24h
```

**Using local cookies (for Nyaa/Sukebei):**
```bash
python comment_scraper.py "https://nyaa.si/?q=anime" --cookies "/path/to/cookies.txt"
```

### Get Help

For a full list of all commands and options, run:
```bash
python comment_scraper.py --help
```

## Configuration

Secrets and configuration can be provided in the following priority order:
1.  **CLI arguments** (e.g., `--webhook`, `--cookies`)
2.  **`.secrets.json` file** in the root directory
3.  **Environment variables**

**Example `.secrets.json`:**
```json
{
  "discord_webhook_url": "https://discord.com/api/webhooks/regular...",
  "discord_secret_webhook_url": "https://discord.com/api/webhooks/sensitive...",
  "cookies_url": "https://example.com/cookies.tar.gz",
  "cookies_key": "your_encryption_key_here"
}
```

**Environment Variables:**
- `DISCORD_WEBHOOK_URL`
- `DISCORD_SECRET_WEBHOOK_URL`
- `COOKIES_PATH` (local file)
- `COOKIES_URL` (remote file)
- `COOKIES_KEY` (decryption key for remote file)

## GitHub Actions Workflows

The project includes three pre-configured GitHub Actions workflows to automate scraping.

| Workflow File                | Schedule          | Target Site | Database File             |
| ---------------------------- | ----------------- | ----------- | ------------------------- |
| `scrape.yml`                 | Every 10 minutes  | Nyaa.si     | `database.json`           |
| `scrape_sukebei.yml`         | Every 15 minutes  | Sukebei     | `database.sukebei.json`   |
| `scrape_animetosho.yml`      | Every 30 minutes  | AnimeTosho  | `database.at.json`        |

### Setup

To use the workflows, you must add secrets to your GitHub repository:
1.  Go to your repository **Settings** → **Secrets and variables** → **Actions**.
2.  Add the required secrets for the workflow you want to use.

**Nyaa.si (`scrape.yml`) Secrets:**
- `NYAA_URL`: The Nyaa.si URL to monitor (e.g., `https://nyaa.si/?q=your-query`).
- `DISCORD_WEBHOOK_URL`: Your main Discord webhook URL.
- `DISCORD_SECRET_WEBHOOK_URL`: (Optional) A separate webhook for receiving sensitive database backup links.

**Sukebei (`scrape_sukebei.yml`) Secrets:**
- `SUKEBEI_URL`: The Sukebei URL to monitor.
- `DISCORD_WEBHOOK_URL`
- `DISCORD_SECRET_WEBHOOK_URL`

**AnimeTosho (`scrape_animetosho.yml`) Secrets:**
- `DISCORD_WEBHOOK_URL`
- `DISCORD_SECRET_WEBHOOK_URL`

### Manual Triggers

All workflows can be triggered manually from the **Actions** tab in your repository. This allows you to override default settings for one-time runs.

**Common Manual Inputs:**
- `dump_comments` (boolean): Check to initialize the database without sending notifications.
- `upload_db` (boolean): Check to create and upload an encrypted database backup.
- `db_expiry` (choice): Set the expiry time for the backup (1h, 12h, 24h, 72h).

**AnimeTosho-Specific Input:**
- `keywords` (string): A comma-separated list of keywords to filter by (e.g., `[EMBER],[SubsPlease]`).

## Project Structure

```
nyaa-comments-py/
├── classes/                  # Class definitions
│   ├── animetosho_scraper.py # Logic for scraping AnimeTosho
│   ├── comment_models.py     # Pydantic models for comments
│   ├── database_manager.py   # Manages the JSON database
│   ├── database_uploader.py  # Handles database backups
│   ├── discord_webhook.py    # Sends Discord notifications
│   ├── nyaa_scraper.py       # Logic for scraping Nyaa/Sukebei
│   └── secrets.py            # Manages secrets and configuration
├── modules/
│   └── crypto_utils.py       # Encryption/decryption utilities
├── .github/workflows/        # GitHub Actions workflows
│   ├── scrape.yml
│   ├── scrape_sukebei.yml
│   └── scrape_animetosho.yml
├── comment_scraper.py        # Main application entry point
├── decrypt_database.py       # Tool for manual file encryption/decryption
└── pyproject.toml            # Project metadata and dependencies
```

## Troubleshooting

- **No Notifications Sent**: Check that your `DISCORD_WEBHOOK_URL` secret is correct and the webhook is valid. Check the workflow logs for any errors.
- **Database Not Persisting**: The GitHub Actions cache expires after 7 days. If the cache is evicted, you may need to re-initialize the database by running the workflow manually with `dump_comments` checked.
- **Keywords Not Filtering (AnimeTosho)**: Ensure keywords are comma-separated without extra spaces between them (e.g., `[Ember],[SubsPlease]`). Keywords are case-insensitive and match against torrent titles.

## License

See [LICENSE](LICENSE) file for details.