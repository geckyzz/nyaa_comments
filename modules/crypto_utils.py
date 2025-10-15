#!/usr/bin/env python3
"""Shared cryptography utilities for encryption and decryption operations."""

import gzip
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet


class CryptoUtils:
    """Utility class for encryption and decryption operations."""

    @staticmethod
    def generate_encryption_key() -> tuple[bytes, str]:
        """Generate a random encryption key.

        :return: Tuple of (key bytes, key string in base64).
        :rtype: tuple[bytes, str]
        """
        key = Fernet.generate_key()
        return key, key.decode("utf-8")

    @staticmethod
    def compress_file(file_path: Path) -> Path:
        """Compress a file using gzip.

        :param file_path: Path to the file to compress.
        :type file_path: Path
        :return: Path to the compressed file.
        :rtype: Path
        """
        compressed_path = file_path.with_suffix(file_path.suffix + ".gz")
        with open(file_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                f_out.writelines(f_in)
        return compressed_path

    @staticmethod
    def decompress_file(compressed_path: Path, output_path: Path) -> None:
        """Decompress a gzip file.

        :param compressed_path: Path to the compressed file.
        :type compressed_path: Path
        :param output_path: Path to save the decompressed file.
        :type output_path: Path
        """
        with gzip.open(compressed_path, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                f_out.writelines(f_in)

    @staticmethod
    def encrypt_file(file_path: Path, key: bytes) -> Path:
        """Encrypt a file using Fernet symmetric encryption.

        :param file_path: Path to the file to encrypt.
        :type file_path: Path
        :param key: Encryption key.
        :type key: bytes
        :return: Path to the encrypted file.
        :rtype: Path
        """
        fernet = Fernet(key)

        with open(file_path, "rb") as f:
            data = f.read()

        encrypted_data = fernet.encrypt(data)

        encrypted_path = file_path.with_suffix(file_path.suffix + ".enc")
        with open(encrypted_path, "wb") as f:
            f.write(encrypted_data)

        return encrypted_path

    @staticmethod
    def decrypt_file(encrypted_path: Path, key: bytes, output_path: Path) -> None:
        """Decrypt a file using Fernet symmetric decryption.

        :param encrypted_path: Path to the encrypted file.
        :type encrypted_path: Path
        :param key: Decryption key.
        :type key: bytes
        :param output_path: Path to save the decrypted file.
        :type output_path: Path
        """
        fernet = Fernet(key)

        with open(encrypted_path, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = fernet.decrypt(encrypted_data)

        with open(output_path, "wb") as f:
            f.write(decrypted_data)

    @classmethod
    def encrypt_and_package(
        cls, file_path: Path, output_name: Optional[str] = None
    ) -> tuple[Path, str]:
        """Compress and encrypt a file.

        The file is first compressed with gzip, then encrypted with Fernet.
        The final file has .enc extension.

        :param file_path: Path to the file to encrypt.
        :type file_path: Path
        :param output_name: Optional name for output (without extensions).
        :type output_name: Optional[str]
        :return: Tuple of (encrypted file path, encryption key string).
        :rtype: tuple[Path, str]
        """
        # Generate encryption key
        key, key_str = cls.generate_encryption_key()

        # Compress file first
        compressed_path = cls.compress_file(file_path)

        try:
            # Then encrypt the compressed file
            encrypted_path = cls.encrypt_file(compressed_path, key)
        finally:
            # Clean up compressed file
            compressed_path.unlink()

        # Rename if output name specified
        if output_name:
            new_encrypted_path = encrypted_path.parent / f"{output_name}.gz.enc"
            encrypted_path.rename(new_encrypted_path)
            encrypted_path = new_encrypted_path

        return encrypted_path, key_str

    @classmethod
    def decrypt_and_extract(
        cls, encrypted_path: Path, decryption_key: str, output_path: Path
    ) -> None:
        """Decrypt and decompress an encrypted file.

        :param encrypted_path: Path to the encrypted file.
        :type encrypted_path: Path
        :param decryption_key: Decryption key string.
        :type decryption_key: str
        :param output_path: Path to save the decrypted and decompressed file.
        :type output_path: Path
        """
        # Decrypt file first
        key = decryption_key.encode("utf-8")
        compressed_path = encrypted_path.with_suffix("")
        cls.decrypt_file(encrypted_path, key, compressed_path)

        try:
            # Then decompress
            cls.decompress_file(compressed_path, output_path)
        finally:
            # Clean up decompressed file
            if compressed_path.exists():
                compressed_path.unlink()
