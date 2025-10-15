# Project Overview

This project contains a modular Python application that scrapes the Nyaa.si
website for new comments on torrents and sends notifications to a Discord
webhook. It can monitor both listing pages and individual torrent pages. The
script is designed to be run locally or as a scheduled GitHub Actions workflow.

## Key Technologies

* **Python 3.10+**
* **Libraries:**
  * `typer`: For creating the command-line interface.
  * `pydantic`: For data validation and settings management.
  * `requests`: For making HTTP requests to Nyaa.si and Discord.
  * `beautifulsoup4`: For parsing HTML and scraping data.
  * `alive-progress`: For displaying progress bars in the terminal.
  * `cryptography`: For encryption/decryption of sensitive files.

## Architecture

The application follows a modular architecture with separate directories for
classes and utilities:

### Main Scripts

* **`comment_scraper.py`:** Main entry point for the scraper application.
* **`decrypt_database.py`:** Utility for encrypting/decrypting files
  (database backups, cookies).

### Classes (`classes/`)

* **`NyaaScraper`:** Handles all interactions with Nyaa.si, including
  fetching pages, parsing torrents, and scraping comments. Supports local
  and remote cookies with optional encryption.
* **`DatabaseManager`:** Manages a local JSON file (`database.json`) to
  store comments and track new ones.
* **`DatabaseUploader`:** Encrypts and uploads database backups to Catbox
  Litterbox.
* **`DiscordWebhook`:** Sends formatted notifications to a Discord webhook.
* **`Secrets`:** Manages configuration from CLI arguments, `.secrets.json`,
  or environment variables.
* **Pydantic Models:** `Comment`, `CommentUser`, and `UserRole` define data
  structures.

### Modules (`modules/`)

* **`CryptoUtils`:** Shared utilities for encryption, decryption, and file
  packaging using Fernet symmetric encryption.

### CLI

The `typer` library is used to create a user-friendly command-line interface
with arguments and options.

## Building and Running

### Local Execution

1. **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    # or
    pip install .
    ```

2. **Run the script:**

    * To monitor a Nyaa.si listing page and send notifications:

        ```bash
        python comment_scraper.py \
          "https://nyaa.si/?f=0&c=0_0&q=some-query" \
          --webhook "YOUR_DISCORD_WEBHOOK_URL"
        ```

    * To monitor a single torrent page:

        ```bash
        python comment_scraper.py "https://nyaa.si/view/1234567" \
          --webhook "YOUR_DISCORD_WEBHOOK_URL"
        ```

    * To initialize the database without sending notifications:

        ```bash
        python comment_scraper.py \
          "https://nyaa.si/?f=0&c=0_0&q=some-query" --dump-comments
        ```

    * With max pages limit:

        ```bash
        python comment_scraper.py "https://nyaa.si/?q=anime" --max-pages 5
        ```

    * With database upload:

        ```bash
        python comment_scraper.py "https://nyaa.si/?q=anime" \
          --upload-db --db-expiry 24h
        ```

3. **Using cookies:**

    * Local file:

        ```bash
        python comment_scraper.py "URL" --cookies /path/to/cookies.txt
        ```

    * Remote encrypted cookies (in `.secrets.json`):

        ```json
        {
          "cookies_url": "https://example.com/cookies.tar.gz",
          "cookies_key": "encryption_key_here"
        }
        ```

4. **Encrypt/Decrypt files:**

    * Encrypt a file:

        ```bash
        python decrypt_database.py encrypt cookies.txt \
          -o cookies_backup
        ```

    * Decrypt a file:

        ```bash
        python decrypt_database.py decrypt cookies.tar.gz \
          "DECRYPTION_KEY" -o cookies.txt
        ```

### GitHub Actions

The project includes a GitHub Actions workflow
(`.github/workflows/scrape.yml`) that runs the scraper every 10 minutes.

* **Configuration:** The workflow uses the following secrets, which need to
  be configured in the repository settings:
  * `DISCORD_WEBHOOK_URL`: The Discord webhook URL for notifications.
  * `DISCORD_SECRET_WEBHOOK_URL`: A separate Discord webhook URL for
    sensitive data like database backups (required when using `upload_db`).
  * `NYAA_URL`: The Nyaa.si URL to monitor.

* **Database Caching:** The `database.json` file is cached between workflow
  runs to maintain the history of scraped comments.

* **Manual Trigger Options:**
  * `dump_comments`: Initialize database without sending notifications
  * `upload_db`: Upload encrypted database backup to Catbox Litterbox
    (requires `DISCORD_SECRET_WEBHOOK_URL`)
  * `db_expiry`: Expiry time for uploads (1h, 12h, 24h, 72h)

* **Security:** When running in GitHub Actions with database upload enabled,
  the application requires `DISCORD_SECRET_WEBHOOK_URL` to prevent exposing
  sensitive backup information (download URLs and decryption keys) in public
  workflow logs.

## Development Conventions

* **Code Style:** The code follows standard Python conventions (PEP 8) and
  is formatted with `ruff`.
* **Type Hinting:** The code uses type hints extensively for clarity and
  static analysis.
* **Data Validation:** Pydantic models are used to ensure data integrity.
* **Modular Design:** Classes and utilities are separated into dedicated
  directories for better maintainability.
* **Secrets Management:** Secrets are loaded from CLI arguments,
  `.secrets.json` file, or environment variables (in priority order). The
  `.secrets.json` file is included in the `.gitignore` file to prevent it
  from being committed.
* **Database:** The `database.json` file is used to store the state of
  scraped comments and is also included in the `.gitignore` file.
* **Path Objects:** All file paths use `pathlib.Path` objects for type
  safety and cross-platform compatibility.

## Git Commit Guidelines

* **No Conventional Commits:** Do NOT use conventional commits format
  (e.g., `feat:`, `fix:`, `chore:`).
* **Granular Commits:** Always make separate commits for each logical change
  rather than bundling multiple changes together.
* **Commit Early and Often:** Create commits for every meaningful change to
  maintain a clear history.

## Project Structure

```text
nyaa_comments/
├── classes/               # Class definitions
│   ├── animetosho_scraper.py
│   ├── comment_models.py  # Comment and user models
│   ├── database_manager.py
│   ├── database_uploader.py
│   ├── discord_webhook.py
│   ├── nyaa_scraper.py
│   ├── secrets.py
│   └── user_role.py
├── modules/               # Utility modules
│   └── crypto_utils.py    # Encryption/decryption utilities
├── comment_scraper.py        # Main application
├── decrypt_database.py    # Encryption/decryption tool
└── .github/workflows/     # CI/CD workflows
    └── scrape.yml
```
