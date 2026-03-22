"""Application configuration — loaded from environment variables."""

import os


# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://scheduler_user:scheduler_pass@localhost:3307/scheduler_db",
)

# ── Redis ────────────────────────────────────────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")

# ── Lock Settings ────────────────────────────────────────────────────────────
LOCK_TTL_SECONDS: int = int(os.getenv("LOCK_TTL_SECONDS", "10"))
LOCK_RETRY_DELAY: float = float(os.getenv("LOCK_RETRY_DELAY", "0.2"))
LOCK_MAX_RETRIES: int = int(os.getenv("LOCK_MAX_RETRIES", "3"))
