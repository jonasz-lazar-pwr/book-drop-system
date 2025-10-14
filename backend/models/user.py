# === models/user.py ===

# """
# SQLAlchemy model for the User table.
#
# This model represents a user in the system, typically linked to AWS Cognito users.
# """
#
# from sqlalchemy import Column, String
# from sqlalchemy.orm import relationship
# from .base import Base
#
# class User(Base):
#     """
#     User model for storing user profile data.
#
#     Attributes:
#         sub (str): The Cognito `sub` identifier (primary key).
#         email (str): The user's unique email address.
#         first_name (str): The user's first name.
#         last_name (str): The user's last name.
#         chats_as_user1 (list): List of Chat objects where the user is user1.
#         chats_as_user2 (list): List of Chat objects where the user is user2.
#     """
#
#     __tablename__ = "users"
#
#     sub = Column(String, primary_key=True, index=True)
#     email = Column(String, unique=True, nullable=False)
#     first_name = Column(String, nullable=False)
#     last_name = Column(String, nullable=False)
#
#     chats_as_user1 = relationship(
#         "Chat",
#         back_populates="user1",
#         foreign_keys="Chat.user1_sub"
#     )
#     chats_as_user2 = relationship(
#         "Chat",
#         back_populates="user2",
#         foreign_keys="Chat.user2_sub"
#     )
