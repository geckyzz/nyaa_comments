#!/usr/bin/env python3
"""Shared cryptography utilities for encryption and decryption operations."""

import tarfile
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

        encrypted_path = file_path.with_suffix(file_path.suffix + ".encrypted")
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

    @staticmethod
    def create_tarball(file_path: Path) -> Path:
        """Create a tarball of a file.

        :param file_path: Path to the file to archive.
        :type file_path: Path
        :return: Path to the tarball.
        :rtype: Path
        """
        tarball_path = file_path.with_suffix(file_path.suffix + ".tar.gz")
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(file_path, arcname=file_path.name)
        return tarball_path

    @staticmethod
    def extract_tarball(tarball_path: Path, output_dir: Optional[Path] = None) -> Path:
        """Extract a tarball and return the path to the extracted file.

        :param tarball_path: Path to the tarball file.
        :type tarball_path: Path
        :param output_dir: Optional directory to extract to (defaults to current dir).
        :type output_dir: Optional[Path]
        :return: Path to the extracted file.
        :rtype: Path
        """
        # Use current directory if output_dir is None
        extract_to = output_dir if output_dir else Path.cwd()
        
        with tarfile.open(tarball_path, "r:gz") as tar:
            members = tar.getmembers()
            if not members:
                raise ValueError("Tarball is empty")

            extracted_file_name = members[0].name
            tar.extract(extracted_file_name, path=extract_to)

            return extract_to / extracted_file_name

    @classmethod
    def encrypt_and_package(
        cls, file_path: Path, output_name: Optional[str] = None
    ) -> tuple[Path, str]:
        """Encrypt a file and package it into a tarball.

        :param file_path: Path to the file to encrypt.
        :type file_path: Path
        :param output_name: Optional name for output (without extensions).
        :type output_name: Optional[str]
        :return: Tuple of (tarball path, encryption key string).
        :rtype: tuple[Path, str]
        """
        # Generate encryption key
        key, key_str = cls.generate_encryption_key()

        # Encrypt file
        encrypted_path = cls.encrypt_file(file_path, key)

        # Create tarball
        tarball_path = cls.create_tarball(encrypted_path)

        # Clean up encrypted file
        encrypted_path.unlink()

        # Rename if output name specified
        if output_name:
            new_tarball_path = tarball_path.parent / f"{output_name}.tar.gz"
            tarball_path.rename(new_tarball_path)
            tarball_path = new_tarball_path

        return tarball_path, key_str

    @classmethod
    def decrypt_and_extract(
        cls, tarball_path: Path, decryption_key: str, output_path: Path
    ) -> None:
        """Decrypt and extract an encrypted tarball.

        :param tarball_path: Path to the encrypted tarball.
        :type tarball_path: Path
        :param decryption_key: Decryption key string.
        :type decryption_key: str
        :param output_path: Path to save the decrypted file.
        :type output_path: Path
        """
        # Extract tarball
        encrypted_file = cls.extract_tarball(tarball_path)

        try:
            # Decrypt file
            key = decryption_key.encode("utf-8")
            cls.decrypt_file(encrypted_file, key, output_path)
        finally:
            # Clean up extracted encrypted file
            if encrypted_file.exists():
                encrypted_file.unlink()
