# === schemas/message.py ===

# from pydantic import BaseModel, Field, model_validator
# from typing import Optional
# from uuid import UUID
# from datetime import datetime
#
#
# class MessageOut(BaseModel):
#     """
#     Schema representing a message in a chat.
#
#     Includes basic information such as message ID, sender, content, and timestamp.
#     Can represent both text and media messages.
#     """
#     id: int = Field(..., description="Unique identifier of the message")
#     chat_id: int = Field(..., description="ID of the chat the message belongs to")
#     sender_sub: str = Field(..., description="Cognito 'sub' of the user who sent the message")
#     content: Optional[str] = Field(None, description="Message text content (optional for media-only messages)")
#     media_url: Optional[str] = Field(None, description="URL to the media file, if the message includes one")
#     media_id: Optional[UUID] = Field(None, description="UUID of the media file stored in external service")
#     sent_at: datetime = Field(..., description="Timestamp when the message was created (UTC)")
#
#     class Config:
#         from_attributes = True
#
#
# class MessageTextIn(BaseModel):
#     chat_id: int = Field(..., description="ID of the chat where the message is sent")
#     content: str = Field(..., min_length=1, description="Text content of the message (must be non-empty)")
#
#
# class MessageMediaIn(BaseModel):
#     chat_id: int = Field(..., description="ID of the chat where the media message is sent")
#     sender_sub: str = Field(..., description="Cognito 'sub' of the user who sends the message")
