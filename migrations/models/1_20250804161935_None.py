from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "jobs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "celery_task_id" VARCHAR(255) NOT NULL UNIQUE,
    "model" VARCHAR(255) NOT NULL,
    "prompt" TEXT NOT NULL,
    "num_outputs" INT NOT NULL  DEFAULT 1,
    "seed" INT,
    "output_format" VARCHAR(50),
    "status" VARCHAR(10) NOT NULL  DEFAULT 'pending',
    "media_url" TEXT,
    "s3_key" TEXT,
    "error_message" TEXT,
    "retry_count" INT NOT NULL  DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "started_at" TIMESTAMPTZ,
    "completed_at" TIMESTAMPTZ
);
COMMENT ON COLUMN "jobs"."status" IS 'PENDING: pending\nPROCESSING: processing\nCOMPLETED: completed\nFAILED: failed\nRETRY: retry';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
