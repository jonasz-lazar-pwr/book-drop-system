# === models/chat.py ===

# """
# SQLAlchemy model for the Chat table.
#
# This model represents a conversation between two users.
# """
#
# from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func
# from sqlalchemy.orm import relationship
# from .base import Base
#
# class Chat(Base):
#     """
#     Chat model for storing conversations between two users.
#
#     Attributes:
#         id (int): Primary key (unique chat ID).
#         user1_sub (str): Cognito `sub` of the first user in the chat.
#         user2_sub (str): Cognito `sub` of the second user in the chat.
#         created_at (datetime): Timestamp when the chat was created (auto-generated).
#
#     Relationships:
#         user1 (User): Relationship to the first user (foreign key: user1_sub).
#         user2 (User): Relationship to the second user (foreign key: user2_sub).
#         messages (list): List of Message objects belonging to this chat.
#     """
#
#     __tablename__ = "chats"
#
#     id = Column(Integer, primary_key=True, index=True)
#     user1_sub = Column(String, ForeignKey("users.sub"), nullable=False)
#     user2_sub = Column(String, ForeignKey("users.sub"), nullable=False)
#     created_at = Column(DateTime, server_default=func.now())
#
#     user1 = relationship(
#         "User",
#         foreign_keys=lambda: [Chat.user1_sub],
#         back_populates="chats_as_user1"
#     )
#     user2 = relationship(
#         "User",
#         foreign_keys=lambda: [Chat.user2_sub],
#         back_populates="chats_as_user2"
#     )
#
#     messages = relationship(
#         "Message",
#         back_populates="chat",
#         cascade="all, delete"
#     )
