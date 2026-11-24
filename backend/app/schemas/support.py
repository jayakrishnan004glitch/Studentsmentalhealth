from typing import Literal

from pydantic import BaseModel

from ai.responses import Support


class SupportOut(BaseModel):
    """Shown by the app after a submission. "urgent" = show the crisis card."""

    level: Literal["urgent", "suggest"]
    title: str
    message: str

    @classmethod
    def of(cls, s: Support) -> "SupportOut":
        return cls(level=s.level, title=s.title, message=s.message)  # type: ignore[arg-type]
