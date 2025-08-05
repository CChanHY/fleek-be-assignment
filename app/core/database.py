from tortoise import Tortoise
from app.core.config import settings


TORTOISE_ORM = {
    "connections": {"default": settings.database_url},
    "apps": {
        "models": {
            "models": ["app.models.job", "aerich.models"],
            "default_connection": "default",
        },
    },
}


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)


async def close_db():
    await Tortoise.close_connections()