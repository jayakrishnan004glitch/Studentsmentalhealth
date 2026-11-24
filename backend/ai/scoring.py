"""Questionnaire definitions and scoring: PHQ-9, GAD-7, DASS-21.

Framework-free (no FastAPI / DB) so it is easy to unit test.

These are SCREENING instruments. Results are shown to students as
"screening", never as a diagnosis.

Sources (all three are free to use without permission):
- PHQ-9 and GAD-7: Spitzer, Kroenke, Williams et al. (Pfizer; no permission
  required to reproduce, translate, display or distribute).
- DASS-21: Lovibond & Lovibond (1995), Manual for the Depression Anxiety
  Stress Scales; public domain. Subscale scores are multiplied by 2 so the
  DASS-42 severity bands apply.

TEAM: before the demo, check the band tables below against the official
manuals once more (brief §8).
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Instrument(StrEnum):
    phq9 = "phq9"
    gad7 = "gad7"
    dass21 = "dass21"


@dataclass(frozen=True)
class Band:
    code: str
    label: str
    min_score: int  # inclusive lower bound; the band runs up to the next band's min - 1


@dataclass(frozen=True)
class Definition:
    instrument: Instrument
    name: str
    short_name: str
    description: str
    stem: str
    options: tuple[str, ...]  # index = item score (0..3)
    items: tuple[str, ...]
    minutes: int


@dataclass(frozen=True)
class SubscaleScore:
    code: str
    label: str
    score: int
    severity: str
    severity_label: str
    level: int  # 0 = lowest band, higher = more severe


@dataclass(frozen=True)
class ScoreResult:
    instrument: Instrument
    total: int
    max_total: int
    severity: str
    severity_label: str
    level: int
    max_level: int
    subscales: tuple[SubscaleScore, ...] = field(default_factory=tuple)
    # PHQ-9 item 9 (thoughts of being better off dead / self-harm) > 0.
    # Always escalated, regardless of the total score (brief §8).
    item9_flag: bool = False


class InvalidAnswers(ValueError):
    pass


# --------------------------------------------------------------------- PHQ-9

_FREQUENCY = ("Not at all", "Several days", "More than half the days", "Nearly every day")

PHQ9 = Definition(
    instrument=Instrument.phq9,
    name="Patient Health Questionnaire (PHQ-9)",
    short_name="PHQ-9",
    description="9 questions about low mood over the last two weeks.",
    stem="Over the last 2 weeks, how often have you been bothered by any of the following?",
    options=_FREQUENCY,
    items=(
        "Little interest or pleasure in doing things",
        "Feeling down, depressed, or hopeless",
        "Trouble falling or staying asleep, or sleeping too much",
        "Feeling tired or having little energy",
        "Poor appetite or overeating",
        "Feeling bad about yourself — or that you are a failure or have let yourself "
        "or your family down",
        "Trouble concentrating on things, such as reading or watching television",
        "Moving or speaking so slowly that other people could have noticed — or the "
        "opposite, being so fidgety or restless that you have been moving around a lot "
        "more than usual",
        "Thoughts that you would be better off dead, or of hurting yourself in some way",
    ),
    minutes=3,
)

PHQ9_BANDS = (
    Band("minimal", "Minimal", 0),
    Band("mild", "Mild", 5),
    Band("moderate", "Moderate", 10),
    Band("moderately_severe", "Moderately severe", 15),
    Band("severe", "Severe", 20),
)

# --------------------------------------------------------------------- GAD-7

GAD7 = Definition(
    instrument=Instrument.gad7,
    name="Generalised Anxiety Disorder scale (GAD-7)",
    short_name="GAD-7",
    description="7 questions about worry and anxiety over the last two weeks.",
    stem="Over the last 2 weeks, how often have you been bothered by the following?",
    options=_FREQUENCY,
    items=(
        "Feeling nervous, anxious, or on edge",
        "Not being able to stop or control worrying",
        "Worrying too much about different things",
        "Trouble relaxing",
        "Being so restless that it is hard to sit still",
        "Becoming easily annoyed or irritable",
        "Feeling afraid, as if something awful might happen",
    ),
    minutes=2,
)

GAD7_BANDS = (
    Band("minimal", "Minimal", 0),
    Band("mild", "Mild", 5),
    Band("moderate", "Moderate", 10),
    Band("severe", "Severe", 15),
)

# -------------------------------------------------------------------- DASS-21

DASS21 = Definition(
    instrument=Instrument.dass21,
    name="Depression, Anxiety and Stress Scale (DASS-21)",
    short_name="DASS-21",
    description="21 statements about depression, anxiety and stress over the past week.",
    stem="How much did each statement apply to you over the past week?",
    options=(
        "Did not apply to me at all",
        "Applied to me to some degree, or some of the time",
        "Applied to me to a considerable degree, or a good part of the time",
        "Applied to me very much, or most of the time",
    ),
    items=(
        "I found it hard to wind down",  # 1  S
        "I was aware of dryness of my mouth",  # 2  A
        "I couldn't seem to experience any positive feeling at all",  # 3  D
        "I experienced breathing difficulty (e.g. excessively rapid breathing, "
        "breathlessness in the absence of physical exertion)",  # 4  A
        "I found it difficult to work up the initiative to do things",  # 5  D
        "I tended to over-react to situations",  # 6  S
        "I experienced trembling (e.g. in the hands)",  # 7  A
        "I felt that I was using a lot of nervous energy",  # 8  S
        "I was worried about situations in which I might panic and make a fool of myself",  # 9  A
        "I felt that I had nothing to look forward to",  # 10 D
        "I found myself getting agitated",  # 11 S
        "I found it difficult to relax",  # 12 S
        "I felt down-hearted and blue",  # 13 D
        "I was intolerant of anything that kept me from getting on with what I was doing",  # 14 S
        "I felt I was close to panic",  # 15 A
        "I was unable to become enthusiastic about anything",  # 16 D
        "I felt I wasn't worth much as a person",  # 17 D
        "I felt that I was rather touchy",  # 18 S
        "I was aware of the action of my heart in the absence of physical exertion "
        "(e.g. sense of heart rate increase, heart missing a beat)",  # 19 A
        "I felt scared without any good reason",  # 20 A
        "I felt that life was meaningless",  # 21 D
    ),
    minutes=5,
)

# 1-based item numbers per subscale (DASS-21 manual).
DASS21_SUBSCALES: dict[str, tuple[str, tuple[int, ...], tuple[Band, ...]]] = {
    "depression": (
        "Depression",
        (3, 5, 10, 13, 16, 17, 21),
        (
            Band("normal", "Normal", 0),
            Band("mild", "Mild", 10),
            Band("moderate", "Moderate", 14),
            Band("severe", "Severe", 21),
            Band("extremely_severe", "Extremely severe", 28),
        ),
    ),
    "anxiety": (
        "Anxiety",
        (2, 4, 7, 9, 15, 19, 20),
        (
            Band("normal", "Normal", 0),
            Band("mild", "Mild", 8),
            Band("moderate", "Moderate", 10),
            Band("severe", "Severe", 15),
            Band("extremely_severe", "Extremely severe", 20),
        ),
    ),
    "stress": (
        "Stress",
        (1, 6, 8, 11, 12, 14, 18),
        (
            Band("normal", "Normal", 0),
            Band("mild", "Mild", 15),
            Band("moderate", "Moderate", 19),
            Band("severe", "Severe", 26),
            Band("extremely_severe", "Extremely severe", 34),
        ),
    ),
}

DEFINITIONS: dict[Instrument, Definition] = {d.instrument: d for d in (PHQ9, GAD7, DASS21)}


# -------------------------------------------------------------------- scoring


def band_for(score: int, bands: tuple[Band, ...]) -> tuple[Band, int]:
    """The band containing `score`, and its index (0 = lowest)."""
    index = 0
    for i, b in enumerate(bands):
        if score >= b.min_score:
            index = i
    return bands[index], index


def validate_answers(instrument: Instrument, answers: list[int]) -> None:
    d = DEFINITIONS[instrument]
    if len(answers) != len(d.items):
        raise InvalidAnswers(f"{d.short_name} needs {len(d.items)} answers, got {len(answers)}")
    top = len(d.options) - 1
    bad = [i + 1 for i, a in enumerate(answers) if not isinstance(a, int) or not 0 <= a <= top]
    if bad:
        raise InvalidAnswers(f"answers must be 0..{top}; check item(s) {bad}")


def score(instrument: Instrument, answers: list[int]) -> ScoreResult:
    validate_answers(instrument, answers)
    if instrument is Instrument.phq9:
        return _simple(instrument, answers, PHQ9_BANDS, item9_flag=answers[8] > 0)
    if instrument is Instrument.gad7:
        return _simple(instrument, answers, GAD7_BANDS)
    return _dass21(answers)


def _simple(
    instrument: Instrument, answers: list[int], bands: tuple[Band, ...], item9_flag: bool = False
) -> ScoreResult:
    total = sum(answers)
    band, level = band_for(total, bands)
    return ScoreResult(
        instrument=instrument,
        total=total,
        max_total=3 * len(answers),
        severity=band.code,
        severity_label=band.label,
        level=level,
        max_level=len(bands) - 1,
        item9_flag=item9_flag,
    )


def _dass21(answers: list[int]) -> ScoreResult:
    subs = []
    for code, (label, items, bands) in DASS21_SUBSCALES.items():
        value = 2 * sum(answers[i - 1] for i in items)
        band, level = band_for(value, bands)
        subs.append(SubscaleScore(code, label, value, band.code, band.label, level))
    # Headline severity = the most severe subscale.
    worst = max(subs, key=lambda s: s.level)
    return ScoreResult(
        instrument=Instrument.dass21,
        total=sum(s.score for s in subs),
        max_total=2 * 3 * len(answers),
        severity=worst.severity,
        severity_label=f"{worst.severity_label} ({worst.label.lower()})"
        if worst.level > 0
        else "Normal",
        level=worst.level,
        max_level=4,
        subscales=tuple(subs),
    )


def suggests_support(result: ScoreResult) -> bool:
    """High bands: gently suggest talking to the counsellor (not an alert)."""
    return result.item9_flag or result.level >= result.max_level - 1
