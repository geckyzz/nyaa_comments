#!/usr/bin/env python3
import json
import os
import re
import secrets as py_secrets
import tarfile
import time
from enum import Enum
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
import typer
from alive_progress import alive_bar
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet
from pydantic import BaseModel, HttpUrl

# --- Enums ---


class UserRole(str, Enum):
    """Enum representing user roles on Nyaa.si."""

    TRUSTED = "trusted"
    UPLOADER = "uploader"


# --- Pydantic Models for Data Validation ---


class CommentUser(BaseModel):
    """Represents the user who made a comment.

    :ivar username: The username of the commenter.
    :ivar image: Optional URL to the user's avatar image.
    """

    username: str
    image: Optional[HttpUrl] = None


class Comment(BaseModel):
    """Represents a single comment on a torrent.

    :ivar id: Unique identifier for the comment.
    :ivar pos: Position/order of the comment on the page.
    :ivar timestamp: Unix timestamp when the comment was posted.
    :ivar user: The user who posted the comment.
    :ivar message: The content of the comment.
    """

    id: int
    pos: int
    timestamp: int
    user: CommentUser
    message: str


class Secrets(BaseModel):
    """Manages application secrets.

    :ivar discord_webhook_url: Optional Discord webhook URL for notifications.
    """

    discord_webhook_url: Optional[HttpUrl] = None

    @classmethod
    def load(cls, cli_webhook: Optional[str] = None) -> "Secrets":
        """Load secrets from CLI, .secrets.json, or environment variables.

        :param cli_webhook: Optional webhook URL provided via command line.
        :type cli_webhook: Optional[str]
        :return: Secrets instance with loaded configuration.
        :rtype: Secrets
        """
        if cli_webhook:
            return cls(discord_webhook_url=cli_webhook)

        secrets_file = Path(".secrets.json")
        if secrets_file.exists():
            try:
                data = json.loads(secrets_file.read_text())
                return cls(discord_webhook_url=data.get("discord_webhook_url"))
            except json.JSONDecodeError:
                pass

        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        return cls(discord_webhook_url=webhook_url)


# --- Core Application Classes ---


class DatabaseManager:
    """Handle reading from and writing to the JSON database.

    :ivar db_path: Path to the JSON database file.
    :ivar data: In-memory database containing comments keyed by Nyaa ID.
    """

    def __init__(self, db_path: str = "database.json") -> None:
        """Initialize the database manager.

        :param db_path: Path to the JSON database file.
        :type db_path: str
        """
        self.db_path = db_path
        self.data = self._load()

    def _load(self) -> dict[str, list[Comment]]:
        """Load the database from a file.

        :return: Dictionary mapping Nyaa IDs to lists of Comment objects.
        :rtype: dict[str, list[Comment]]
        """
        try:
            with open(self.db_path, "r") as f:
                raw_data = json.load(f)
                return {
                    k: [Comment.model_validate(c) for c in v]
                    for k, v in raw_data.items()
                }
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get_comments(self, nyaa_id: str) -> list[Comment]:
        """Retrieve comments for a specific Nyaa ID.

        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :return: List of Comment objects for the given torrent.
        :rtype: list[Comment]
        """
        return self.data.get(nyaa_id, [])

    def update_comments(self, nyaa_id: str, comments: list[Comment]) -> None:
        """Update the comments for a specific Nyaa ID.

        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :param comments: List of Comment objects to store.
        :type comments: list[Comment]
        """
        self.data[nyaa_id] = comments

    def save(self) -> None:
        """Save the current database state to the file."""
        with open(self.db_path, "w") as f:
            # Convert Pydantic models to dictionaries for JSON serialization
            serializable_data = {
                k: [c.model_dump(mode="json") for c in v] for k, v in self.data.items()
            }
            # Sort by nyaa_id (key) before saving
            sorted_data = dict(
                sorted(serializable_data.items(), key=lambda x: int(x[0]))
            )
            json.dump(sorted_data, f)


