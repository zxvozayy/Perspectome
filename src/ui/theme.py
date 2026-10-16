"""Chart palette — the colours views.py writes into the HTML.

Navy and matte gold on white, after the site's design. Colour carries meaning
and is assigned once: a series keeps its colour in every chart. The page CSS
lives in web/site.css and uses the same values.
"""

NAVY = "#08265A"
NAVY_DEEP = "#061A3B"
GOLD = "#C6A02F"
GOLD_DEEP = "#9C7C1F"
INK = "#102A43"
MUTED = "#667085"
SLATE = "#98A2B3"  # the quiet comparison series
BLUE = "#2E6FB7"
PLUM = "#7A4FB0"
BRICK = "#B4443A"
TEAL = "#2C7A7B"

# One colour per series, everywhere. "engine" is the treatment arm seen from
# the validation side, so they share a colour.
SERIES = {
    "treatment": NAVY,
    "placebo": SLATE,
    "vanilla": MUTED,
    "real": GOLD,
    "engine": NAVY,
    "equation_baseline": BLUE,
    "ml_baseline": PLUM,
}
_EXTRA_SERIES = (BRICK, TEAL, SLATE)

# Answer options, used only where the marks are options rather than arms.
OPTION_COLORS = (GOLD, NAVY, BLUE, PLUM, BRICK, SLATE)

# Direction of a difference: above / below the reference.
ABOVE = NAVY
BELOW = BRICK


def series_color(name: str, index: int = 0) -> str:
    return SERIES.get(name) or _EXTRA_SERIES[index % len(_EXTRA_SERIES)]


def option_color(index: int) -> str:
    return OPTION_COLORS[index % len(OPTION_COLORS)]
