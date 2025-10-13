"""Secrets management for application configuration."""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, HttpUrl


class Secrets(BaseModel):
    """Manages application secrets.

    :ivar discord_webhook_url: Optional Discord webhook URL for notifications.
    :ivar discord_secret_webhook_url: Optional separate webhook URL for sensitive data (database backups).
    :ivar cookies_url: Optional URL to remote cookies file.
    :ivar cookies_path: Optional local path to cookies file.
    :ivar cookies_key: Optional decryption key for encrypted remote cookies.
    """

    discord_webhook_url: Optional[HttpUrl] = None
    discord_secret_webhook_url: Optional[HttpUrl] = None
    cookies_url: Optional[str] = None
    cookies_path: Optional[Path] = None
    cookies_key: Optional[str] = None

    @classmethod
    def load(
        cls,
        cli_webhook: Optional[str] = None,
        cli_cookies: Optional[Path] = None,
        cli_cookies_key: Optional[str] = None,
        cli_secret_webhook: Optional[str] = None,
    ) -> "Secrets":
        """Load secrets from CLI, .secrets.json, or environment variables.

        :param cli_webhook: Optional webhook URL provided via command line.
        :type cli_webhook: Optional[str]
        :param cli_cookies: Optional cookies path provided via command line.
        :type cli_cookies: Optional[Path]
        :param cli_cookies_key: Optional cookies decryption key from CLI.
        :type cli_cookies_key: Optional[str]
        :param cli_secret_webhook: Optional secret webhook URL for sensitive data from CLI.
        :type cli_secret_webhook: Optional[str]
        :return: Secrets instance with loaded configuration.
        :rtype: Secrets
        """
        # CLI arguments take precedence
        if cli_webhook or cli_cookies or cli_secret_webhook:
            return cls(
                discord_webhook_url=cli_webhook,
                discord_secret_webhook_url=cli_secret_webhook,
                cookies_path=cli_cookies,
                cookies_key=cli_cookies_key,
            )

        # Try loading from .secrets.json
        secrets_file = Path(".secrets.json")
        if secrets_file.exists():
            try:
                data = json.loads(secrets_file.read_text())
                cookies_path_data = data.get("cookies_path")
                cookies_url_data = data.get("cookies_url")

                return cls(
                    discord_webhook_url=data.get("discord_webhook_url"),
                    discord_secret_webhook_url=data.get("discord_secret_webhook_url"),
                    cookies_url=cookies_url_data,
                    cookies_path=(
                        Path(cookies_path_data) if cookies_path_data else None
                    ),
                    cookies_key=data.get("cookies_key"),
                )
            except json.JSONDecodeError:
                pass

        # Fall back to environment variables
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        secret_webhook_url = os.environ.get("DISCORD_SECRET_WEBHOOK_URL")
        cookies_url = os.environ.get("COOKIES_URL")
        cookies_path_env = os.environ.get("COOKIES_PATH")
        cookies_key = os.environ.get("COOKIES_KEY")

        return cls(
            discord_webhook_url=webhook_url,
            discord_secret_webhook_url=secret_webhook_url,
            cookies_url=cookies_url,
            cookies_path=Path(cookies_path_env) if cookies_path_env else None,
            cookies_key=cookies_key,
        )
