#!/usr/bin/env python3
"""AnimeTosho comment scraper with Discord notifications."""

import os
from pathlib import Path
from typing import Optional

import typer
from alive_progress import alive_bar

from classes.animetosho_scraper import AnimeToshoScraper
from classes.comment_models import Comment
from classes.database_manager import DatabaseManager
from classes.database_uploader import DatabaseUploader
from classes.discord_webhook import DiscordWebhook
from classes.secrets import Secrets


def main(
    base_url: str = typer.Argument(
        "https://animetosho.org/comments",
        help="The AnimeTosho URL to start scraping from (default: comments page).",
    ),
    dump_comments: bool = typer.Option(
        False,
        "--dump-comments",
        help="Initialize the database without sending Discord notifications.",
    ),
    discord_webhook_url: Optional[str] = typer.Option(
        None,
        "--webhook",
        help="Discord webhook URL (overrides .secrets.json and env vars).",
    ),
    discord_secret_webhook_url: Optional[str] = typer.Option(
        None,
        "--secret-webhook",
        help="Discord webhook URL for sensitive data like database backups (overrides .secrets.json and env vars).",
    ),
    keywords: Optional[list[str]] = typer.Option(
        None,
        "--keyword",
        "-k",
        help="Filter torrents by keyword (can be specified multiple times). Example: -k '[ToonsHub]' -k '[EMBER]'",
    ),
    max_pages: int = typer.Option(
        5,
        "--max-pages",
        help="Maximum number of pages to scrape (0 = unlimited, default = 5).",
    ),
    upload_db: bool = typer.Option(
        False,
        "--upload-db",
        help="Upload encrypted database to Catbox Litterbox and send webhook with download URL and decryption key.",
    ),
    db_expiry: str = typer.Option(
        "12h",
        "--db-expiry",
        help="Expiry time for database upload (1h, 12h, 24h, 72h).",
    ),
):
    """
    A Python script to scrape comments from AnimeTosho and send notifications to Discord.
    Supports keyword filtering and HTML to Markdown conversion.
    """
    # Check if running in GitHub Actions
    is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

    secrets = Secrets.load(
        discord_webhook_url, None, None, discord_secret_webhook_url
    )
    if not dump_comments and not secrets.discord_webhook_url:
        print(
            "Error: Discord webhook URL is not set. Provide it via --webhook, .secrets.json, or DISCORD_WEBHOOK_URL environment variable."
        )
        raise typer.Exit(code=1)

    # Validate secret webhook URL for database uploads in GitHub Actions
    if upload_db and is_github_actions and not secrets.discord_secret_webhook_url:
        print(
            "Error: Database upload in GitHub Actions requires a separate secret webhook URL.\n"
            "Provide it via DISCORD_SECRET_WEBHOOK_URL environment variable or .secrets.json to prevent exposing sensitive data."
        )
        raise typer.Exit(code=1)

    # Use separate database for AnimeTosho
    db_manager = DatabaseManager(db_path=Path("database.at.json"))
    scraper = AnimeToshoScraper(base_url, secrets, keywords, max_pages)
    discord = (
        DiscordWebhook(secrets.discord_webhook_url)
        if secrets.discord_webhook_url
        else None
    )

    if keywords:
        print(f"Filtering by keywords: {', '.join(keywords)}")

    print("Scraping AnimeTosho for comments...")
    all_comments = scraper.scrape_all_comments()

    if not all_comments:
        print("No comments found or failed to scrape.")
        raise typer.Exit()

    print(
        f"Found {len(all_comments)} torrent(s) with comments. Checking for updates..."
    )

    new_comment_queue = []

    with alive_bar(len(all_comments), title="Checking torrents") as bar:
        for torrent_id, (title, comments) in all_comments.items():
            bar.text(f"-> Checking: {torrent_id}")

            stored_comments = db_manager.get_comments(torrent_id)
            stored_comment_count = len(stored_comments)
            current_comment_count = len(comments)

            if dump_comments and not stored_comments:
                db_manager.update_comments(torrent_id, comments)
            elif current_comment_count > stored_comment_count:
                new_comments = comments[stored_comment_count:]
                new_comment_queue.extend(
                    (torrent_id, title, comment) for comment in new_comments
                )
                db_manager.update_comments(torrent_id, comments)

            bar()

    print("Saving database...")
    db_manager.save()

    if not dump_comments and discord:
        if new_comment_queue:
            new_comment_queue.sort(key=lambda item: item[2].timestamp)

            print(
                f"\nSending {len(new_comment_queue)} new comment notifications to Discord..."
            )
            with alive_bar(len(new_comment_queue), title="Sending notifications") as bar:
                for torrent_id, title, comment in new_comment_queue:
                    # For AnimeTosho, we use the torrent_id directly
                    # We don't have user roles, so pass None
                    discord.send_embed(torrent_id, title, comment, None, is_animetosho=True)
                    bar()
        else:
            print("\nNo new comments to notify about.")

    # Handle database upload if requested
    if upload_db:
        # Determine which webhook to use for database upload notification
        webhook_for_upload = (
            secrets.discord_secret_webhook_url or secrets.discord_webhook_url
        )

        if not webhook_for_upload:
            print(
                "Error: Discord webhook URL is required for database upload notification."
            )
        else:
            print("\n" + "=" * 50)
            print("Database Upload Process")
            print("=" * 50)

            result = DatabaseUploader.process_and_upload(
                db_path=Path("database.at.json"), expiry=db_expiry
            )

            if result:
                download_url, decrypt_key, expiry = result
                print(f"\n✓ Upload successful!")

                # Only print sensitive info if NOT running in GitHub Actions
                if not is_github_actions:
                    print(f"Download URL: {download_url}")
                    print(f"Decryption Key: {decrypt_key}")
                    print(f"Expiry: {expiry}")
                else:
                    print(
                        "Sensitive information sent to Discord webhook only (not printed in logs)."
                    )

                # Create a separate webhook instance for sensitive data
                upload_discord = DiscordWebhook(webhook_for_upload)
                print("\nSending upload notification to Discord...")
                upload_discord.send_database_upload_notification(
                    download_url, decrypt_key, expiry
                )
                print("✓ Notification sent!")
            else:
                print("\n✗ Upload failed!")

    print("\nDone!")


if __name__ == "__main__":
    typer.run(main)
