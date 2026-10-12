"""Design tokens, chart palettes and page CSS — one system for every screen.

A night-sea atmosphere: layered deep navy and charcoal, smoked-glass cards,
ice blue for focus. Colour carries meaning and is assigned once: a series
keeps its colour in every chart.
"""

# --- surfaces and text ---
NIGHT = "#050A12"  # top of the page gradient, and the intro's background
DEEP = "#071A2D"  # bottom of the page gradient
SURFACE = "#0E1E32"
INK = "#EAF2F8"
MUTED = "#8CA2B8"
LINE = "#1E3148"

# --- accents ---
ICE = "#55C7FF"  # primary: focus, the main series
TURQUOISE = "#4FE0C1"  # secondary
CORAL = "#FF7D7D"
AMBER = "#F4C95D"
PURPLE = "#B88CFF"
SLATE = "#8FA6BD"  # the quiet comparison series
GREY = "#5D738A"  # reference marks

BG = NIGHT
PRIMARY = ICE
ACCENT = TURQUOISE

# One colour per series, everywhere. "engine" is the treatment arm seen from
# the validation side, so they share a colour.
SERIES = {
    "treatment": ICE,
    "placebo": SLATE,
    "vanilla": GREY,
    "real": INK,
    "engine": ICE,
    "equation_baseline": TURQUOISE,
    "ml_baseline": PURPLE,
}
_EXTRA_SERIES = (AMBER, CORAL, SLATE)

# Answer options, used only where the marks are options rather than arms.
OPTION_COLORS = (AMBER, PURPLE, SLATE, TURQUOISE, CORAL, ICE)

# Direction of a difference: above / below the reference.
ABOVE = TURQUOISE
BELOW = CORAL

# The intro's communities.
COMMUNITIES = (AMBER, CORAL, PURPLE)


def series_color(name: str, index: int = 0) -> str:
    return SERIES.get(name) or _EXTRA_SERIES[index % len(_EXTRA_SERIES)]


def option_color(index: int) -> str:
    return OPTION_COLORS[index % len(OPTION_COLORS)]


FONT_URL = (
    "https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&display=swap"
)

