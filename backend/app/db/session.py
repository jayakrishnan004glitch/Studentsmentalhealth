from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def make_engine(database_url: str) -> AsyncEngine:
    # statement_cache_size=0: required behind Supabase's pooler in transaction
    # mode (PgBouncer/Supavisor), which does not support prepared statements.
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
