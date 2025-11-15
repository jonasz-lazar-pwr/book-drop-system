# api/main.py

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import auth, cart, catalog, checkout, librarian, seed
from core.middleware import add_middleware

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bookdrop")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup and shutdown logic for the BookDrop API."""
    logger.info("Starting up BookDrop API...")
    yield
    logger.info("Shutting down BookDrop API...")


# Initialize FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title="BookDrop API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Apply global middleware (e.g., CORS)
add_middleware(app)


@app.get(
    "/health",
    summary="Health check",
    description="Basic health check endpoint",
    tags=["Health"],
)
def health_check():
    return {"status": "ok"}


# Mount routers
app.include_router(auth.router, prefix="/auth")
app.include_router(seed.router, prefix="/api/seed")
app.include_router(catalog.router, prefix="/api/catalog")
app.include_router(cart.router, prefix="/api/cart")
app.include_router(checkout.router, prefix="/api/checkout")
app.include_router(librarian.router, prefix="/api/librarian")
