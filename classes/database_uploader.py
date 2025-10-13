"""Database uploader for Catbox Litterbox."""

from pathlib import Path
from typing import Optional

import requests

from modules.crypto_utils import CryptoUtils


class DatabaseUploader:
    """Handle encrypting and uploading database to Catbox Litterbox."""

    LITTERBOX_API = "https://litterbox.catbox.moe/resources/internals/api.php"

    @classmethod
    def upload_to_litterbox(cls, file_path: Path, expiry: str = "12h") -> Optional[str]:
        """Upload file to Catbox Litterbox.

        :param file_path: Path to the file to upload.
        :type file_path: Path
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
        cls, db_path: Path = Path("database.json"), expiry: str = "12h"
    ) -> Optional[tuple[str, str, str]]:
        """Encrypt database, create tarball, and upload to Litterbox.

        :param db_path: Path to the database file.
        :type db_path: Path
        :param expiry: Expiry time for the upload.
        :type expiry: str
        :return: Tuple of (download_url, decryption_key, expiry) if successful, None otherwise.
        :rtype: Optional[tuple[str, str, str]]
        """
        if not db_path.exists():
            print(f"Database file {db_path} not found.")
            return None

        print("Encrypting and packaging database...")
        tarball_path, key_str = CryptoUtils.encrypt_and_package(db_path)

        print(f"Uploading to Litterbox (expiry: {expiry})...")
        download_url = cls.upload_to_litterbox(tarball_path, expiry)

        # Cleanup temporary files
        try:
            tarball_path.unlink()
        except Exception as e:
            print(f"Warning: Failed to cleanup temporary files: {e}")

        if download_url:
            return download_url, key_str, expiry
        return None


# --- Main Application Logic ---
