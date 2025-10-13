#!/usr/bin/env python3
"""Utility script to decrypt and extract encrypted database backups from Catbox Litterbox."""

import tarfile
from pathlib import Path

import typer
from cryptography.fernet import Fernet


def decrypt_and_extract(
    encrypted_tarball: str = typer.Argument(
        ..., help="Path to the encrypted tarball file."
    ),
    decryption_key: str = typer.Argument(
        ..., help="Decryption key from Discord notification."
    ),
    output_file: str = typer.Option(
        "database.json", "--output", "-o", help="Output file path."
    ),
):
    """
    Decrypt and extract an encrypted database backup.

    This tool decrypts database backups created with the --upload-db option.
    """
    tarball_path = Path(encrypted_tarball)

    if not tarball_path.exists():
        print(f"Error: File '{encrypted_tarball}' not found.")
        raise typer.Exit(code=1)

    print(f"Extracting tarball: {encrypted_tarball}")

    # Extract the tarball
    try:
        with tarfile.open(tarball_path, "r:gz") as tar:
            # Get the encrypted file name from the tarball
            members = tar.getmembers()
            if not members:
                print("Error: Tarball is empty.")
                raise typer.Exit(code=1)

            encrypted_file = members[0].name
            tar.extract(encrypted_file)
            print(f"✓ Extracted: {encrypted_file}")
    except Exception as e:
        print(f"Error extracting tarball: {e}")
        raise typer.Exit(code=1)

    # Decrypt the file
    print(f"Decrypting with provided key...")
    try:
        key = decryption_key.encode("utf-8")
        fernet = Fernet(key)

        with open(encrypted_file, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = fernet.decrypt(encrypted_data)

        with open(output_file, "wb") as f:
            f.write(decrypted_data)

        print(f"✓ Decrypted successfully!")
        print(f"✓ Output saved to: {output_file}")

        # Clean up extracted encrypted file
        Path(encrypted_file).unlink()
        print(f"✓ Cleaned up temporary file: {encrypted_file}")

    except Exception as e:
        print(f"Error during decryption: {e}")
        print("\nPossible causes:")
        print("  - Invalid decryption key")
        print("  - Corrupted encrypted file")
        print("  - File was not encrypted with this tool")

        # Clean up if exists
        if Path(encrypted_file).exists():
            Path(encrypted_file).unlink()

        raise typer.Exit(code=1)

    print("\nDone!")


if __name__ == "__main__":
    typer.run(decrypt_and_extract)