class NyaaScraper:
    """Scrape Nyaa.si for torrents with comments.

    :ivar base_url: The base URL to scrape from.
    :ivar session: The requests session for HTTP connections.
    :ivar is_single_torrent: Whether the URL is for a single torrent.
    :ivar single_torrent_id: The torrent ID if single torrent mode.
    :ivar cookies_path: Optional path to the Netscape-format cookie file.
    """

    def __init__(
        self,
        base_url: str,
        cookies_path: Optional[str] = None,
        max_pages: Optional[int] = None,
    ) -> None:
        """Initialize the Nyaa scraper.

        :param base_url: The Nyaa.si URL to scrape from.
        :type base_url: str
        :param cookies_path: Optional path to cookies file.
        :type cookies_path: Optional[str]
        :param max_pages: Optional maximum number of pages to scrape.
        :type max_pages: Optional[int]
        """
        self.base_url = base_url
        self.cookies_path = Path(cookies_path) if cookies_path else None
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        self._load_cookies()
        self.is_single_torrent = self._is_single_torrent_url(base_url)
        self.single_torrent_id = (
            self._extract_torrent_id(base_url) if self.is_single_torrent else None
        )

    def _load_cookies(self) -> None:
        """Load cookies from Netscape format file if it exists and is not empty."""
        if not self.cookies_path:
            return

        if not self.cookies_path.exists():
            return

        if self.cookies_path.stat().st_size == 0:
            return

        try:
            cookie_jar = MozillaCookieJar(str(self.cookies_path))
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            self.session.cookies.update(cookie_jar)
            print(f"Loaded {len(cookie_jar)} cookies from {self.COOKIE_PATH}")
        except Exception as e:
            print(f"Warning: Could not load cookies from {self.COOKIE_PATH}: {e}")

    def _is_single_torrent_url(self, url: str) -> bool:
        """Check if the URL is for a single torrent view page.

        :param url: The URL to check.
        :type url: str
        :return: True if URL is a single torrent view page.
        :rtype: bool
        """
        return "/view/" in url

    def _extract_torrent_id(self, url: str) -> Optional[str]:
        """Extract the torrent ID from a view URL.

        :param url: The torrent view URL.
        :type url: str
        :return: The extracted torrent ID, or None if not found.
        :rtype: Optional[str]
        """
        match = re.search(r"/view/(\d+)", url)
        return match.group(1) if match else None

    def _get_page(self, url: str, max_retries: int = 10) -> Optional[BeautifulSoup]:
        """Fetch and parse a single page with a retry mechanism.

        :param url: The URL to fetch.
        :type url: str
        :param max_retries: Maximum number of retry attempts.
        :type max_retries: int
        :return: Parsed BeautifulSoup object, or None if failed.
        :rtype: Optional[BeautifulSoup]
        """
        for attempt in range(max_retries):
            try:
                time.sleep(1)  # Respectful delay
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    print(
                        f"Error fetching {url} on attempt {attempt + 1}/{max_retries}: {e}"
                    )
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to fetch {url} after {max_retries} attempts.")
        return None

    def get_total_pages(self, soup: BeautifulSoup) -> int:
        """Determine the total number of pages to scrape.

        :param soup: Parsed BeautifulSoup object of the first page.
        :type soup: BeautifulSoup
        :return: Total number of pages to scrape.
        :rtype: int
        """
        items_per_page = 75

        if "/user/" in self.base_url:
            h3 = soup.find("h3")
            if h3 and (match := re.search(r"\((\d+)\)", h3.text)):
                return (int(match.group(1)) + items_per_page - 1) // items_per_page
        else:
            page_info = soup.find("div", class_="pagination-page-info")
            if page_info and (
                match := re.search(r"out of (\d+) results", page_info.text)
            ):
                return (int(match.group(1)) + items_per_page - 1) // items_per_page
        return 1

    def _get_comment_count_from_soup(self, soup: BeautifulSoup) -> int:
        """Get the number of comments on a torrent page.

        :param soup: Parsed BeautifulSoup object of the torrent page.
        :type soup: BeautifulSoup
        :return: Number of comments found.
        :rtype: int
        """
        comment_panel = soup.find("div", id="comments")
        if comment_panel:
            comments = comment_panel.find_all("div", class_="comment-panel")
            return len(comments)
        return 0

    def scrape_torrents_with_comments(self) -> dict[str, int]:
        """Find torrents with comments on Nyaa.si.

        :return: Dictionary mapping torrent IDs to comment counts.
        :rtype: dict[str, int]
        """
        # If this is a single torrent URL, just check if it has comments
        if self.is_single_torrent and self.single_torrent_id:
            soup = self._get_page(self.base_url)
            if not soup:
                return {}

            comment_count = self._get_comment_count_from_soup(soup)
            return {self.single_torrent_id: comment_count} if comment_count else {}

        # Original behavior for listing pages
        print("Determining total number of pages...")
        first_page_soup = self._get_page(self.base_url)
        if not first_page_soup:
            return {}

        total_pages = self.get_total_pages(first_page_soup)

        # Apply max_pages limit if specified
        if self.max_pages is not None and self.max_pages > 0:
            total_pages = min(total_pages, self.max_pages)
            print(f"Limited to {total_pages} pages (max-pages={self.max_pages}).")
        else:
            print(f"Found {total_pages} pages to scrape.")

        torrents = {}
        with alive_bar(total_pages, title="Scraping pages") as bar:
            for page_num in range(1, total_pages + 1):
                separator = "?" if "?" not in self.base_url else "&"
                page_url = f"{self.base_url}{separator}p={page_num}"
                soup = self._get_page(page_url)
                if not soup:
                    continue

                for row in soup.select("tr.default, tr.success"):
                    comment_link = row.find("a", class_="comments")
                    if comment_link:
                        view_link = row.find(
                            "a",
                            href=lambda href: href
                            and "/view/" in href
                            and "#" not in href,
                        )
                        if view_link:
                            nyaa_id = view_link["href"].split("/")[-1]
                            try:
                                comment_count = int(
                                    re.sub(r"\D", "", comment_link.text)
                                )
                                torrents[nyaa_id] = comment_count
                            except (ValueError, TypeError):
                                continue
                bar()
        return torrents

    def get_torrent_title(self, nyaa_id: str) -> str:
        """Fetch the title of a torrent.

        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :return: The torrent title, or a default string if not found.
        :rtype: str
        """
        soup = self._get_page(f"https://nyaa.si/view/{nyaa_id}")
        title_elem = soup.find("h3", class_="panel-title") if soup else None
        return title_elem.text.strip() if title_elem else f"Torrent ID {nyaa_id}"

    def _get_user_role(
        self, panel, nyaa_id: str, soup: BeautifulSoup
    ) -> Optional[UserRole]:
        """Detect user role (Trusted/Uploader) from the comment panel or torrent page.

        :param panel: The BeautifulSoup comment panel element.
        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :param soup: The complete torrent page soup.
        :type soup: BeautifulSoup
        :return: The detected user role, or None if no role detected.
        :rtype: Optional[UserRole]
        """
        # Check for Trusted user
        user_link = panel.find("a", href=lambda href: href and "/user/" in href)
        if user_link:
            # Check if user has "Trusted" title attribute
            if user_link.has_attr("title") and user_link["title"] == "Trusted":
                return UserRole.TRUSTED

            # Check if user is marked as uploader in the comment
            parent_p = user_link.find_parent("p")
            if parent_p and "(uploader)" in parent_p.text:
                return UserRole.UPLOADER

        # Check if this user is the uploader from the torrent details
        if soup:
            submitter_div = soup.find(
                "div",
                class_="col-md-5",
                string=lambda text: text and "Anonymous" in text,
            )
            if not submitter_div:
                # Try finding it differently
                for div in soup.find_all("div", class_="col-md-5"):
                    if div.text and "Anonymous" in div.text:
                        submitter_div = div
                        break

            if submitter_div:
                # Check if there's a user link after "Anonymous"
                uploader_link = submitter_div.find(
                    "a", href=lambda href: href and "/user/" in href
                )
                if uploader_link and user_link:
                    if uploader_link.text.strip() == user_link.text.strip():
                        return UserRole.UPLOADER

        return None

    def _parse_comment(
        self, panel, index: int, nyaa_id: str, soup: Optional[BeautifulSoup] = None
    ) -> Optional[Comment]:
        """Parse a single comment panel into a Comment object.

        :param panel: The BeautifulSoup comment panel element.
        :param index: The index/position of this comment.
        :type index: int
        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :param soup: Optional complete torrent page soup for role detection.
        :type soup: Optional[BeautifulSoup]
        :return: Parsed Comment object, or None if parsing failed.
        :rtype: Optional[Comment]
        """
        user_link = panel.find("a", href=lambda href: href and "/user/" in href)
        user_avatar = panel.find("img", class_="avatar")
        timestamp_tag = panel.find("small", {"data-timestamp-swap": True})
        content_div = panel.find("div", class_="comment-content")

        if not (
            user_link and timestamp_tag and content_div and content_div.has_attr("id")
        ):
            return None

        avatar_url = None
        if user_avatar and user_avatar.has_attr("src"):
            avatar_url = urljoin("https://nyaa.si", user_avatar["src"])

        try:
            comment_id_str = re.sub(r"\D", "", content_div["id"])
            if not comment_id_str:
                return None

            return Comment(
                id=int(comment_id_str),
                pos=index + 1,
                timestamp=int(timestamp_tag["data-timestamp"]),
                user=CommentUser(username=user_link.text.strip(), image=avatar_url),
                message=content_div.text.strip(),
            )
        except Exception as e:
            print(f"Could not parse a comment on Nyaa ID {nyaa_id}: {e}")
            return None

    def scrape_comments_for_torrent(
        self, nyaa_id: str
    ) -> tuple[list[Comment], dict[int, Optional[UserRole]]]:
        """Scrape all comments from a specific torrent view page.

        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :return: Tuple of (comments list, roles dict mapping comment_id to role).
        :rtype: tuple[list[Comment], dict[int, Optional[UserRole]]]
        """
        url = f"https://nyaa.si/view/{nyaa_id}"
        soup = self._get_page(url)
        if not soup:
            return [], {}

        comment_panels = soup.find_all("div", class_="comment-panel")
        comments = []
        roles = {}

        for i, panel in enumerate(comment_panels):
            comment = self._parse_comment(panel, i, nyaa_id, soup)
            if comment:
                comments.append(comment)
                # Get role for this comment
                role = self._get_user_role(panel, nyaa_id, soup)
                if role:
                    roles[comment.id] = role

        # Sort comments by timestamp (oldest first) to ensure consistent ordering
        comments.sort(key=lambda c: c.timestamp)
        return comments, roles


