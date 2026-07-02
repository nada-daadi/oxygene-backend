from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import client, init_database
from app.core.cloudinary_client import init_cloudinary

# Routers
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.articles import router as articles_router
from app.routers.favorites import router as favorites_router
from app.routers.comments import router as comments_router
from app.routers.ratings import router as ratings_router
from app.routers.chatbot import router as chatbot_router
from app.routers.shares import router as shares_router
from app.routers.records import router as records_router
from app.ai.router import router as ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("🚀 Oxygène FM API Started")

    await init_database()
    init_cloudinary()

    yield

    client.close()

    print("❌ Oxygène FM API Stopped")


app = FastAPI(
    title="Oxygène FM API",
    description="Backend API for Oxygène FM 2.0",
    version="1.0.0",
    lifespan=lifespan
)

# CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers

app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    users_router,
    prefix="/api/users",
    tags=["Users"]
)

app.include_router(
    articles_router,
    prefix="/api/articles",
    tags=["Articles"]
)

app.include_router(
    favorites_router,
    prefix="/api/favorites",
    tags=["Favorites"]
)

app.include_router(
    comments_router,
    prefix="/api/comments",
    tags=["Comments"]
)

app.include_router(
    ratings_router,
    prefix="/api/ratings",
    tags=["Ratings"]
)

app.include_router(
    chatbot_router,
    prefix="/api/chatbot",
    tags=["Chatbot"]
)

app.include_router(
    shares_router,
    prefix="/api/shares",
    tags=["Shares"]
)

app.include_router(
    records_router,
    prefix="/api/records",
    tags=["Records"]
)

app.include_router(
    ai_router,
    prefix="/api/ai",
    tags=["AI"]
)


@app.get("/")
async def root():
    return {
        "project": "Oxygène FM 2.0",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }
