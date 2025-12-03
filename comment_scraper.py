#!/usr/bin/env python3
"""
Unified comment scraper for Nyaa.si, Sukebei, and AnimeTosho with Discord notifications.
"""

import os
from pathlib import Path
from typing import List, Optional

import typer
from alive_progress import alive_bar

from classes.animetosho_scraper import AnimeToshoScraper
from classes.database_manager import DatabaseManager
from classes.database_uploader import DatabaseUploader
from classes.discord_webhook import DiscordWebhook
from classes.nyaa_scraper import NyaaScraper
from classes.secrets import Secrets


def main(
    base_url: str = typer.Argument(
        ...,
        help="The Nyaa.si, Sukebei, or AnimeTosho URL to start scraping from.",
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
    cookies_path: Optional[Path] = typer.Option(
        None,
        "--cookies",
        help="Path to local cookies file (for Nyaa/Sukebei).",
    ),
    cookies_key: Optional[str] = typer.Option(
        None,
        "--cookies-key",
        help="Decryption key for encrypted remote cookies (for Nyaa/Sukebei).",
    ),
    keywords: Optional[List[str]] = typer.Option(
        None,
        "--keyword",
        "-k",
        help="Filter torrents by keyword (for AnimeTosho, can be specified multiple times).",
    ),
    max_pages: Optional[int] = typer.Option(
        None,
        "--max-pages",
        help="Maximum number of pages to scrape (0 for unlimited on AnimeTosho, default 5 for AT).",
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
    A Python script to scrape comments from Nyaa.si, Sukebei, and AnimeTosho, and send notifications to Discord.
    """
    is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

    # Determine scraper type and database path
    is_animetosho = "animetosho.org" in base_url
    is_sukebei = "sukebei.nyaa.si" in base_url

    if is_animetosho:
        db_path = Path("database.at.json")
        scraper_name = "AnimeTosho"
    elif is_sukebei:
        db_path = Path("database.sukebei.json")
        scraper_name = "Sukebei"
    else:
        db_path = Path("database.json")
        scraper_name = "Nyaa.si"

    print(f"Using database: {db_path}")

    secrets = Secrets.load(
        discord_webhook_url, cookies_path, cookies_key, discord_secret_webhook_url
    )
    if not dump_comments and not secrets.discord_webhook_url:
        print(
            "Error: Discord webhook URL is not set. Provide it via --webhook, .secrets.json, or DISCORD_WEBHOOK_URL environment variable."
        )
        raise typer.Exit(code=1)

    if upload_db and is_github_actions and not secrets.discord_secret_webhook_url:
        print(
            "Error: Database upload in GitHub Actions requires a separate secret webhook URL.\n"
            "Provide it via DISCORD_SECRET_WEBHOOK_URL environment variable or .secrets.json to prevent exposing sensitive data."
        )
        raise typer.Exit(code=1)

    db_manager = DatabaseManager(db_path=db_path)
    discord = (
        DiscordWebhook(secrets.discord_webhook_url)
        if secrets.discord_webhook_url
        else None
    )

    new_comment_queue = []

    if is_animetosho:
        # AnimeTosho scraping logic
        scraper = AnimeToshoScraper(base_url, secrets, keywords, max_pages or 5)
        if keywords:
            print(f"Filtering by keywords: {', '.join(keywords)}")

        print(f"Scraping {scraper_name} for comments...")
        all_comments = scraper.scrape_all_comments()

        if not all_comments:
            print("No comments found or failed to scrape.")
            raise typer.Exit()

        print(
            f"Found {len(all_comments)} torrent(s) with comments. Checking for updates..."
        )

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
    else:
        # Nyaa.si/Sukebei scraping logic
        scraper = NyaaScraper(base_url, secrets, max_pages)
        if scraper.is_single_torrent:
            print(f"Monitoring specific torrent: {scraper.single_torrent_id}")
        else:
            print(f"Scraping {scraper_name} for torrents with comments...")

        torrents_with_comments = scraper.scrape_torrents_with_comments()

        if not torrents_with_comments:
            msg = (
                "No comments found on this torrent or failed to scrape."
                if scraper.is_single_torrent
                else f"No torrents with comments found on {scraper_name} or failed to scrape."
            )
            print(msg)
            raise typer.Exit()

        print(
            f"Found {len(torrents_with_comments)} torrent(s) with comments. Checking for updates..."
        )

        role_cache = {}
        with alive_bar(len(torrents_with_comments), title="Checking torrents") as bar:
            for nyaa_id, current_comment_count in torrents_with_comments.items():
                bar.text(f"-> Checking Nyaa ID: {nyaa_id}")
                stored_comments = db_manager.get_comments(nyaa_id)
                stored_comment_count = len(stored_comments)

                if dump_comments and not stored_comments:
                    all_comments, roles = scraper.scrape_comments_for_torrent(nyaa_id)
                    db_manager.update_comments(nyaa_id, all_comments)
                elif current_comment_count > stored_comment_count:
                    all_comments, roles = scraper.scrape_comments_for_torrent(nyaa_id)
                    title = scraper.get_torrent_title(nyaa_id)
                    new_comments = all_comments[stored_comment_count:]
                    new_comment_queue.extend(
                        (nyaa_id, title, comment) for comment in new_comments
                    )
                    db_manager.update_comments(nyaa_id, all_comments)
                    if roles:
                        role_cache[nyaa_id] = roles
                bar()

    print("Saving database...")
    db_manager.save()

    if not dump_comments and discord:
        if new_comment_queue:
            new_comment_queue.sort(key=lambda item: item[2].timestamp)
            print(
                f"\nSending {len(new_comment_queue)} new comment notifications to Discord..."
            )
            with alive_bar(
                len(new_comment_queue), title="Sending notifications"
            ) as bar:
                if is_animetosho:
                    for torrent_id, title, comment in new_comment_queue:
                        discord.send_embed(
                            torrent_id, title, comment, None, is_animetosho=True
                        )
                        bar()
                else:
                    role_cache = locals().get("role_cache", {})
                    for nyaa_id, title, comment in new_comment_queue:
                        user_role = role_cache.get(nyaa_id, {}).get(comment.id)
                        discord.send_embed(
                            nyaa_id, title, comment, user_role, is_sukebei=is_sukebei
                        )
                        bar()
        else:
            print("\nNo new comments to notify about.")

    if upload_db:
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
                db_path=db_path, expiry=db_expiry
            )
            if result:
                download_url, decrypt_key, expiry = result
                print("\n✓ Upload successful!")
                if not is_github_actions:
                    print(f"Download URL: {download_url}")
                    print(f"Decryption Key: {decrypt_key}")
                    print(f"Expiry: {expiry}")
                else:
                    print(
                        "Sensitive information sent to Discord webhook only (not printed in logs)."
                    )
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
