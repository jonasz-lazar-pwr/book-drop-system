# === routes/chat.py ===

# """
# Chat endpoints module.
#
# This module provides endpoints for managing user chats:
# - Retrieving all chats for the authenticated user.
# - Creating a new chat with another user if it doesn't already exist.
# """
#
# import json
# from fastapi import APIRouter, Depends, HTTPException, Header
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from api.db.deps import get_db
# from api.models.chat import Chat
# from api.models.user import User
# from api.schemas.chat import ChatListItem, ChatParticipant, ChatCreate
#
# router = APIRouter()
#
#
# @router.get(
#     "/",
#     response_model=list[ChatListItem],
#     summary="Get user chats",
#     description="Returns all chats for the authenticated user, excluding full user data.",
#     responses={
#         200: {"description": "List of user chats"},
#         400: {"description": "Invalid token payload"},
#         422: {"description": "Missing X-User-Payload header"},
#     }
# )
# async def get_user_chats(
#     x_user_payload: str = Header(..., alias="X-User-Payload"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Retrieve all chats for the authenticated user.
#
#     For each chat, it includes minimal chat information and basic details of the other participant.
#
#     Args:
#         x_user_payload (str): JWT payload (JSON string) from the gateway-provided header.
#         db (AsyncSession): Dependency-injected SQLAlchemy async session.
#
#     Returns:
#         list[ChatListItem]: List of user's chats with simplified participant info.
#
#     Raises:
#         HTTPException: If token is missing or malformed, or sub is not present.
#     """
#     try:
#         payload = json.loads(x_user_payload)
#         current_user_sub = payload.get("sub")
#     except (json.JSONDecodeError, AttributeError):
#         raise HTTPException(status_code=400, detail="Invalid X-User-Payload header")
#
#     if not current_user_sub:
#         raise HTTPException(status_code=400, detail="Missing 'sub' in token payload")
#
#     # Retrieve all chats where current user is a participant
#     result = await db.execute(
#         select(Chat).where(
#             (Chat.user1_sub == current_user_sub) | (Chat.user2_sub == current_user_sub)
#         )
#     )
#     chats = result.scalars().all()
#     chat_items = []
#
#     # For each chat, fetch the other participant's basic details
#     for chat in chats:
#         other_sub = chat.user2_sub if chat.user1_sub == current_user_sub else chat.user1_sub
#         user_result = await db.execute(select(User).where(User.sub == other_sub))
#         other_user = user_result.scalar_one_or_none()
#
#         if other_user:
#             chat_items.append(ChatListItem(
#                 id=chat.id,
#                 participant=ChatParticipant(
#                     first_name=other_user.first_name,
#                     last_name=other_user.last_name
#                 )
#             ))
#
#     return chat_items
#
#
# @router.post(
#     "/",
#     response_model=ChatListItem,
#     summary="Create a new chat with another user",
#     description="Creates a new one-on-one chat unless it already exists. Returns chat ID and basic info about the other participant.",
#     responses={
#         200: {"description": "Chat created successfully"},
#         400: {"description": "Invalid token payload or attempting to chat with self"},
#         404: {"description": "Target user does not exist"},
#         409: {"description": "Chat between users already exists"},
#     }
# )
# async def create_chat(
#     chat_in: ChatCreate,
#     x_user_payload: str = Header(..., alias="X-User-Payload"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Create a new one-on-one chat between the authenticated user and a target user.
#
#     Prevents self-chat and duplicate conversations. Returns minimal information about the new chat.
#
#     Args:
#         chat_in (ChatCreate): Request body with the target user's `sub`.
#         x_user_payload (str): JWT payload header containing the current user's `sub`.
#         db (AsyncSession): Injected database session.
#
#     Returns:
#         ChatListItem: Object with the new chat ID and basic data of the other participant.
#
#     Raises:
#         HTTPException:
#             - 400 if the token is malformed or self-chat is attempted.
#             - 404 if the target user does not exist.
#             - 409 if the chat already exists.
#     """
#     try:
#         payload = json.loads(x_user_payload)
#         current_user_sub = payload.get("sub")
#     except (json.JSONDecodeError, AttributeError):
#         raise HTTPException(status_code=400, detail="Invalid X-User-Payload header")
#
#     if not current_user_sub:
#         raise HTTPException(status_code=400, detail="Missing 'sub' in token payload")
#
#     if current_user_sub == chat_in.target_user_sub:
#         raise HTTPException(status_code=400, detail="Cannot create a chat with yourself")
#
#     target_result = await db.execute(select(User).where(User.sub == chat_in.target_user_sub))
#     target_user = target_result.scalar_one_or_none()
#     if not target_user:
#         raise HTTPException(status_code=404, detail="Target user not found")
#
#     existing_chat_result = await db.execute(
#         select(Chat).where(
#             ((Chat.user1_sub == current_user_sub) & (Chat.user2_sub == chat_in.target_user_sub)) |
#             ((Chat.user1_sub == chat_in.target_user_sub) & (Chat.user2_sub == current_user_sub))
#         )
#     )
#     existing_chat = existing_chat_result.scalar_one_or_none()
#     if existing_chat:
#         raise HTTPException(status_code=409, detail="Chat already exists")
#
#     new_chat = Chat(user1_sub=current_user_sub, user2_sub=chat_in.target_user_sub)
#     db.add(new_chat)
#     await db.commit()
#     await db.refresh(new_chat)
#
#     # Load the user1 and user2 relationships
#     await db.refresh(new_chat, attribute_names=["user1", "user2"])
#
#     # Determine the other user based on the current user's sub
#     other_user = new_chat.user2 if new_chat.user1_sub == current_user_sub else new_chat.user1
#
#     return ChatListItem(
#         id=new_chat.id,
#         participant=ChatParticipant(
#             first_name=other_user.first_name,
#             last_name=other_user.last_name
#         )
#     )
