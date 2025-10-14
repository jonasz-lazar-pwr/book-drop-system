# api/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.middleware import add_middleware
from routes import message, chat, user


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Define the startup and shutdown logic for the BookDrop API.

    Args:
        _app (FastAPI): The FastAPI application instance.

    Yields:
        None
    """
    print("Starting up BookDrop API...")
    yield
    print("Shutting down BookDrop API...")


# Initialize the FastAPI application
app = FastAPI(
    lifespan=lifespan,
    title="BookDrop API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Apply global middleware (e.g., CORS)
add_middleware(app)

@app.get(
    "/health",
    summary="Health check",
    description="Basic health check endpoint",
    tags=["Health"]
)
def health_check():
    return {"status": "ok"}

# Mount routers for different parts of the API
# app.include_router(message.router, prefix="/messages")
# app.include_router(chat.router, prefix="/chats")
# app.include_router(user.router, prefix="/users")