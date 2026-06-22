from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGODB_URL)

database = client[settings.DATABASE_NAME]


async def init_database() -> None:
    from app.repositories.favorite_repository import create_favorite_indexes
    from app.repositories.share_repository import create_share_indexes
    from app.repositories.user_repository import create_user_indexes
    from app.repositories.comment_repository import create_comment_indexes
    from app.repositories.rating_repository import create_rating_indexes

    await create_user_indexes()
    await create_favorite_indexes()
    await create_share_indexes()
    await create_comment_indexes()
    await create_rating_indexes()
