"""AnimeTosho web scraper for comments."""

import re
import time
from typing import Optional

import requests
from alive_progress import alive_bar
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from classes.comment_models import Comment, CommentUser
from classes.secrets import Secrets


class AnimeToshoScraper:
    """Scrape AnimeTosho for comments with keyword filtering.

    :ivar base_url: The base URL to scrape from.
    :ivar session: The requests session for HTTP connections.
    :ivar keywords: List of keywords to filter torrents.
    :ivar max_pages: Maximum number of pages to scrape (0 = unlimited).
    """

    BASE_DOMAIN = "https://animetosho.org"

    def __init__(
        self,
        base_url: str,
        secrets: Secrets,
        keywords: Optional[list[str]] = None,
        max_pages: int = 5,
    ) -> None:
        """Initialize the AnimeTosho scraper.

        :param base_url: The AnimeTosho URL to scrape from.
        :type base_url: str
        :param secrets: Secrets object containing configuration.
        :type secrets: Secrets
        :param keywords: Optional list of keywords to filter torrents.
        :type keywords: Optional[list[str]]
        :param max_pages: Maximum pages to scrape (0 = unlimited, default = 5).
        :type max_pages: int
        """
        self.base_url = base_url
        self.secrets = secrets
        self.keywords = keywords or []
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

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

    def _get_max_page_from_pagination(self, soup: BeautifulSoup) -> int:
        """Extract the maximum page number from the pagination element.

        :param soup: Parsed BeautifulSoup object.
        :type soup: BeautifulSoup
        :return: Maximum page number found.
        :rtype: int
        """
        pagination = soup.find("div", class_="pagination")
        if not pagination:
            return 1

        # Find all page links
        page_links = pagination.find_all("a", href=True)
        max_page = 1

        for link in page_links:
            href = link["href"]
            # Extract page number from URL
            match = re.search(r"[?&]page=(\d+)", href)
            if match:
                page_num = int(match.group(1))
                max_page = max(max_page, page_num)

        return max_page

    def get_total_pages(self, soup: BeautifulSoup) -> int:
        """Determine the total number of pages to scrape.

        :param soup: Parsed BeautifulSoup object of the first page.
        :type soup: BeautifulSoup
        :return: Total number of pages to scrape.
        :rtype: int
        """
        if self.max_pages == 0:
            # Unlimited - get max from pagination
            return self._get_max_page_from_pagination(soup)
        else:
            # Use user-specified limit
            actual_max = self._get_max_page_from_pagination(soup)
            return min(self.max_pages, actual_max)

    def _extract_torrent_id(self, comment_div: BeautifulSoup) -> Optional[str]:
        """Extract torrent ID (full slug) from comment div.

        :param comment_div: The comment div element.
        :type comment_div: BeautifulSoup
        :return: Torrent ID (full slug) or None.
        :rtype: Optional[str]
        """
        # Find the torrent link in comment_user
        comment_user = comment_div.find("div", class_="comment_user")
        if not comment_user:
            return None

        # Find link to torrent view page
        torrent_link = comment_user.find("a", href=lambda h: h and "/view/" in h)
        if not torrent_link:
            return None

        href = torrent_link["href"]
        # Extract full slug from URL like /view/gecko-something.n2030318
        match = re.search(r"/view/([^#]+)", href)
        if match:
            return match.group(1)

        return None

    def _matches_keywords(self, title: str) -> bool:
        """Check if title matches any of the keywords.

        :param title: The torrent title.
        :type title: str
        :return: True if matches any keyword, False if no keywords or no match.
        :rtype: bool
        """
        if not self.keywords:
            return True

        title_lower = title.lower()
        return any(keyword.lower() in title_lower for keyword in self.keywords)

    def _parse_relative_time(self, time_str: str) -> int:
        """Parse relative time string to Unix timestamp.

        :param time_str: Time string like "Today 15:51", "Yesterday 23:47", or "25/10/25 18:33".
        :type time_str: str
        :return: Unix timestamp.
        :rtype: int
        """
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)

        if "Today" in time_str:
            # Extract time and use current UTC date
            time_match = re.search(r"(\d{1,2}):(\d{2})", time_str)
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
                dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return int(dt.timestamp())

        elif "Yesterday" in time_str:
            time_match = re.search(r"(\d{1,2}):(\d{2})", time_str)
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
                yesterday = now - datetime.timedelta(days=1)
                dt = yesterday.replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                return int(dt.timestamp())

        else:
            # Parse dd/mm/yy HH:mm format
            date_match = re.search(
                r"(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(\d{1,2}):(\d{2})", time_str
            )
            if date_match:
                day, month, year, hour, minute = map(int, date_match.groups())
                # Handle 2-digit year
                if year < 100:
                    year += 2000
                dt = datetime.datetime(
                    year, month, day, hour, minute, 0, 0, tzinfo=datetime.timezone.utc
                )
                return int(dt.timestamp())

        # Default to current time if parsing fails
        return int(now.timestamp())

    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML content to Markdown.

        :param html_content: HTML string.
        :type html_content: str
        :return: Markdown formatted string.
        :rtype: str
        """
        # Use markdownify to convert HTML to Markdown
        markdown = md(html_content, heading_style="ATX", bullets="-")

        # Apply cleanup replacements
        replacements = {
            r"\n{3,}": "\n\n",  # Clean up excessive newlines
            r"\[https://(.*?)\]": r"[\1]",  # Remove https:// from link labels
            r"\[http://(.*?)\]": r"[\1]",  # Remove http:// from link labels
        }

        for pattern, replacement in replacements.items():
            markdown = re.sub(pattern, replacement, markdown)

        return markdown.strip()

    def scrape_comments_from_page(
        self, page_url: str
    ) -> list[tuple[str, str, Comment]]:
        """Scrape comments from a single comments page.

        :param page_url: URL of the comments page.
        :type page_url: str
        :return: List of tuples (torrent_id, torrent_title, comment).
        :rtype: list[tuple[str, str, Comment]]
        """
        soup = self._get_page(page_url)
        if not soup:
            return []

        comments_data = []
        comment_divs = soup.find_all("div", class_=["comment", "comment2"])

        for comment_div in comment_divs:
            torrent_id = self._extract_torrent_id(comment_div)
            if not torrent_id:
                continue

            # Extract torrent title
            comment_user = comment_div.find("div", class_="comment_user")
            if not comment_user:
                continue

            # Find all links - first is "Comment", second is the torrent title
            torrent_links = comment_user.find_all(
                "a", href=lambda h: h and "/view/" in h
            )
            torrent_title = (
                torrent_links[1].text.strip()
                if len(torrent_links) > 1
                else f"Torrent {torrent_id}"
            )

            # Check keyword filter
            if not self._matches_keywords(torrent_title):
                continue

            # Extract comment ID from the Comment link
            comment_link = comment_user.find("a", href=lambda h: h and "#comment" in h)
            comment_id = 0
            if comment_link:
                match = re.search(r"#comment(\d+)", comment_link["href"])
                if match:
                    comment_id = int(match.group(1))

            # Extract username
            username_elem = comment_user.find("strong")
            if not username_elem:
                continue

            username = username_elem.text.strip()
            # Handle Anonymous users with custom nicknames
            # Format: "Anonymous: "nickname"" or just "Anonymous"
            if username.startswith("Anonymous"):
                if ":" in username:
                    # Extract custom nickname after colon
                    custom_nick = username.split(":", 1)[1].strip().strip('"')
                    if custom_nick:
                        # Show as "Anonymous (nickname)"
                        username = f"Anonymous ({custom_nick})"
                    else:
                        username = "Anonymous"
                # else: username stays "Anonymous"

            # Extract timestamp
            time_elem = comment_user.find("br")
            time_str = ""
            if time_elem and time_elem.next_sibling:
                time_str = str(time_elem.next_sibling).strip()
                # Remove leading " — " if present
                time_str = re.sub(r"^[—\s]+", "", time_str)

            timestamp = (
                self._parse_relative_time(time_str) if time_str else int(time.time())
            )

            # Extract comment content
            content_div = comment_div.find("div", class_="user_message_c")
            if not content_div:
                continue

            # Convert HTML to Markdown
            message = self._html_to_markdown(str(content_div))

            # Create Comment object
            comment = Comment(
                id=comment_id,
                pos=0,  # Will be set later when organizing
                timestamp=timestamp,
                user=CommentUser(username=username, image=None),
                message=message,
            )

            comments_data.append((torrent_id, torrent_title, comment))

        return comments_data

    def scrape_all_comments(self) -> dict[str, tuple[str, list[Comment]]]:
        """Scrape all comments from AnimeTosho.

        :return: Dictionary mapping torrent_id to (title, comments_list).
        :rtype: dict[str, tuple[str, list[Comment]]]
        """
        print("Determining total number of pages...")
        first_page_soup = self._get_page(self.base_url)
        if not first_page_soup:
            return {}

        total_pages = self.get_total_pages(first_page_soup)

        if self.max_pages == 0:
            print(f"Found {total_pages} pages to scrape (unlimited mode).")
        else:
            print(f"Will scrape {total_pages} pages (max-pages={self.max_pages}).")

        all_comments = {}

        with alive_bar(total_pages, title="Scraping pages") as bar:
            for page_num in range(1, total_pages + 1):
                # Construct page URL
                separator = "?" if "?" not in self.base_url else "&"
                page_url = f"{self.base_url}{separator}page={page_num}"

                comments_data = self.scrape_comments_from_page(page_url)

                # Organize comments by torrent ID
                for torrent_id, torrent_title, comment in comments_data:
                    if torrent_id not in all_comments:
                        all_comments[torrent_id] = (torrent_title, [])
                    all_comments[torrent_id][1].append(comment)

                bar()

        # Sort comments within each torrent and assign positions
        for torrent_id in all_comments:
            title, comments = all_comments[torrent_id]
            # Sort by timestamp (oldest first)
            comments.sort(key=lambda c: c.timestamp)
            # Assign positions
            for i, comment in enumerate(comments):
                comment.pos = i + 1
            all_comments[torrent_id] = (title, comments)

        return all_comments
