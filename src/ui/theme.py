"""Chart palette — the colours views.py writes into the HTML.

Blue and matte gold, after the site's design. Colour carries meaning and is
assigned once: a series keeps its colour in every chart. The values are
mid-tones so they read on both the light and the dark panel. The page CSS
lives in web/site.css and web/panel.css and uses the same values.
"""

BLUE = "#1E4FD0"    # the treatment arm, the engine
SKY = "#6EA8FF"
GOLD = "#C6A02F"    # the real survey answer
INK = "#102A43"
MUTED = "#667085"
SLATE = "#98A2B3"   # the quiet comparison series
PLUM = "#7A4FB0"
BRICK = "#B4443A"
TEAL = "#2C7A7B"

# One colour per series, everywhere. "engine" is the treatment arm seen from
# the validation side, so they share a colour.
SERIES = {
    "treatment": BLUE,
    "placebo": SLATE,
    "vanilla": MUTED,
    "real": GOLD,
    "engine": BLUE,
    "equation_baseline": SKY,
    "ml_baseline": PLUM,
}
_EXTRA_SERIES = (BRICK, TEAL, SLATE)

# Answer options, used only where the marks are options rather than arms.
OPTION_COLORS = (GOLD, BLUE, SKY, PLUM, BRICK, TEAL)

# Direction of a difference: above / below the reference.
ABOVE = BLUE
BELOW = BRICK


def series_color(name: str, index: int = 0) -> str:
    return SERIES.get(name) or _EXTRA_SERIES[index % len(_EXTRA_SERIES)]


def option_color(index: int) -> str:
    return OPTION_COLORS[index % len(OPTION_COLORS)]
