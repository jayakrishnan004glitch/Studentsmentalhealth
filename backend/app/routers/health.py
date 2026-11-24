from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    db_status = "ok"
    try:
        async with request.app.state.sessionmaker() as session:
            await session.execute(text("select 1"))
    except Exception:  # noqa: BLE001 - health must never raise
        db_status = "unavailable"
    return {"status": "ok", "database": db_status}
