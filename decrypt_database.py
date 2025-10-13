#!/usr/bin/env python3
"""Utility script to encrypt/decrypt and extract/package files."""

from pathlib import Path
from typing import Optional

import typer

from modules.crypto_utils import CryptoUtils

app = typer.Typer()


@app.command()
def encrypt(
    input_file: Path = typer.Argument(..., help="Path to the file to encrypt."),
    output_name: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output name (without extensions)."
    ),
):
    """
    Encrypt a file and package it into a tarball.

    Generates a random encryption key and outputs an encrypted tarball.
    """
    if not input_file.exists():
        print(f"Error: File '{input_file}' not found.")
        raise typer.Exit(code=1)

    print(f"Encrypting: {input_file}")

    try:
        tarball_path, encryption_key = CryptoUtils.encrypt_and_package(
            input_file, output_name
        )

        print(f"\n✓ Encryption successful!")
        print(f"✓ Output: {tarball_path}")
        print(f"✓ Encryption Key: {encryption_key}")
        print(f"\n⚠ Keep the encryption key safe - you'll need it to decrypt!")

    except Exception as e:
        print(f"Error during encryption: {e}")
        raise typer.Exit(code=1)


@app.command()
def decrypt(
    encrypted_tarball: Path = typer.Argument(
        ..., help="Path to the encrypted tarball file."
    ),
    decryption_key: str = typer.Argument(
        ..., help="Decryption key from encryption output."
    ),
    output_file: Path = typer.Option(
        Path("decrypted_output"), "--output", "-o", help="Output file path."
    ),
):
    """
    Decrypt and extract an encrypted tarball.

    This tool decrypts files created with the encrypt command or the --upload-db option.
    """
    if not encrypted_tarball.exists():
        print(f"Error: File '{encrypted_tarball}' not found.")
        raise typer.Exit(code=1)

    print(f"Extracting and decrypting: {encrypted_tarball}")

    try:
        CryptoUtils.decrypt_and_extract(encrypted_tarball, decryption_key, output_file)

        print(f"✓ Decrypted successfully!")
        print(f"✓ Output saved to: {output_file}")

    except Exception as e:
        print(f"Error during decryption: {e}")
        print("\nPossible causes:")
        print("  - Invalid decryption key")
        print("  - Corrupted encrypted file")
        print("  - File was not encrypted with this tool")
        raise typer.Exit(code=1)

    print("\nDone!")


if __name__ == "__main__":
    app()
