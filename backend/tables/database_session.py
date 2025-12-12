import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database connection settings (configure via environment variables)
DB_NAME = os.environ.get('DB_NAME', 'yacs')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_PASS = os.environ.get('DB_PASS', '')

# Connection pool tuning (tunable via env vars)
# pool_size: number of persistent connections in the pool
# max_overflow: additional connections beyond the pool_size (temporary)
# pool_timeout: seconds to wait for a connection from the pool before raising
# pool_recycle: number of seconds after which a connection is recycled
POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', '5'))
MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', '10'))
POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', '30'))
POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', '1800'))  # 30 minutes

# Construct the DB URL (supports password possibly empty)
if DB_PASS:
    DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DB_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create the engine with a tuned pool. pool_pre_ping helps with stale connections.
engine = create_engine(
    DB_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    future=False,
)

# Session factory: do not expire objects on commit to reduce unexpected refreshes
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

if __name__ == "__main__":
    import time
    import sys

    # quick connection check
    is_online = False

    for i in range(5):
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            is_online = True
            break
        except Exception as err:
            print(f"DB connection attempt {i+1} failed: {err}", file=sys.stderr)
        time.sleep(1)

    if not is_online:
        raise Exception("Database not connected")