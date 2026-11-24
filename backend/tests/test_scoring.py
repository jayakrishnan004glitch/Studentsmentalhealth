"""PHQ-9 / GAD-7 / DASS-21 scoring (pure functions)."""

import pytest

from ai.scoring import (
    DASS21_SUBSCALES,
    DEFINITIONS,
    Instrument,
    InvalidAnswers,
    score,
    suggests_support,
)


def phq9(total: int, item9: int = 0) -> list[int]:
    """9 answers summing to `total`, with item 9 set explicitly."""
    rest = total - item9
    answers = []
    for _ in range(8):
        v = min(3, rest)
        answers.append(v)
        rest -= v
    assert rest == 0
    return answers + [item9]


@pytest.mark.parametrize(
    ("total", "severity"),
    [
        (0, "minimal"),
        (4, "minimal"),
        (5, "mild"),
        (9, "mild"),
        (10, "moderate"),
        (14, "moderate"),
        (15, "moderately_severe"),
        (19, "moderately_severe"),
        (20, "severe"),
        (24, "severe"),
    ],
)
def test_phq9_bands(total: int, severity: str) -> None:
    r = score(Instrument.phq9, phq9(total))
    assert (r.total, r.severity, r.item9_flag) == (total, severity, False)


def test_phq9_item9_flags_regardless_of_total() -> None:
    r = score(Instrument.phq9, phq9(1, item9=1))
    assert r.severity == "minimal"
    assert r.item9_flag is True
    assert suggests_support(r) is True


@pytest.mark.parametrize(
    ("answers", "severity"),
    [
        ([0] * 7, "minimal"),
        ([1, 1, 1, 1, 0, 0, 0], "minimal"),
        ([1, 1, 1, 1, 1, 0, 0], "mild"),
        ([2, 2, 2, 2, 2, 0, 0], "moderate"),
        ([3, 3, 3, 2, 2, 1, 1], "severe"),
        ([3] * 7, "severe"),
    ],
)
def test_gad7_bands(answers: list[int], severity: str) -> None:
    r = score(Instrument.gad7, answers)
    assert r.severity == severity
    assert r.max_total == 21


def dass(depression: int = 0, anxiety: int = 0, stress: int = 0) -> list[int]:
    """21 answers giving the given RAW subscale sums."""
    answers = [0] * 21
    for code, raw in (("depression", depression), ("anxiety", anxiety), ("stress", stress)):
        for item in DASS21_SUBSCALES[code][1]:
            v = min(3, raw)
            answers[item - 1] = v
            raw -= v
        assert raw == 0
    return answers


def test_dass21_subscales_are_doubled_and_banded() -> None:
    r = score(Instrument.dass21, dass(depression=7, anxiety=4, stress=9))
    subs = {s.code: (s.score, s.severity) for s in r.subscales}
    assert subs == {
        "depression": (14, "moderate"),
        "anxiety": (8, "mild"),
        "stress": (18, "mild"),
    }
    assert r.severity == "moderate"
    assert r.severity_label == "Moderate (depression)"
    assert r.total == 40


@pytest.mark.parametrize(
    ("code", "raw", "severity"),
    [
        ("depression", 4, "normal"),  # 8
        ("depression", 5, "mild"),  # 10
        ("depression", 14, "extremely_severe"),  # 28
        ("anxiety", 3, "normal"),  # 6
        ("anxiety", 5, "moderate"),  # 10
        ("anxiety", 10, "extremely_severe"),  # 20
        ("stress", 7, "normal"),  # 14
        ("stress", 13, "severe"),  # 26
        ("stress", 17, "extremely_severe"),  # 34
    ],
)
def test_dass21_band_edges(code: str, raw: int, severity: str) -> None:
    r = score(Instrument.dass21, dass(**{code: raw}))
    assert {s.code: s.severity for s in r.subscales}[code] == severity


def test_dass21_all_normal() -> None:
    r = score(Instrument.dass21, [0] * 21)
    assert (r.severity, r.severity_label, r.level) == ("normal", "Normal", 0)
    assert suggests_support(r) is False


def test_subscales_cover_every_item_once() -> None:
    items = sorted(i for _, its, _ in DASS21_SUBSCALES.values() for i in its)
    assert items == list(range(1, 22))
    assert len(DEFINITIONS[Instrument.dass21].items) == 21


@pytest.mark.parametrize(
    ("instrument", "answers"),
    [
        (Instrument.phq9, [0] * 8),
        (Instrument.phq9, [0] * 10),
        (Instrument.gad7, [0] * 6 + [4]),
        (Instrument.gad7, [0] * 6 + [-1]),
        (Instrument.dass21, [0] * 20),
    ],
)
def test_invalid_answers(instrument: Instrument, answers: list[int]) -> None:
    with pytest.raises(InvalidAnswers):
        score(instrument, answers)


def test_suggests_support_in_high_bands() -> None:
    assert suggests_support(score(Instrument.phq9, phq9(15))) is True
    assert suggests_support(score(Instrument.phq9, phq9(14))) is False
    assert suggests_support(score(Instrument.gad7, [2, 2, 2, 2, 1, 1, 0])) is True
