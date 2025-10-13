"""Comment-related data models."""

from typing import Optional

from pydantic import BaseModel, HttpUrl


class CommentUser(BaseModel):
    """Represents the user who made a comment.

    :ivar username: The username of the commenter.
    :ivar image: Optional URL to the user's avatar image.
    """

    username: str
    image: Optional[HttpUrl] = None


class Comment(BaseModel):
    """Represents a single comment on a torrent.

    :ivar id: Unique identifier for the comment.
    :ivar pos: Position/order of the comment on the page.
    :ivar timestamp: Unix timestamp when the comment was posted.
    :ivar user: The user who posted the comment.
    :ivar message: The content of the comment.
    """

    id: int
    pos: int
    timestamp: int
    user: CommentUser
    message: str
