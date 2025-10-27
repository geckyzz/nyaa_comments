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
    Compress and encrypt a file.

    Generates a random encryption key and outputs an encrypted file (.gz.enc).
    """
    if not input_file.exists():
        print(f"Error: File '{input_file}' not found.")
        raise typer.Exit(code=1)

    print(f"Encrypting: {input_file}")

    try:
        encrypted_path, encryption_key = CryptoUtils.encrypt_and_package(
            input_file, output_name
        )

        print("\n✓ Encryption successful!")
        print(f"✓ Output: {encrypted_path}")
        print(f"✓ Encryption Key: {encryption_key}")
        print("\n⚠ Keep the encryption key safe - you'll need it to decrypt!")

    except Exception as e:
        print(f"Error during encryption: {e}")
        raise typer.Exit(code=1)


@app.command()
def decrypt(
    encrypted_file: Path = typer.Argument(
        ..., help="Path to the encrypted file (.gz.enc)."
    ),
    decryption_key: str = typer.Argument(
        ..., help="Decryption key from encryption output."
    ),
    output_file: Path = typer.Option(
        Path("decrypted_output"), "--output", "-o", help="Output file path."
    ),
):
    """
    Decrypt and decompress an encrypted file.

    This tool decrypts files created with the encrypt command or the
    --upload-db option.
    """
    if not encrypted_file.exists():
        print(f"Error: File '{encrypted_file}' not found.")
        raise typer.Exit(code=1)

    print(f"Decrypting and decompressing: {encrypted_file}")

    try:
        CryptoUtils.decrypt_and_extract(encrypted_file, decryption_key, output_file)

        print("✓ Decrypted successfully!")
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
