# === schemas/chat.py ===

# from pydantic import BaseModel, Field
#
#
# class ChatParticipant(BaseModel):
#     """Basic information about the other participant in a chat.
#
#     This model is used to represent the person on the other side of a chat,
#     showing only their first and last name (used in `ChatListItem`).
#     """
#
#     first_name: str = Field(..., description="First name of the participant")
#     last_name: str = Field(..., description="Last name of the participant")
#
#     class Config:
#         from_attributes = True
#
#
# class ChatListItem(BaseModel):
#     """Schema representing a single chat entry in the user's chat list.
#
#     Returned by the GET /chats endpoint, this model includes the chat ID
#     and the basic data of the other participant.
#     """
#
#     id: int = Field(..., description="Unique ID of the chat")
#     participant: ChatParticipant = Field(..., description="Information about the other participant in the chat")
#
#     class Config:
#         from_attributes = True
#
#
# class ChatCreate(BaseModel):
#     """Schema used to create a new chat.
#
#     Sent in POST /chats request body to initiate a new conversation.
#     """
#
#     target_user_sub: str = Field(..., description="Cognito sub of the user to chat with")
