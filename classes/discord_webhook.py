"""Discord webhook handler for notifications."""

import time
from typing import Optional

import requests
from pydantic import HttpUrl

from classes.comment_models import Comment
from classes.user_role import UserRole


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
