#!/usr/bin/env python3
"""Nyaa.si comment scraper with Discord notifications."""

import os
from pathlib import Path
from typing import Optional

import typer
from alive_progress import alive_bar

from classes.comment_models import Comment
from classes.database_manager import DatabaseManager
from classes.database_uploader import DatabaseUploader
from classes.discord_webhook import DiscordWebhook
from classes.nyaa_scraper import NyaaScraper
from classes.secrets import Secrets


def main(
    base_url: str = typer.Argument(
        ...,
        help="The Nyaa.si URL to start scraping from (can be a listing page or a specific torrent view page like https://nyaa.si/view/2008634).",
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
    cookies_path: Optional[Path] = typer.Option(
        None,
        "--cookies",
        help="Path to local cookies file (overrides .secrets.json and env vars).",
    ),
    cookies_key: Optional[str] = typer.Option(
        None,
        "--cookies-key",
        help="Decryption key for encrypted remote cookies.",
    ),
    max_pages: Optional[int] = typer.Option(
        None,
        "--max-pages",
        help="Maximum number of pages to scrape (useful for testing or limiting scope).",
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
    A Python script to scrape comments from Nyaa.si and send notifications to Discord.
    Supports both listing pages (e.g., https://nyaa.si/?f=0&c=0_0&q=...) and specific torrent pages (e.g., https://nyaa.si/view/2008634).
    """
    # Check if running in GitHub Actions
    is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

    secrets = Secrets.load(discord_webhook_url, cookies_path, cookies_key)
    if not dump_comments and not secrets.discord_webhook_url:
        print(
            "Error: Discord webhook URL is not set. Provide it via --webhook, .secrets.json, or DISCORD_WEBHOOK_URL environment variable."
        )
        raise typer.Exit(code=1)

    db_manager = DatabaseManager()
    scraper = NyaaScraper(base_url, secrets, max_pages)
    discord = (
        DiscordWebhook(secrets.discord_webhook_url)
        if secrets.discord_webhook_url
        else None
    )

    if scraper.is_single_torrent:
        print(f"Monitoring specific torrent: {scraper.single_torrent_id}")
    else:
        print("Scraping for torrents with comments...")

    torrents_with_comments = scraper.scrape_torrents_with_comments()

    if not torrents_with_comments:
        msg = (
            "No comments found on this torrent or failed to scrape."
            if scraper.is_single_torrent
            else "No torrents with comments found or failed to scrape."
        )
        print(msg)
        raise typer.Exit()

    print(
        f"Found {len(torrents_with_comments)} torrent(s) with comments. Checking for updates..."
    )

    new_comment_queue = []
    role_cache = {}  # Cache roles: { nyaa_id: { comment_id: role } }

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
                # Cache roles for this torrent
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
                for nyaa_id, title, comment in new_comment_queue:
                    user_role = role_cache.get(nyaa_id, {}).get(comment.id)
                    discord.send_embed(nyaa_id, title, comment, user_role)
                    bar()
        else:
            print("\nNo new comments to notify about.")

    # Handle database upload if requested
    if upload_db:
        if not secrets.discord_webhook_url:
            print(
                "Error: Discord webhook URL is required for database upload notification."
            )
        else:
            print("\n" + "=" * 50)
            print("Database Upload Process")
            print("=" * 50)

            result = DatabaseUploader.process_and_upload(expiry=db_expiry)

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

                if discord:
                    print("\nSending upload notification to Discord...")
                    discord.send_database_upload_notification(
                        download_url, decrypt_key, expiry
                    )
                    print("✓ Notification sent!")
            else:
                print("\n✗ Upload failed!")

    print("\nDone!")


if __name__ == "__main__":
    typer.run(main)
