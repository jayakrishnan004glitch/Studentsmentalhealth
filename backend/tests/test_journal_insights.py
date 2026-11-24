"""Pure insight calculations (no database)."""

from datetime import UTC, date, datetime, timedelta

from app.services.journal import (
    DayRow,
    build_insights,
    local_day_start_utc,
    local_today,
    streak,
)

TODAY = date(2026, 11, 20)


def d(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)


def test_streak_counts_back_from_today() -> None:
    assert streak([d(0), d(1), d(2), d(4)], TODAY) == 3


def test_streak_still_alive_if_not_logged_yet_today() -> None:
    assert streak([d(1), d(2)], TODAY) == 2


def test_streak_broken() -> None:
    assert streak([d(2), d(3)], TODAY) == 0
    assert streak([], TODAY) == 0


def test_local_day_uses_offset() -> None:
    # 20:00 UTC on the 19th is already the 20th in India (+05:30).
    now = datetime(2026, 11, 19, 20, 0, tzinfo=UTC)
    assert local_today(now, 330) == date(2026, 11, 20)
    assert local_today(now, 0) == date(2026, 11, 19)
    assert local_day_start_utc(date(2026, 11, 20), 330) == datetime(
        2026, 11, 19, 18, 30, tzinfo=UTC
    )


def test_build_insights_fills_gaps_and_weights_averages() -> None:
    rows = [
        # two entries yesterday: moods 2 + 4, sleep logged once (6h)
        DayRow(day=d(1), entries=2, mood_sum=6, sleep_sum=6, sleep_entries=1),
        DayRow(day=d(0), entries=1, mood_sum=5, sleep_sum=8, sleep_entries=1),
    ]
    out = build_insights(
        today=TODAY,
        range_days=7,
        rows=rows,
        logged_days=[d(0), d(1)],
        tag_counts=[("family", 1), ("exams", 3), ("sleep", 1)],
    )
    assert [x.date for x in out.days] == [d(i) for i in range(6, -1, -1)]
    assert out.days[0].entries == 0 and out.days[0].mood_avg is None
    assert out.days[-2].mood_avg == 3.0
    assert out.days[-2].sleep_avg == 6.0
    assert out.entries == 3
    assert out.mood_avg == round(11 / 3, 2)  # per entry, not per day
    assert out.sleep_avg == 7.0
    assert out.streak_days == 2
    assert [(t.tag, t.count) for t in out.top_tags] == [("exams", 3), ("family", 1), ("sleep", 1)]


def test_build_insights_empty() -> None:
    out = build_insights(today=TODAY, range_days=30, rows=[], logged_days=[], tag_counts=[])
    assert len(out.days) == 30
    assert (out.entries, out.mood_avg, out.sleep_avg, out.streak_days) == (0, None, None, 0)