class DiscordWebhook:
    """Handle sending notifications to a Discord webhook.

    :ivar webhook_url: The Discord webhook URL.
    """

    def __init__(self, webhook_url: HttpUrl) -> None:
        """Initialize the Discord webhook handler.

        :param webhook_url: The Discord webhook URL.
        :type webhook_url: HttpUrl
        """
        self.webhook_url = str(webhook_url)

    def _create_embed(
        self,
        nyaa_id: str,
        torrent_title: str,
        comment: Comment,
        user_role: Optional[UserRole] = None,
    ) -> dict:
        """Create a Discord embed for a comment.

        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :param torrent_title: The title of the torrent.
        :type torrent_title: str
        :param comment: The comment to create an embed for.
        :type comment: Comment
        :param user_role: Optional user role to display.
        :type user_role: Optional[UserRole]
        :return: Discord embed dictionary.
        :rtype: dict
        """
        user_avatar_url = (
            str(comment.user.image)
            if comment.user.image
            else "https://nyaa.si/static/img/avatar/default.png"
        )

        # Format username with role if present
        author_name = comment.user.username
        if user_role == UserRole.TRUSTED:
            author_name = f"{comment.user.username} (trusted)"
        elif user_role == UserRole.UPLOADER:
            author_name = f"{comment.user.username} (uploader)"

        return {
            "title": f"New Comment on: {torrent_title}",
            "url": f"https://nyaa.si/view/{nyaa_id}#com-{comment.pos}",
            "color": 0x0085FF,
            "author": {
                "name": author_name,
                "url": f"https://nyaa.si/user/{comment.user.username}",
                "icon_url": user_avatar_url,
            },
            "thumbnail": {"url": user_avatar_url},
            "description": comment.message,
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(comment.timestamp)
            ),
        }

    def send_embed(
        self,
        nyaa_id: str,
        torrent_title: str,
        new_comment: Comment,
        user_role: Optional[UserRole] = None,
    ) -> None:
        """Send a formatted embed for a new comment to Discord.

        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :param torrent_title: The title of the torrent.
        :type torrent_title: str
        :param new_comment: The new comment to send.
        :type new_comment: Comment
        :param user_role: Optional user role to display.
        :type user_role: Optional[UserRole]
        """
        embed = self._create_embed(nyaa_id, torrent_title, new_comment, user_role)
        payload = {"embeds": [embed]}

        while True:
            try:
                response = requests.post(self.webhook_url, json=payload, timeout=10)

                if response.status_code == 429:
                    retry_after = float(response.json().get("retry_after", 1))
                    print(
                        f"Rate limited by Discord. Waiting for {retry_after:.2f} seconds."
                    )
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()

                if (
                    "X-RateLimit-Remaining" in response.headers
                    and int(response.headers["X-RateLimit-Remaining"]) == 0
                ):
                    reset_after = float(
                        response.headers.get("X-RateLimit-Reset-After", 1)
                    )
                    print(
                        f"Rate limit bucket depleted. Waiting {reset_after:.2f} seconds for reset."
                    )
                    time.sleep(reset_after)

                break
            except requests.RequestException as e:
                print(f"Error sending webhook for Nyaa ID {nyaa_id}: {e}")
                break

    def send_database_upload_notification(
        self, download_url: str, decrypt_key: str, expiry: str
    ) -> None:
        """Send notification about database upload to Catbox Litterbox.

        :param download_url: The URL to download the encrypted database.
        :type download_url: str
        :param decrypt_key: The decryption key.
        :type decrypt_key: str
        :param expiry: The expiry time of the upload.
        :type expiry: str
        """
        embed = {
            "title": "Database Backup Uploaded",
            "color": 0x00FF00,
            "description": "Encrypted database backup has been uploaded to Catbox Litterbox.",
            "fields": [
                {"name": "Download URL", "value": download_url, "inline": False},
                {
                    "name": "Decryption Key",
                    "value": f"```{decrypt_key}```",
                    "inline": False,
                },
                {"name": "Expiry", "value": expiry, "inline": True},
            ],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        }
        payload = {"embeds": [embed]}

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error sending database upload notification: {e}")


