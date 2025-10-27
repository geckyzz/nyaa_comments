"""Nyaa.si web scraper for torrents and comments."""

import re
import time
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from alive_progress import alive_bar
from bs4 import BeautifulSoup

from classes.comment_models import Comment, CommentUser
from classes.secrets import Secrets
from classes.user_role import UserRole
from modules.crypto_utils import CryptoUtils


class NyaaScraper:
    """Scrape Nyaa.si for torrents with comments.

    :ivar base_url: The base URL to scrape from.
    :ivar site_base_url: The base URL of the site (e.g., https://nyaa.si).
    :ivar session: The requests session for HTTP connections.
    :ivar is_single_torrent: Whether the URL is for a single torrent.
    :ivar single_torrent_id: The torrent ID if single torrent mode.
    :ivar cookies_path: Optional path to the Netscape-format cookie file.
    """

    def __init__(
        self,
        base_url: str,
        secrets: Secrets,
        max_pages: Optional[int] = None,
    ) -> None:
        """Initialize the Nyaa scraper.

        :param base_url: The Nyaa.si URL to scrape from.
        :type base_url: str
        :param secrets: Secrets object containing cookies configuration.
        :type secrets: Secrets
        :param max_pages: Optional maximum number of pages to scrape.
        :type max_pages: Optional[int]
        """
        self.base_url = base_url
        parsed_url = urlparse(self.base_url)
        self.site_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.secrets = secrets
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
        """Load cookies from local file or remote URL."""
        # Try remote URL first
        if self.secrets.cookies_url:
            self._load_remote_cookies(
                self.secrets.cookies_url, self.secrets.cookies_key
            )
        # Fall back to local path
        elif self.secrets.cookies_path:
            self._load_local_cookies(self.secrets.cookies_path)

    def _load_local_cookies(self, cookies_path: Path) -> None:
        """Load cookies from local Netscape format file."""
        if not cookies_path.exists():
            return

        if cookies_path.stat().st_size == 0:
            return

        try:
            cookie_jar = MozillaCookieJar(str(cookies_path))
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            self.session.cookies.update(cookie_jar)
            print(f"Loaded {len(cookie_jar)} cookies from {cookies_path}")
        except Exception as e:
            print(f"Warning: Could not load cookies from {cookies_path}: {e}")

    def _load_remote_cookies(
        self, cookies_url: str, decryption_key: Optional[str] = None
    ) -> None:
        """Load cookies from remote URL, with optional decryption.

        :param cookies_url: URL to download cookies from.
        :type cookies_url: str
        :param decryption_key: Optional decryption key for encrypted cookies.
        :type decryption_key: Optional[str]
        """
        try:
            print(f"Downloading cookies from {cookies_url}...")
            response = requests.get(cookies_url, timeout=30)
            response.raise_for_status()

            # Create temp directory for cookies
            temp_dir = Path(".temp_cookies")
            temp_dir.mkdir(exist_ok=True)

            # Determine if encrypted (ends with .enc or .gz.enc)
            is_encrypted = cookies_url.endswith(".enc")

            if is_encrypted and decryption_key:
                # Save encrypted file
                encrypted_path = temp_dir / "cookies.enc"
                encrypted_path.write_bytes(response.content)

                # Decrypt and decompress
                cookies_path = temp_dir / "cookies.txt"
                print("Decrypting cookies...")
                CryptoUtils.decrypt_and_extract(
                    encrypted_path, decryption_key, cookies_path
                )

                # Load cookies
                self._load_local_cookies(cookies_path)

                # Cleanup
                encrypted_path.unlink(missing_ok=True)
                cookies_path.unlink(missing_ok=True)
            else:
                # Save and load plain cookies file
                cookies_path = temp_dir / "cookies.txt"
                cookies_path.write_bytes(response.content)
                self._load_local_cookies(cookies_path)
                cookies_path.unlink(missing_ok=True)

            # Cleanup temp directory
            try:
                temp_dir.rmdir()
            except Exception as _:
                pass

        except Exception as e:
            print(f"Warning: Could not load remote cookies: {e}")

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
        soup = self._get_page(f"{self.site_base_url}/view/{nyaa_id}")
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
            avatar_url = urljoin(self.site_base_url, user_avatar["src"])

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
        url = f"{self.site_base_url}/view/{nyaa_id}"
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
