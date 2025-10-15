# Recent Changes

## v4.0 - Unified Scraper

### Major Change: Script Unification

- Merged `nyaa_scraper.py` and `animetosho_scraper.py` into a single, unified
  script: `comment_scraper.py`.
- The new script can handle URLs from Nyaa.si, Sukebei, and AnimeTosho.
- The correct database (`database.json`, `database.sukebei.json`, or
  `database.at.json`) is now chosen automatically based on the input URL.
- The old `nyaa_scraper.py` and `animetosho_scraper.py` files have been removed.
- All documentation and workflows have been updated to use `comment_scraper.py`.

**Example:**

```bash
# Scrape Nyaa.si
python comment_scraper.py "https://nyaa.si/view/12345"

# Scrape AnimeTosho with a keyword
python comment_scraper.py "https://animetosho.org/comments" -k "[EMBER]"
```

---

## v3.0 - AnimeTosho Support

### New Feature: AnimeTosho Scraper

Added complete support for scraping AnimeTosho comments with keyword filtering
and HTML to Markdown conversion:

- **New Script**: `animetosho_scraper.py`
  - Separate scraper for AnimeTosho comments
  - Uses separate database file: `database.at.json`
  - Full Discord webhook integration

- **Keyword Filtering**: Filter comments by torrent titles
  - Support for multiple keywords via `-k` or `--keyword` flag
  - Example: `-k "[ToonsHub]" -k "[EMBER]"`
  - Case-insensitive matching

- **HTML to Markdown Conversion**: Comments are automatically converted from
  HTML to Markdown
  - Preserves formatting (links, line breaks, emphasis)
  - Uses `markdownify` library for clean conversion

- **Page Limit Options**:
  - Default: 5 pages
  - Set to 0 for unlimited pages (scrapes all available)
  - Controlled via `--max-pages` parameter

- **Pagination Detection**: Automatically detects maximum pages from
  AnimeTosho's pagination element

**Usage Examples:**

```bash
# Basic usage with keyword filtering
python animetosho_scraper.py --keyword "[ToonsHub]" --webhook "YOUR_WEBHOOK_URL"

# Initialize database with multiple keywords
python animetosho_scraper.py --dump-comments -k "[EMBER]" -k "[SubsPlease]"
--max-pages 10

# Unlimited scraping (all pages)
python animetosho_scraper.py --max-pages 0 --dump-comments
```

### Improvements

- **Database Manager**: Updated to handle both numeric IDs (Nyaa) and
  alphanumeric slugs (AnimeTosho)