class DatabaseUploader:
    """Handle encrypting and uploading database to Catbox Litterbox."""

    LITTERBOX_API = "https://litterbox.catbox.moe/resources/internals/api.php"

    @staticmethod
    def generate_encryption_key() -> tuple[bytes, str]:
        """Generate a random encryption key.

        :return: Tuple of (key bytes, key string in base64).
        :rtype: tuple[bytes, str]
        """
        key = Fernet.generate_key()
        return key, key.decode("utf-8")

    @staticmethod
    def encrypt_file(file_path: str, key: bytes) -> str:
        """Encrypt a file using Fernet symmetric encryption.

        :param file_path: Path to the file to encrypt.
        :type file_path: str
        :param key: Encryption key.
        :type key: bytes
        :return: Path to the encrypted file.
        :rtype: str
        """
        fernet = Fernet(key)

        with open(file_path, "rb") as f:
            data = f.read()

        encrypted_data = fernet.encrypt(data)

        encrypted_path = f"{file_path}.encrypted"
        with open(encrypted_path, "wb") as f:
            f.write(encrypted_data)

        return encrypted_path

    @staticmethod
    def create_tarball(file_path: str) -> str:
        """Create a tarball of the database file.

        :param file_path: Path to the file to archive.
        :type file_path: str
        :return: Path to the tarball.
        :rtype: str
        """
        tarball_path = f"{file_path}.tar.gz"
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(file_path, arcname=Path(file_path).name)
        return tarball_path

    @classmethod
    def upload_to_litterbox(cls, file_path: str, expiry: str = "12h") -> Optional[str]:
        """Upload file to Catbox Litterbox.

        :param file_path: Path to the file to upload.
        :type file_path: str
        :param expiry: Expiry time (1h, 12h, 24h, 72h).
        :type expiry: str
        :return: Download URL if successful, None otherwise.
        :rtype: Optional[str]
        """
        try:
            with open(file_path, "rb") as f:
                files = {"fileToUpload": f}
                data = {"reqtype": "fileupload", "time": expiry}

                response = requests.post(
                    cls.LITTERBOX_API, files=files, data=data, timeout=60
                )
                response.raise_for_status()

                url = response.text.strip()
                if url.startswith("http"):
                    return url
                else:
                    print(f"Upload failed: {url}")
                    return None
        except requests.RequestException as e:
            print(f"Error uploading to Litterbox: {e}")
            return None

    @classmethod
    def process_and_upload(
        cls, db_path: str = "database.json", expiry: str = "12h"
    ) -> Optional[tuple[str, str, str]]:
        """Encrypt database, create tarball, and upload to Litterbox.

        :param db_path: Path to the database file.
        :type db_path: str
        :param expiry: Expiry time for the upload.
        :type expiry: str
        :return: Tuple of (download_url, decryption_key, expiry) if successful, None otherwise.
        :rtype: Optional[tuple[str, str, str]]
        """
        if not Path(db_path).exists():
            print(f"Database file {db_path} not found.")
            return None

        print("Generating encryption key...")
        key, key_str = cls.generate_encryption_key()

        print("Encrypting database...")
        encrypted_path = cls.encrypt_file(db_path, key)

        print("Creating tarball...")
        tarball_path = cls.create_tarball(encrypted_path)

        print(f"Uploading to Litterbox (expiry: {expiry})...")
        download_url = cls.upload_to_litterbox(tarball_path, expiry)

        # Cleanup temporary files
        try:
            Path(encrypted_path).unlink()
            Path(tarball_path).unlink()
        except Exception as e:
            print(f"Warning: Failed to cleanup temporary files: {e}")

        if download_url:
            return download_url, key_str, expiry
        return None


# --- Main Application Logic ---


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
    cookies_path: Optional[str] = typer.Option(
        None,
        "--cookies",
        help="Path to cookies file (defaults to cookies.txt).",
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

    secrets = Secrets.load(discord_webhook_url)
    if not dump_comments and not secrets.discord_webhook_url:
        print(
            "Error: Discord webhook URL is not set. Provide it via --webhook, .secrets.json, or DISCORD_WEBHOOK_URL environment variable."
        )
        raise typer.Exit(code=1)

    db_manager = DatabaseManager()
    scraper = NyaaScraper(base_url, cookies_path, max_pages)
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
