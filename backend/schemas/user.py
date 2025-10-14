# === schemas/user.py ===

# from pydantic import BaseModel, Field
#
#
# class UserRegisterOut(BaseModel):
#     """Response confirming user registration."""
#     message: str = Field(..., description="Confirmation message")
#
#
# class UserSearchOut(BaseModel):
#     """Minimal user data returned in user search results."""
#     sub: str = Field(..., description="Cognito sub of the user")
#     first_name: str = Field(..., description="First name of the user")
#     last_name: str = Field(..., description="Last name of the user")
#
#     class Config:
#         from_attributes = True
