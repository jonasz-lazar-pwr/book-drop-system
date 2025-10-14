# === routes/user.py ===

# """
# Routes for user-related operations.
#
# This module provides endpoints to:
# - search users by name (first name or last name, case-insensitive),
# - register a new user after authentication via Cognito.
#
# Endpoints:
# - POST /users/register
# - GET /users/search
# """
#
# from fastapi import APIRouter, status, Depends, Response, Query, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, or_, exists
# from api.db.deps import get_db
# from api.models import User, Chat
# from api.schemas.user import UserSearchOut, UserRegisterOut
# from fastapi import Header
# import json
#
# # Create a router instance for user-related routes
# router = APIRouter()
#
#
# @router.post(
#     "/register/",
#     response_model=UserRegisterOut,
#     status_code=201,
#     summary="Register a new user",
#     description=(
#         "Registers a new user using attributes from the JWT payload passed via the X-User-Payload header. "
#         "If the user already exists, returns 204 No Content."
#     ),
#     responses={
#         201: {"description": "User created successfully"},
#         204: {"description": "User already exists"},
#         400: {"description": "Missing required user attributes in token or invalid payload"},
#         422: {"description": "Missing X-User-Payload header"},
#     }
# )
# async def register_user(
#     x_user_payload: str = Header(..., alias="X-User-Payload"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Register a new user if they are not already registered.
#
#     This endpoint registers a new user based on information extracted from the
#     X-User-Payload header. The payload is expected to be a JSON string containing
#     the following required fields:
#     - sub: Unique Cognito user identifier.
#     - email: User's email address.
#     - given_name: User's first name.
#     - family_name: User's last name.
#
#     If a user with the provided 'sub' already exists, the endpoint returns 204 No Content.
#     If any required attribute is missing or the payload is invalid, an appropriate error
#     response is returned.
#
#     Args:
#         x_user_payload (str): A JSON string provided via the X-User-Payload header,
#             containing user identity attributes from the validated token.
#         db (AsyncSession): The asynchronous database session (injected).
#
#     Returns:
#         UserRegisterOut: A success message when the user is created.
#
#     Raises:
#         HTTPException: 400 if the payload is invalid or required fields are missing.
#         HTTPException: 422 if the X-User-Payload header is missing.
#     """
#     # Attempt to parse the JSON payload from the header.
#     try:
#         payload = json.loads(x_user_payload)
#     except json.JSONDecodeError:
#         raise HTTPException(status_code=400, detail="Invalid JSON in X-User-Payload header")
#
#     # Extract required user attributes from the payload.
#     sub = payload.get("sub")
#     email = payload.get("email")
#     first_name = payload.get("given_name")
#     last_name = payload.get("family_name")
#
#     # Validate that all required fields are present.
#     if not sub or not email or not first_name or not last_name:
#         raise HTTPException(status_code=400, detail="Missing required user attributes in token payload")
#
#     # Check if a user with the same 'sub' already exists in the database.
#     result = await db.execute(select(User).where(User.sub == sub))
#     user = result.scalar_one_or_none()
#
#     if user:
#         # User already exists; return 204 No Content.
#         return Response(status_code=status.HTTP_204_NO_CONTENT)
#
#     # Create and persist the new user in the database.
#     new_user = User(
#         sub=sub,
#         email=email,
#         first_name=first_name,
#         last_name=last_name
#     )
#     db.add(new_user)
#     await db.commit()
#
#     return UserRegisterOut(message="User created successfully")
#
#
# @router.get(
#     "/search",
#     response_model=list[UserSearchOut],
#     summary="Search users by name (excluding self and existing chat partners)",
#     description=(
#         "Returns users whose first name or last name contains the given query string "
#         "(case-insensitive). Excludes the current authenticated user and users "
#         "who already have a chat with them."
#     ),
#     responses={
#         200: {"description": "List of matching users"},
#         400: {"description": "Invalid token payload"},
#         422: {"description": "Validation error (e.g., missing query param or header)"},
#     }
# )
# async def search_users(
#     query: str = Query(..., min_length=1),
#     x_user_payload: str = Header(..., alias="X-User-Payload"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Search for users by name, excluding the current user and existing chat partners.
#
#     This endpoint allows the authenticated user to search for other users by their
#     first or last name. The search is case-insensitive and filters out:
#     - the current authenticated user,
#     - users with whom a chat already exists.
#
#     Args:
#         query (str): The search query string (minimum length of 1 character).
#         x_user_payload (str): A JSON string containing the JWT payload, provided by the API gateway
#             via the X-User-Payload header. Must include the 'sub' field.
#         db (AsyncSession): The asynchronous database session (injected).
#
#     Returns:
#         list[UserSearchOut]: A list of users matching the search criteria.
#
#     Raises:
#         HTTPException: 400 if the token payload is invalid or missing required fields.
#         HTTPException: 422 if the X-User-Payload header is missing.
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
#     # Build the ORM query:
#     # 1. Match users whose first or last name contains the search query (case-insensitive).
#     # 2. Exclude the current user from the results.
#     # 3. Exclude users who are already in a chat with the current user.
#     stmt = (
#         select(User)
#         .where(
#             (User.first_name.ilike(f"%{query}%")) | (User.last_name.ilike(f"%{query}%")),
#             User.sub != current_user_sub,
#             ~exists().where(
#                 or_(
#                     (Chat.user1_sub == current_user_sub) & (Chat.user2_sub == User.sub),
#                     (Chat.user2_sub == current_user_sub) & (Chat.user1_sub == User.sub),
#                 )
#             )
#         )
#     )
#
#     result = await db.execute(stmt)
#     users = result.scalars().all()
#     return users