- **Discord Webhook**: Added `is_animetosho` parameter to support different URL
  formats and colors
  - AnimeTosho uses orange color (#FF6B00)
  - Nyaa uses blue color (#0085FF)
- **Dependencies**: Added `markdownify>=0.11.0` to `pyproject.toml`

### Files Added

- `classes/animetosho_scraper.py` - AnimeTosho scraper class
- `animetosho_scraper.py` - Main AnimeTosho CLI script

### Files Modified

- `classes/discord_webhook.py` - Added AnimeTosho support
- `classes/database_manager.py` - Handle non-numeric IDs
- `pyproject.toml` - Added markdownify dependency
- `README.md` - Added AnimeTosho documentation
- `.gitignore` - Added `database.at.json`

---

## v2.1 - Security Improvement for Database Uploads

### Security Fix

#### **Separate Secret Webhook for Sensitive Data**

Added a new security feature to prevent exposing sensitive backup information in
GitHub Actions logs:

- **New Configuration Option**: `discord_secret_webhook_url` /
  `--secret-webhook`
- Can be provided via CLI argument, `.secrets.json`, or
`DISCORD_SECRET_WEBHOOK_URL` environment variable
- Used for sending database backup notifications containing download URLs and
decryption keys
- When running in GitHub Actions with `--upload-db`, this webhook is
**required** to prevent leaking sensitive data

- **Validation**: The script now validates that `DISCORD_SECRET_WEBHOOK_URL` is
  provided when:
  - Running in GitHub Actions (`GITHUB_ACTIONS=true`)
  - AND using the `--upload-db` flag
  
- **Fallback Behavior**: When not in GitHub Actions, the regular webhook can be
  used for database uploads

**Migration Guide:**
If you use the database upload feature in GitHub Actions, add a new secret:

1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Add `DISCORD_SECRET_WEBHOOK_URL` with a dedicated webhook URL
3. This webhook will receive sensitive backup notifications separately from
regular comment notifications

**Example `.secrets.json`:**

```json
{
  "discord_webhook_url": "https://discord.com/api/webhooks/regular...",
  "discord_secret_webhook_url": "https://discord.com/api/webhooks/sensitive..."
}
```

---

## v2.0 - Modular Refactor & New Features

### Major Changes

#### 1. **Modular Architecture**

The entire codebase has been refactored into a modular structure:

- **`classes/`** directory containing all class definitions
- **`modules/`** directory for shared utilities
- Main script renamed from `nyaa_comments.py` to **`nyaa_scraper.py`**
- Enhanced maintainability and testability

**Structure:**

```text
classes/
  ├── comment_models.py      - Comment and CommentUser models
  ├── database_manager.py    - JSON database management
  ├── database_uploader.py   - Catbox Litterbox uploader
  ├── discord_webhook.py     - Discord notifications
  ├── nyaa_scraper.py        - Web scraper for Nyaa.si
  ├── secrets.py             - Configuration management
  └── user_role.py           - User role enumeration

modules/
  └── crypto_utils.py        - Shared encryption/decryption utilities
```

#### 2. **Enhanced Cookies Support**

Cookies can now be loaded from multiple sources with encryption support:

**Sources (priority order):**

1. `--cookies` CLI parameter (local file)
2. `.secrets.json` file (local path or remote URL)
3. Environment variables (`COOKIES_PATH`, `COOKIES_URL`, `COOKIES_KEY`)

**Remote Cookies:**

```json
{
  "cookies_url": "https://example.com/cookies.tar.gz",
  "cookies_key": "encryption_key_here"
}
```

The scraper will automatically download, decrypt (if encrypted), and load the
cookies.

**Usage:**

```bash
# Local file
python nyaa_scraper.py "URL" --cookies /path/to/cookies.txt

# With decryption key for remote
python nyaa_scraper.py "URL" --cookies-key "DECRYPTION_KEY"
```

#### 3. **Encryption/Decryption Utility Enhancement**

`decrypt_database.py` now supports both encryption and decryption:

**Encrypt a file:**

```bash
python decrypt_database.py encrypt cookies.txt -o cookies_backup
# Outputs: cookies_backup.tar.gz and encryption key
```

**Decrypt a file:**

```bash
python decrypt_database.py decrypt backup.tar.gz "KEY" -o output.txt
```

### New Features

#### 1. Max Pages Parameter (`--max-pages`)

Limit the number of pages to scrape from Nyaa.si listing pages. Useful for
testing or limiting the scope of scraping.

**Usage:**

```bash
python nyaa_scraper.py "https://nyaa.si/?q=anime" --max-pages 5
```

This will scrape only the first 5 pages instead of all available pages.

#### 2. Database Upload to Catbox Litterbox (`--upload-db`)

Upload an encrypted backup of your database to Catbox Litterbox and receive the
download URL and decryption key via Discord webhook.

**Features:**

- Database is encrypted using Fernet (symmetric encryption)
- Encrypted file is compressed into a tar.gz archive
- Uploaded to Catbox Litterbox with configurable expiry time
- Download URL and decryption key sent to Discord webhook
- Sensitive information is NOT printed in GitHub Actions logs (only sent to
  Discord)

**Usage:**

```bash
# Upload with default 12h expiry
python nyaa_scraper.py "https://nyaa.si/?q=anime" --upload-db

# Upload with custom expiry (1h, 12h, 24h, or 72h)
python nyaa_scraper.py "https://nyaa.si/?q=anime" --upload-db --db-expiry 24h
```

**Security Note:**

- When running in GitHub Actions, the decryption key and download URL are only
  sent to the Discord webhook and NOT printed in the workflow logs.
- When running locally, both are displayed in the terminal output.

#### 3. GitHub Actions Workflow Enhancement

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

- `cryptography>=41.0.0` - For database encryption and file
  encryption/decryption

### New Modules

- `crypto_utils.py`: Shared utilities for encryption, decryption, tarball
  creation, and extraction

### Modified Classes

- `NyaaScraper`: Now accepts `Secrets` object for configuration, supports remote
  cookies with decryption
- `Secrets`: Extended to support cookies configuration from multiple sources
- `DiscordWebhook`: Added `send_database_upload_notification()` method
- `DatabaseUploader`: Refactored to use shared `CryptoUtils`

### Type Safety Improvements

- All path parameters now use `pathlib.Path` objects instead of strings
- Consistent type handling throughout the codebase

### Code Quality

- Formatted with `ruff`
- Import statements sorted alphabetically
- Reduced code duplication

## How to Use Encrypted Files

### Encrypt a File

```bash
python decrypt_database.py encrypt cookies.txt
# Output: cookies.txt.encrypted.tar.gz
# Key: (printed to terminal)
```

### Decrypt and Extract a File

```bash
python decrypt_database.py decrypt backup.tar.gz "DECRYPTION_KEY" -o output.json
```

## Migration Guide

If you're upgrading from v1.x:

1. **Update your commands:**

   ```bash
   # Old
   python nyaa_comments.py "URL"
   
   # New
   python nyaa_scraper.py "URL"
   ```

2. **No other changes needed** - all existing functionality is preserved and
backwards compatible.

3. **Optional: Use new features:**
   - Add `--max-pages` to limit scraping
   - Add `--upload-db` for automatic backups
   - Configure remote cookies in `.secrets.json`

## Examples

### Example 1: Full-featured scraping

```bash
python nyaa_scraper.py "https://nyaa.si/?q=anime" \
  --max-pages 10 \
  --upload-db \
  --db-expiry 24h \
  --webhook "https://discord.com/api/webhooks/..."
```

### Example 2: Using remote encrypted cookies

Create `.secrets.json`:

```json
{
  "discord_webhook_url": "https://discord.com/api/webhooks/...",
  "cookies_url": "https://example.com/cookies.tar.gz",
  "cookies_key": "your_encryption_key_here"
}
```

Then run:

```bash
python nyaa_scraper.py "https://nyaa.si/?q=anime"
```

### Example 3: GitHub Actions manual trigger

Navigate to Actions → Nyaa Comments Scraper → Run workflow

- Select branch
- Check "Upload encrypted database to Catbox Litterbox"
- Select "24h" for expiry
- Run workflow

The Discord webhook will receive:

- Regular comment notifications (if any)
- Database backup notification with download URL and decryption key