CSS = f"""
<style>
@import url('{FONT_URL}');

:root {{
  --night: {NIGHT}; --deep: {DEEP}; --ink: {INK}; --muted: {MUTED};
  --primary: {PRIMARY}; --accent: {ACCENT}; --saffron: {AMBER}; --oxide: {CORAL}; --grey: {GREY};
  --below: {BELOW}; --above: {ABOVE};
  --line: rgba(140, 180, 220, .15);
  --glass: linear-gradient(180deg, rgba(22, 42, 66, .56), rgba(11, 24, 40, .56));
  --ease: cubic-bezier(.2, .7, .2, 1);
}}

/* --- atmosphere: layered night sea, never flat black --- */
.stApp {{
  background:
    radial-gradient(1100px 620px at 82% -12%, rgba(85, 199, 255, .08), transparent 62%),
    radial-gradient(900px 620px at -6% 104%, rgba(79, 224, 193, .05), transparent 60%),
    linear-gradient(165deg, var(--night) 0%, var(--deep) 62%, #06111E 100%);
  background-attachment: fixed;
}}

.block-container {{ max-width: 920px; padding-top: 2.2rem; padding-bottom: 7rem;
  animation: pt-fade .6s ease both; }}
header[data-testid="stHeader"] {{ background: transparent; }}

/* --- buttons: white pill for the one main action, quiet outlines for the rest --- */
.stButton button {{ border-radius: 999px; border-color: var(--line); transition: all .2s var(--ease); }}
.stButton button {{ background: rgba(18, 36, 58, .45); }}
.stButton button:hover {{ border-color: rgba(85, 199, 255, .45); background: rgba(24, 48, 76, .6); color: var(--ink); }}
.stButton button[kind="primary"] {{ background: var(--ink); color: var(--night); border-color: var(--ink);
  font-weight: 600; padding: .6rem 2rem; }}
.stButton button[kind="primary"]:hover {{ background: #fff; color: var(--night); transform: translateY(-1px);
  box-shadow: 0 10px 34px rgba(85, 199, 255, .22); }}
[data-testid="stChatInput"] > div {{ border-radius: 22px; border: 1px solid var(--line);
  background: rgba(12, 26, 44, .78); backdrop-filter: blur(14px); }}
[data-testid="stBottom"] > div {{ background: linear-gradient(transparent, rgba(8, 28, 48, .94) 45%); }}
[data-testid="stBottom"] {{ background: transparent; }}
[data-testid="stExpander"] details {{ background: rgba(12, 26, 44, .4); border-color: var(--line); border-radius: 14px; }}

/* --- history panel, on the right --- */
@media (min-width: 769px) {{ [data-testid="stAppViewContainer"] {{ flex-direction: row-reverse; }} }}
[data-testid="stSidebar"][aria-expanded="false"] > div {{ visibility: hidden; }}  /* nothing leaks out when closed */
[data-testid="stSidebar"] {{ background: rgba(5, 12, 22, .6); backdrop-filter: blur(18px);
  border-left: 1px solid var(--line); }}
[data-testid="stSidebar"] .stButton button {{ border-radius: 10px; border-color: transparent;
  background: transparent; color: var(--muted); justify-content: flex-start; padding: .4rem .7rem; }}
[data-testid="stSidebar"] .stButton button p {{ overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; text-align: left; }}
[data-testid="stSidebar"] .stButton button:hover {{ background: rgba(24, 48, 76, .5); color: var(--ink); }}
[data-testid="stSidebar"] .stButton button[kind="primary"] {{ background: rgba(85, 199, 255, .12); color: var(--ink);
  font-weight: 500; box-shadow: none; transform: none; }}
[data-testid="stSidebar"] .st-key-new-chat button {{ border-color: var(--line); color: var(--ink);
  justify-content: center; }}

/* --- intro and empty chat --- */
.pt-listen {{ text-align: center; font-size: 46px; font-weight: 500; letter-spacing: -.02em;
  color: rgba(234,242,248,.2); margin: 20vh 0 6px; animation: pt-breathe 5s ease-in-out infinite; }}
@keyframes pt-breathe {{ 50% {{ color: rgba(234,242,248,.34); }} }}

.pt, .pt * {{ font-family: 'Instrument Sans', system-ui, sans-serif; box-sizing: border-box; }}
.pt {{ color: var(--ink); font-size: 14px; line-height: 1.5; }}
.pt .num {{ font-variant-numeric: tabular-nums; }}

@keyframes pt-rise {{ from {{ opacity: 0; transform: translateY(10px); }} }}
@keyframes pt-fade {{ from {{ opacity: 0; }} }}
@keyframes pt-w {{ from {{ width: var(--from, 0%); }} }}
@keyframes pt-sx {{ from {{ transform: scaleX(0); }} }}
@keyframes pt-draw {{ to {{ stroke-dashoffset: 0; }} }}
@keyframes pt-x {{ from {{ left: var(--from); }} }}
@keyframes pt-pop {{ from {{ opacity: 0; transform: translate(-50%, -50%) scale(.3); }} }}
@keyframes pt-dot {{ 0%, 60%, 100% {{ opacity: .25; transform: none; }} 30% {{ opacity: 1; transform: translateY(-3px); }} }}

/* --- chat --- */
.pt-user {{ display: flex; justify-content: flex-end; margin: 10px 0 14px; animation: pt-rise .35s var(--ease) both; }}
.pt-user > div {{
  background: var(--glass); border: 1px solid var(--line); border-radius: 18px 18px 4px 18px;
  padding: 10px 16px; max-width: 78%; font-size: 15px; backdrop-filter: blur(14px);
}}
.pt-who {{ display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px;
  letter-spacing: .04em; text-transform: uppercase; font-weight: 600; margin-top: 6px; }}
.pt-who i {{ width: 8px; height: 8px; border-radius: 50%; background: var(--primary);
  box-shadow: 0 0 10px var(--primary); }}
.pt-typing {{ display: flex; gap: 5px; padding: 6px 2px; }}
.pt-typing i {{ width: 7px; height: 7px; border-radius: 50%; background: var(--primary);
  animation: pt-dot 1.1s infinite; }}
.pt-typing i:nth-child(2) {{ animation-delay: .15s; }}
.pt-typing i:nth-child(3) {{ animation-delay: .3s; }}

.pt-top {{ display: flex; align-items: baseline; gap: 12px; }}
.pt-top b {{ font-size: 20px; font-weight: 500; letter-spacing: -.01em; }}
.pt-badge {{ font-size: 11px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase;
  color: var(--saffron); border: 1px solid color-mix(in srgb, var(--saffron) 45%, transparent);
  border-radius: 999px; padding: 2px 9px; }}
.pt-hint {{ color: var(--muted); font-size: 13px; text-align: center; margin: 2px 0 6px; }}

/* --- cards --- */
/* Smoked glass, kept quiet: the content leads. */
.pt-card {{ background: var(--glass); border: 1px solid var(--line); border-radius: 18px;
  padding: 24px 26px; margin-bottom: 20px; backdrop-filter: blur(14px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .05), 0 24px 50px -34px rgba(0, 0, 0, .7);
  animation: pt-rise .55s var(--ease) both; }}
.pt-eyebrow {{ color: var(--muted); font-size: 11px; font-weight: 600; letter-spacing: .07em;
  text-transform: uppercase; }}
.pt-card > .pt-eyebrow:first-child {{ margin-bottom: 16px; }}
.pt-title {{ font-size: 20px; font-weight: 500; margin: -10px 0 14px; }}
.pt-note {{ color: var(--muted); font-size: 12.5px; margin-top: 12px; }}
.pt-legend {{ display: flex; flex-wrap: wrap; gap: 6px 16px; margin-top: 14px; color: var(--muted);
  font-size: 12.5px; }}
.pt-legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
.pt-sw {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
.pt-sw.tick {{ width: 2px; height: 12px; border-radius: 0; }}
.pt-sw.dot {{ border-radius: 50%; }}
.pt-foot {{ color: var(--muted); font-size: 12px; opacity: .8; margin: 2px 2px 14px; }}

/* --- micro-explanations --- */
.pt-tip {{ position: relative; display: inline-grid; place-items: center; width: 15px; height: 15px;
  margin-left: 6px; border: 1px solid var(--muted); border-radius: 50%; color: var(--muted);
  font-size: 10px; font-weight: 600; font-style: normal; letter-spacing: 0; text-transform: none;
  line-height: 1; cursor: help; vertical-align: 1px; }}
.pt-tip::after {{ content: attr(data-tip); position: absolute; left: 50%; bottom: calc(100% + 9px);
  transform: translate(-50%, 4px); width: max-content; max-width: min(280px, 70vw);
  background: #0B1A2B; border: 1px solid rgba(140, 180, 220, .25); border-radius: 10px;
  padding: 9px 11px; color: var(--ink); font-size: 12.5px; font-weight: 400; line-height: 1.45;
  text-align: left; white-space: normal; box-shadow: 0 14px 34px rgba(0, 0, 0, .5);
  opacity: 0; pointer-events: none; transition: opacity .18s ease, transform .18s ease; z-index: 30; }}
.pt-tip:hover::after, .pt-tip:focus::after {{ opacity: 1; transform: translate(-50%, 0); }}
.pt-tip:hover, .pt-tip:focus {{ color: var(--primary); border-color: var(--primary); outline: none; }}

/* --- warnings --- */
.pt-warn {{ border: 1px solid color-mix(in srgb, var(--saffron) 40%, transparent);
  border-left: 3px solid var(--saffron); border-radius: 12px; padding: 12px 16px;
  background: color-mix(in srgb, var(--saffron) 6%, transparent); margin-bottom: 20px;
  animation: pt-rise .4s var(--ease) both; }}
.pt-warn .pt-eyebrow {{ color: var(--saffron); }}
.pt-warn ul {{ margin: 4px 0 0; padding-left: 18px; }}
.pt-warn li {{ margin: 2px 0; }}

/* --- effect headline --- */
.pt-big {{ font-size: 38px; font-weight: 500; letter-spacing: -.02em; line-height: 1.15; margin: 6px 0 2px; }}
.pt-big small {{ font-size: 15px; color: var(--muted); font-weight: 400; letter-spacing: 0; margin-left: 6px; }}
.pt-big.null {{ font-size: 24px; color: var(--muted); }}
.pt-eff {{ display: grid; grid-template-columns: 110px 1fr 84px; align-items: center; gap: 4px 12px;
  margin-top: 16px; }}
.pt-eff .trk {{ position: relative; height: 14px; }}
.pt-eff .trk::before {{ content: ''; position: absolute; left: 50%; top: -3px; bottom: -3px;
  width: 1px; background: var(--muted); opacity: .6; }}
.pt-eff .bar {{ position: absolute; top: 0; height: 100%; border-radius: 3px;
  animation: pt-sx .8s var(--ease) .15s both; }}
.pt-eff .bar.pos {{ left: 50%; transform-origin: left; background: var(--above); }}
.pt-eff .bar.neg {{ right: 50%; transform-origin: right; background: var(--below); }}
.pt-eff .v {{ text-align: right; }}

.pt-noise {{ margin-top: 20px; padding-top: 14px; border-top: 1px solid var(--line); }}
.pt-noise .trk {{ position: relative; height: 22px; margin: 26px 0 6px; background:
  rgba(140, 180, 220, .08); border-radius: 4px; }}
.pt-noise .band {{ position: absolute; inset: 0 auto 0 0; border-radius: 4px 0 0 4px;
  border-right: 1px dashed var(--muted);
  background: repeating-linear-gradient(135deg, transparent 0 5px, rgba(140,162,184,.32) 5px 7px); }}
.pt-noise .eff {{ position: absolute; left: 0; top: 7px; height: 8px; border-radius: 4px;
  background: var(--primary); animation: pt-w 1.1s var(--ease) .3s both; }}
.pt-noise .eff.null {{ background: var(--grey); }}
.pt-noise .lab {{ position: absolute; top: -22px; font-size: 12px; color: var(--muted);
  white-space: nowrap; animation: pt-fade .5s ease 1s both; }}
.pt-noise .lab.e {{ color: var(--ink); transform: translateX(-100%); }}

/* --- arm bars --- */
.pt-bars {{ display: grid; grid-template-columns: 110px 1fr; gap: 14px 12px; align-items: center; }}
.pt-bars .tracks {{ position: relative; margin-right: 52px; display: grid; gap: 3px; }}
.pt-bars .trk {{ position: relative; height: 13px; }}
.pt-bars .bar {{ height: 100%; width: var(--w); min-width: 2px; border-radius: 3px;
  animation: pt-w .9s var(--ease) both; }}
.pt-bars .bar.shift {{ animation-duration: 1.1s; animation-delay: .7s; }}
.pt-bars .v {{ position: absolute; left: calc(var(--w) + 8px); top: -3px; font-size: 12.5px;
  color: var(--muted); animation: pt-fade .4s ease 1.5s both; }}
.pt-bars .tick {{ position: absolute; top: -3px; bottom: -3px; left: var(--v); width: 2px;
  background: var(--grey); animation: pt-fade .5s ease 1.6s both; }}

/* --- dot plot: both arms on one scale --- */
.pt-dots {{ display: grid; grid-template-columns: 110px 1fr 104px; gap: 16px 12px; align-items: center; }}
.pt-dots .trk {{ position: relative; height: 22px;
  background: linear-gradient(90deg, rgba(140, 180, 220, .16) 1px, transparent 1px) 0 0 / 25% 100%;
  border-right: 1px solid rgba(140, 180, 220, .16); }}
.pt-dots .seg {{ position: absolute; top: 50%; height: 2px; margin-top: -1px; left: var(--a); width: var(--len);
  background: var(--muted); opacity: .7; animation: pt-fade .5s ease 1.2s both; }}
.pt-dots .dot {{ position: absolute; top: 50%; left: var(--x); width: 13px; height: 13px; border-radius: 50%;
  transform: translate(-50%, -50%); box-shadow: 0 0 0 3px rgba(5, 12, 22, .7);
  animation: pt-pop .5s var(--ease) both; }}
.pt-dots .dot.move {{ animation: pt-x 1.1s var(--ease) .5s both; }}
.pt-dots .van {{ position: absolute; top: 1px; bottom: 1px; left: var(--x); width: 2px; margin-left: -1px;
  background: var(--grey); }}
.pt-dots .v {{ text-align: right; color: var(--muted); font-size: 13px; }}
.pt-dots .v b {{ color: var(--ink); font-weight: 500; }}
.pt-dots .axis {{ position: relative; height: 16px; font-size: 11.5px; color: var(--muted); }}
.pt-dots .axis span {{ position: absolute; transform: translateX(-50%); }}

/* --- svg charts --- */
.pt-svg {{ width: 100%; height: auto; display: block; overflow: visible; }}
.pt-svg text {{ fill: var(--muted); font-size: 12px; font-family: 'Instrument Sans', system-ui, sans-serif;
  font-variant-numeric: tabular-nums; }}
.pt-svg text.ink {{ fill: var(--ink); }}
.pt-svg .grid {{ stroke: rgba(140, 180, 220, .16); stroke-width: 1; }}
.pt-svg .ln {{ fill: none; stroke-linecap: round; stroke-linejoin: round;
  animation: pt-draw 1.1s var(--ease) both; }}
.pt-svg .pt-late {{ animation: pt-fade .4s ease 1s both; }}

/* --- tvd bars --- */
.pt-tvd {{ display: grid; grid-template-columns: 150px 1fr; gap: 9px 12px; align-items: center; }}
.pt-tvd .trk {{ position: relative; height: 13px; margin-right: 52px; }}
.pt-tvd .bar {{ height: 100%; width: var(--w); min-width: 2px; border-radius: 3px;
  animation: pt-w .9s var(--ease) both; }}
.pt-tvd .v {{ position: absolute; left: calc(var(--w) + 8px); top: -3px; font-size: 12.5px; }}
.pt-tvd .floor {{ position: absolute; left: var(--f); top: -5px; bottom: -5px; width: 0;
  border-left: 1px dashed var(--muted); }}

/* --- tables / details --- */
.pt-table {{ width: 100%; border-collapse: collapse; }}
.pt-table th, .pt-table td {{ border: 0; background: transparent; }}
.pt-table th {{ text-align: left; color: var(--muted); font-size: 11px; font-weight: 600;
  letter-spacing: .06em; text-transform: uppercase; padding: 6px 10px 6px 0;
  border-bottom: 1px solid var(--line); }}
.pt-table td {{ padding: 9px 10px 9px 0; border-bottom: 1px solid rgba(140, 180, 220, .08); }}
.pt-table td.r, .pt-table th.r {{ text-align: right; }}
.pt-flag {{ color: var(--oxide); font-weight: 600; }}
.pt-dl {{ display: grid; grid-template-columns: 170px 1fr; gap: 5px 12px; margin: 0; }}
.pt-dl dt {{ color: var(--muted); }}
.pt-dl dd {{ margin: 0; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }}

/* --- subgroups --- */
.pt-cells {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
.pt-cell {{ border: 1px solid var(--line); border-radius: 12px; padding: 9px 14px; min-width: 96px;
  background: rgba(12, 26, 44, .35);
  animation: pt-rise .4s var(--ease) both; }}
.pt-cell b {{ font-weight: 500; display: block; }}
.pt-cell .arrow {{ font-size: 20px; line-height: 1.2; }}
.pt-cell .arrow.up {{ color: var(--above); }}
.pt-cell .arrow.down {{ color: var(--below); }}
.pt-cell.small {{ opacity: .62; border-style: dashed; }}
.pt-cell.small span {{ font-size: 11.5px; color: var(--muted); }}

/* --- map --- */
.pt-map {{ position: relative; }}
.pt-map path {{ fill: rgba(22, 46, 74, .55); stroke: rgba(170, 210, 240, .5); stroke-width: 1.2;
  filter: drop-shadow(0 6px 10px rgba(0, 0, 0, .55)) drop-shadow(0 -1px 0 rgba(255, 255, 255, .12)); }}
.pt-map .msg {{ position: absolute; inset: 0; display: grid; place-items: center; text-align: center;
  padding: 0 14%; }}

@media (max-width: 640px) {{
  .pt-card {{ padding: 18px 16px; border-radius: 16px; }}
  .pt-big {{ font-size: 30px; }}
  .pt-eff {{ grid-template-columns: 84px 1fr 72px; }}
  .pt-bars, .pt-tvd {{ grid-template-columns: 96px 1fr; }}
  .pt-dots {{ grid-template-columns: 84px 1fr 86px; }}
  .pt-dl {{ grid-template-columns: 120px 1fr; }}
  .pt-listen {{ font-size: 34px; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .pt, .pt * {{ animation: none !important; }}
  .pt-svg .ln {{ stroke-dashoffset: 0 !important; }}
}}
</style>
"""
