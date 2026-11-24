"""Rule-based safety gate: detects possible self-harm / suicidal language.

Runs on every piece of free text a student sends (journal notes now; chat
messages later) BEFORE any model sees it. A match forces the High-risk path
(design rule: the LLM never decides risk; rules can only raise it).

Design choices:
- Prefer false positives over false negatives. "I'd never kill myself" is
  still flagged; the student just sees supportive help options.
- Common idioms that are NOT self-harm ("this exam is killing me", "dead
  tired") are deliberately not matched.
- Only rule CATEGORIES are returned and stored, never the matched text.
- English plus a starter set of Malayalam (script and Manglish) phrases.
  TEAM: review and extend the Malayalam list with native speakers.
"""

import re
import unicodedata
from dataclasses import dataclass, field

# category -> patterns (matched against normalised, lower-cased text)
_RULES: dict[str, tuple[str, ...]] = {
    "suicidal_ideation": (
        r"\bsuicid(e|al)\b",
        r"\bkill(ing)? ?my ?self\b",
        r"\bkms\b",
        r"\b(want|wanted|wanna|going|gonna|plan|planning) to die\b",
        r"\b(wanna|gonna) die\b",
        r"\bi (want|wish) (i was|i were|to be) dead\b",
        r"\bend (my|it all|my own) li(fe|ves)\b",
        r"\bend it all\b",
        r"\btake my (own )?life\b",
        r"\bhang(ing)? my ?self\b",
        r"\bjump (off|from) (a|the|my) (bridge|building|roof|terrace|balcony)\b",
        r"\bdon'?t want to (live|be alive|exist|wake up)( anymore)?\b",
        r"\b(better off|be better) dead\b",
        r"\bno (reason|point) (to live|in living|living)\b",
        r"\bnothing to live for\b",
        r"\bnot worth living\b",
        r"\blife (is|feels) (not worth|pointless|meaningless)\b",
        r"\beveryone would be better (off )?without me\b",
        r"\bwish i (was|were|had) never (been )?born\b",
    ),
    "self_harm": (
        r"\bself[- ]?harm(ing)?\b",
        r"\b(hurt|hurting|harm|harming|cut|cutting|burn|burning) my ?self\b",
        r"\boverdos(e|ed|ing)\b",
        r"\bswallow(ed)? (all )?(the |my )?(pills|tablets)\b",
    ),
    # Malayalam script and common Manglish spellings.
    "suicidal_ideation_ml": (
        r"ആത്മഹത്യ",
        r"മരിക്കണം",
        r"മരിക്കാൻ തോന്നുന്നു",
        r"ചാകണം",
        r"ചാകാൻ തോന്നുന്നു",
        r"ജീവിക്കാൻ (താല്പര്യമില്ല|തോന്നുന്നില്ല)",
        r"\baathmahathya\b|\batmahatya\b|\bathmahathya\b",
        r"\b(chaakan|chakan|chaakanam|chakanam|marikkan|marikanam|marikkanam)\b",
        r"\bchathal (mathi|madhi)\b",
        r"\bjeevikkan (thalparyam ?illa|thonnunnilla|vayya)\b",
    ),
}

_COMPILED = {cat: tuple(re.compile(p) for p in pats) for cat, pats in _RULES.items()}


@dataclass(frozen=True)
class SafetyResult:
    flagged: bool
    categories: tuple[str, ...] = field(default_factory=tuple)


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'").replace("‘", "'")
    # Keep letters, combining marks (Malayalam vowel signs and virama are marks,
    # not letters) and digits from any script, plus apostrophes. Drop format
    # characters (ZWJ/ZWNJ); everything else becomes a space.
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if ch == "'" or cat[0] in "LMN":
            out.append(ch)
        elif cat != "Cf":
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def check_text(text: str | None) -> SafetyResult:
    if not text or not text.strip():
        return SafetyResult(flagged=False)
    norm = normalise(text)
    cats = tuple(
        cat.removesuffix("_ml")
        for cat, patterns in _COMPILED.items()
        if any(p.search(norm) for p in patterns)
    )
    cats = tuple(dict.fromkeys(cats))  # dedupe, keep order
    return SafetyResult(flagged=bool(cats), categories=cats)
