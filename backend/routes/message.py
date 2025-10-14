# === routes/message.py ===

# import json
# from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from api.db.deps import get_db
# from api.models.message import Message
# from api.models.chat import Chat
# from api.schemas.message import MessageOut, MessageTextIn
# from api.services.notification import send_notification_for_message
# from api.services.media import upload_media_to_s3
# from uuid import UUID
#
#
# async def get_validated_chat_and_user(
#     db: AsyncSession,
#     chat_id: int,
#     x_user_payload: str
# ) -> tuple[str, Chat]:
#     """
#     Validates the token, checks if the chat exists, and ensures the user is a participant.
#
#     Args:
#         db (AsyncSession): The database session.
#         chat_id (int): The ID of the chat to validate.
#         x_user_payload (str): JSON string from the X-User-Payload header.
#
#     Returns:
#         Tuple[str, Chat]: (sender_sub, Chat object)
#
#     Raises:
#         HTTPException:
#             - 400: Invalid token payload.
#             - 403: User is not a participant of the chat.
#             - 404: Chat not found.
#     """
#     try:
#         payload = json.loads(x_user_payload)
#         sender_sub = payload.get("sub")
#     except (json.JSONDecodeError, AttributeError):
#         raise HTTPException(status_code=400, detail="Invalid X-User-Payload header")
#
#     if not sender_sub:
#         raise HTTPException(status_code=400, detail="Missing 'sub' in token payload")
#
#     # Check if chat exists
#     chat_result = await db.execute(select(Chat).where(Chat.id == chat_id))
#     chat = chat_result.scalar_one_or_none()
#     if chat is None:
#         raise HTTPException(status_code=404, detail="Chat not found")
#
#     # Check if sender is a participant
#     if sender_sub not in [chat.user1_sub, chat.user2_sub]:
#         raise HTTPException(status_code=403, detail="You are not a participant of this chat")
#
#     return sender_sub, chat
#
#
# # Create a router instance to handle message-related routes
# router = APIRouter()
#
# @router.post(
#     "/text/",
#     response_model=MessageOut,
#     summary="Create a new text message",
#     description=(
#         "Creates a new text-only message in the specified chat. "
#         "The sender is automatically identified based on the JWT token provided "
#         "in the `X-User-Payload` header. Only participants of the chat are allowed "
#         "to send messages. This endpoint does not allow media attachments."
#     ),
#     responses={
#         200: {"description": "Text message created successfully"},
#         400: {"description": "Invalid input data or missing token payload"},
#         403: {"description": "The user is not a participant of the specified chat"},
#         404: {"description": "Chat not found"},
#         500: {"description": "Unexpected server error (e.g., notification failure)"}
#     },
#     tags=["Messages"]
# )
# async def create_text_message(
#     message_in: MessageTextIn,
#     x_user_payload: str = Header(..., alias="X-User-Payload"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Create a new text-only message in the specified chat.
#
#     This endpoint allows an authenticated user to post a text message
#     to an existing chat. The sender is identified automatically from
#     the `X-User-Payload` header (JWT token payload) and **must be a participant
#     of the chat**.
#
#     Process:
#     1. Extract the `sub` (Cognito user ID) from the token payload.
#     2. Validate that the message `content` is non-empty.
#     3. Verify that the chat with the given `chat_id` exists.
#     4. Ensure the sender is a participant of the chat.
#     5. Insert the message into the database.
#     6. Trigger a notification to inform recipients about the new message.
#
#     Args:
#         message_in (MessageTextIn): The input payload containing `chat_id` and `content`.
#         x_user_payload (str): JSON string from the `X-User-Payload` header (JWT payload, must include `sub`).
#         db (AsyncSession): SQLAlchemy async session (dependency injection).
#
#     Returns:
#         MessageOut: The newly created message, including ID, sender, content, and timestamp.
#
#     Raises:
#         HTTPException:
#             - 400: If the token payload is invalid or `content` is empty.
#             - 403: If the sender is not a participant of the specified chat.
#             - 404: If the specified chat does not exist.
#             - 500: If sending the notification fails unexpectedly.
#     """
#     sender_sub, chat = await get_validated_chat_and_user(db, message_in.chat_id, x_user_payload)
#
#     # Create the message
#     message = Message(
#         chat_id=message_in.chat_id,
#         sender_sub=sender_sub,
#         content=message_in.content,
#         media_url=None,
#         media_id=None
#     )
#
#     db.add(message)
#     await db.commit()
#     await db.refresh(message)
#
#     try:
#         await send_notification_for_message(
#             db=db,
#             sender_sub=sender_sub,
#             message_content=message_in.content,
#             has_media=False
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")
#
#     return message
#
#
# @router.post(
#     "/media/",
#     response_model=MessageOut,
#     summary="Create a new media message",
#     description=(
#         "Creates a new message that contains ONLY media (no text allowed). "
#         "The sender is identified based on the JWT token provided in the `X-User-Payload` header."
#     ),
#     responses={
#         200: {"description": "Media message created successfully"},
#         400: {"description": "Invalid input data (e.g., missing media, invalid file type)"},
#         403: {"description": "User is not a participant of the chat"},
#         404: {"description": "Chat not found"},
#         500: {"description": "Unexpected server error"}
#     },
#     tags=["Messages"]
# )
# async def create_media_message(
#     chat_id: int = Form(...),
#     media_file: UploadFile = File(...),
#     x_user_payload: str = Header(..., alias="X-User-Payload"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     This endpoint allows an authenticated user to upload an image and post it as a message.
#     The sender is extracted from the `X-User-Payload` header (JWT payload).
#
#     Args:
#         chat_id (int): ID of the chat where the media is being sent.
#         media_file (UploadFile): The uploaded media file (must be an image).
#         x_user_payload (str): JSON string from the `X-User-Payload` header (JWT payload).
#         db (AsyncSession): SQLAlchemy async session.
#
#     Returns:
#         MessageOut: The newly created media message with metadata.
#
#     Raises:
#         HTTPException:
#             - 400: Invalid input (e.g., no media, bad type) or failed upload.
#             - 403: User is not a participant of the chat.
#             - 404: Chat not found.
#             - 500: Notification or upload error.
#     """
#     sender_sub, chat = await get_validated_chat_and_user(db, chat_id, x_user_payload)
#
#     media_metadata = await upload_media_to_s3(media_file)
#
#     # Create the message
#     message = Message(
#         chat_id=chat_id,
#         sender_sub=sender_sub,
#         content=None,
#         media_url=media_metadata["url"],
#         media_id=UUID(media_metadata["id"])
#     )
#
#     db.add(message)
#     await db.commit()
#     await db.refresh(message)
#
#     try:
#         await send_notification_for_message(
#             db=db,
#             sender_sub=sender_sub,
#             message_content=None,
#             has_media=True
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")
#
#     return message
#
#
# @router.get(
#     "/{chat_id}/",
#     response_model=list[MessageOut],
#     summary="Get messages from a chat",
#     description=(
#         "Retrieves all messages from a given chat, ordered by time sent. "
#         "Requires the authenticated user to be a participant of the chat (validated via X-User-Payload header)."
#     ),
#     responses={
#         200: {"description": "List of messages in the chat"},
#         400: {"description": "Invalid token payload"},
#         403: {"description": "User is not a participant of the chat"},
#         404: {"description": "Chat not found"},
#         422: {"description": "Missing X-User-Payload header"},
#     }
# )
# async def get_chat_messages(
#     chat_id: int,
#     x_user_payload: str = Header(..., alias="X-User-Payload"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Retrieve all messages from a specific chat for the authenticated user.
#
#     Ensures that the requesting user is a participant of the chat before returning messages.
#
#     Args:
#         chat_id (int): ID of the chat whose messages are to be retrieved.
#         x_user_payload (str): JSON string from the `X-User-Payload` header (must include `sub`).
#         db (AsyncSession): SQLAlchemy async session.
#
#     Returns:
#         list[MessageOut]: A list of all messages in the specified chat, ordered by timestamp.
#
#     Raises:
#         HTTPException:
#             - 400: Invalid token payload.
#             - 403: User is not a participant of the chat.
#             - 404: Chat not found.
#             - 422: Missing X-User-Payload header.
#     """
#     # Parse the token to extract the user's sub
#     try:
#         payload = json.loads(x_user_payload)
#         current_user_sub = payload.get("sub")
#     except (json.JSONDecodeError, AttributeError):
#         raise HTTPException(status_code=400, detail="Invalid X-User-Payload header")
#
#     if not current_user_sub:
#         raise HTTPException(status_code=400, detail="Missing 'sub' in token payload")
#
#     # Check if the chat exists
#     result = await db.execute(select(Chat).where(Chat.id == chat_id))
#     chat = result.scalar_one_or_none()
#     if not chat:
#         raise HTTPException(status_code=404, detail="Chat not found")
#
#     # Check if the user is a participant
#     if current_user_sub not in [chat.user1_sub, chat.user2_sub]:
#         raise HTTPException(status_code=403, detail="You are not a participant of this chat")
#
#     # Retrieve all messages, ordered by sent_at
#     result = await db.execute(
#         select(Message).where(Message.chat_id == chat_id).order_by(Message.sent_at)
#     )
#     return result.scalars().all()
