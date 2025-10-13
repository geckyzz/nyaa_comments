"""Database manager for handling comment storage."""

import json
from pathlib import Path

from classes.comment_models import Comment


class DatabaseManager:
    """Handle reading from and writing to the JSON database.

    :ivar db_path: Path to the JSON database file.
    :ivar data: In-memory database containing comments keyed by Nyaa ID.
    """

    def __init__(self, db_path: Path = Path("database.json")) -> None:
        """Initialize the database manager.

        :param db_path: Path to the JSON database file.
        :type db_path: Path
        """
        self.db_path = db_path
        self.data = self._load()

    def _load(self) -> dict[str, list[Comment]]:
        """Load the database from a file.

        :return: Dictionary mapping Nyaa IDs to lists of Comment objects.
        :rtype: dict[str, list[Comment]]
        """
        try:
            with open(self.db_path, "r") as f:
                raw_data = json.load(f)
                return {
                    k: [Comment.model_validate(c) for c in v]
                    for k, v in raw_data.items()
                }
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get_comments(self, nyaa_id: str) -> list[Comment]:
        """Retrieve comments for a specific Nyaa ID.

        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :return: List of Comment objects for the given torrent.
        :rtype: list[Comment]
        """
        return self.data.get(nyaa_id, [])

    def update_comments(self, nyaa_id: str, comments: list[Comment]) -> None:
        """Update the comments for a specific Nyaa ID.

        :param nyaa_id: The Nyaa torrent ID.
        :type nyaa_id: str
        :param comments: List of Comment objects to store.
        :type comments: list[Comment]
        """
        self.data[nyaa_id] = comments

    def save(self) -> None:
        """Save the current database state to the file."""
        with open(self.db_path, "w") as f:
            # Convert Pydantic models to dictionaries for JSON serialization
            serializable_data = {
                k: [c.model_dump(mode="json") for c in v] for k, v in self.data.items()
            }
            # Sort by nyaa_id (key) before saving
            sorted_data = dict(
                sorted(serializable_data.items(), key=lambda x: int(x[0]))
            )
            json.dump(sorted_data, f)
