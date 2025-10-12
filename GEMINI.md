# Project Overview

This project contains a Python script named `nyaa_comments.py` that scrapes the Nyaa.si website for new comments on torrents and sends notifications to a Discord webhook. It can monitor both listing pages and individual torrent pages. The script is designed to be run locally or as a scheduled GitHub Actions workflow.

## Key Technologies

*   **Python 3.10+**
*   **Libraries:**
    *   `typer`: For creating the command-line interface.
    *   `pydantic`: For data validation and settings management.
    *   `requests`: For making HTTP requests to Nyaa.si and Discord.
    *   `beautifulsoup4`: For parsing HTML and scraping data.
    *   `alive-progress`: For displaying progress bars in the terminal.

## Architecture

The script is a single-file application with the following components:

*   **`NyaaScraper`:** Handles all interactions with Nyaa.si, including fetching pages, parsing torrents, and scraping comments.
*   **`DatabaseManager`:** Manages a local JSON file (`database.json`) to store comments and track new ones.
*   **`DiscordWebhook`:** Sends formatted notifications to a Discord webhook.
*   **Pydantic Models:** `Comment`, `CommentUser`, and `Secrets` are used to define the data structure and handle settings.
*   **CLI:** The `typer` library is used to create a user-friendly command-line interface with arguments and options.

# Building and Running

## Local Execution

1.  **Install Dependencies:**
    ```bash
    pip install typer pydantic requests beautifulsoup4 alive-progress
    ```

2.  **Run the script:**

    *   To monitor a Nyaa.si listing page and send notifications:
        ```bash
        python nyaa_comments.py "https://nyaa.si/?f=0&c=0_0&q=some-query" --webhook "YOUR_DISCORD_WEBHOOK_URL"
        ```

    *   To monitor a single torrent page:
        ```bash
        python nyaa_comments.py "https://nyaa.si/view/1234567" --webhook "YOUR_DISCORD_WEBHOOK_URL"
        ```

    *   To initialize the database without sending notifications:
        ```bash
        python nyaa_comments.py "https://nyaa.si/?f=0&c=0_0&q=some-query" --dump-comments
        ```

## GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/scrape.yml`) that runs the scraper every 5 minutes.

*   **Configuration:** The workflow uses the following secrets, which need to be configured in the repository settings:
    *   `DISCORD_WEBHOOK_URL`: The Discord webhook URL for notifications.
    *   `NYAA_URL`: The Nyaa.si URL to monitor.

*   **Database Caching:** The `database.json` file is cached between workflow runs to maintain the history of scraped comments.

# Development Conventions

*   **Code Style:** The code follows standard Python conventions (PEP 8).
*   **Type Hinting:** The code uses type hints extensively for clarity and static analysis.
*   **Data Validation:** Pydantic models are used to ensure data integrity.
*   **Secrets Management:** Secrets are loaded from a `.secrets.json` file, environment variables, or command-line arguments. The `.secrets.json` file is included in the `.gitignore` file to prevent it from being committed.
*   **Database:** The `database.json` file is used to store the state of scraped comments and is also included in the `.gitignore` file.
