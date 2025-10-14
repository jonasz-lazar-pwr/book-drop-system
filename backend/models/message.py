# === models/message.py ===

# """
# SQLAlchemy model for the Message table.
#
# This model represents individual messages within a chat, supporting both
# text content and optional media attachments.
# """
#
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Text, func
# from sqlalchemy.orm import relationship
# from .base import Base
#
# class Message(Base):
#     """
#     Message model for storing chat messages.
#
#     Attributes:
#         id (int): Primary key (unique message ID).
#         chat_id (int): Foreign key referencing the chat this message belongs to.
#         sender_sub (str): Cognito `sub` of the user who sent the message.
#         content (str | None): Text content of the message (nullable).
#         media_url (str | None): URL of the attached media file (if any).
#         media_id (UUID | None): UUID of the associated media (stored in DynamoDB/S3).
#         sent_at (datetime): Timestamp when the message was sent (auto-generated).
#
#     Relationships:
#         chat (Chat): Relationship to the Chat model (parent chat).
#     """
#
#     __tablename__ = "messages"
#
#     id = Column(Integer, primary_key=True, index=True)
#     chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"))
#     sender_sub = Column(String, ForeignKey("users.sub"), nullable=False)
#     content = Column(Text, nullable=True)
#     media_url = Column(String, nullable=True)
#     media_id = Column(UUID(as_uuid=True), nullable=True)
#     sent_at = Column(DateTime, server_default=func.now())
#
#     chat = relationship(
#         "Chat",
#         back_populates="messages"
#     )
