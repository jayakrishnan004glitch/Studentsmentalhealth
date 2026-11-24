"""Rule-based safety gate (pure functions)."""

import pytest

from ai.safety import check_text, normalise


@pytest.mark.parametrize(
    "text",
    [
        "I want to die",
        "i wanna die tbh",
        "Sometimes I think about suicide",
        "feeling suicidal tonight",
        "I'm going to kill myself",
        "kms",
        "I don’t want to live anymore",  # curly apostrophe
        "dont want to wake up",
        "everyone would be better off without me",
        "there is no reason to live",
        "I have nothing to live for",
        "I want to end my life",
        "maybe I should just end it all",
        "I wish I was never born",
        "I'd be better off dead",
        "I KILL MYSELF IN MY HEAD",
    ],
)
def test_flags_suicidal_ideation(text: str) -> None:
    r = check_text(text)
    assert r.flagged, text
    assert "suicidal_ideation" in r.categories


@pytest.mark.parametrize(
    "text",
    ["I've been cutting myself", "I hurt myself again", "self-harm", "I took an overdose"],
)
def test_flags_self_harm(text: str) -> None:
    r = check_text(text)
    assert r.flagged and "self_harm" in r.categories


@pytest.mark.parametrize(
    "text",
    [
        "ആത്മഹത്യ ചെയ്യാൻ തോന്നുന്നു",
        "എനിക്ക് മരിക്കണം",
        "chathal mathi ennu thonnunnu",
        "enikku chaakan thonnunnu",
        "jeevikkan thalparyam illa",
    ],
)
def test_flags_malayalam_and_manglish(text: str) -> None:
    r = check_text(text)
    assert r.flagged, text
    assert r.categories == ("suicidal_ideation",)


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "   ",
        "this exam is killing me",
        "I'm dead tired after the lab",
        "lol I'm dead 😂",
        "Had a great day with friends",
    ],
)
def test_does_not_flag_ordinary_text(text: str | None) -> None:
    assert check_text(text).flagged is False


def test_prefers_false_positives() -> None:
    # Negated statements are still flagged on purpose: the student only sees
    # supportive help options, and missing a real crisis is worse.
    assert check_text("I would never kill myself").flagged is True
    # Known false positive of keyword rules (accepted trade-off):
    assert check_text("I want to die my hair blue").flagged is True


def test_both_categories_and_no_text_returned() -> None:
    r = check_text("I want to die and I keep hurting myself")
    assert r.categories == ("suicidal_ideation", "self_harm")


def test_normalise() -> None:
    assert normalise("  I DON’T   want—to LIVE!! ") == "i don't want to live"
