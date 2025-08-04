from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "jobs" ADD COLUMN "media" JSONB;
        UPDATE "jobs" SET "media" = 
            CASE 
                WHEN "media_url" IS NOT NULL AND "s3_key" IS NOT NULL THEN
                    JSON_BUILD_ARRAY(JSON_BUILD_OBJECT('media_url', "media_url", 's3_key', "s3_key"))
                ELSE NULL
            END;
        ALTER TABLE "jobs" DROP COLUMN "media_url";
        ALTER TABLE "jobs" DROP COLUMN "s3_key";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "jobs" ADD COLUMN "media_url" TEXT;
        ALTER TABLE "jobs" ADD COLUMN "s3_key" TEXT;
        UPDATE "jobs" SET 
            "media_url" = ("media"->0->>'media_url'),
            "s3_key" = ("media"->0->>'s3_key')
        WHERE "media" IS NOT NULL AND jsonb_array_length("media") > 0;
        ALTER TABLE "jobs" DROP COLUMN "media";"""