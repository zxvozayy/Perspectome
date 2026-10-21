"""HTML for every answer block. Display only — no metric is computed here.

Every number comes straight from results.json / comparison.json; if Track C
hasn't provided an effect, none is shown (src/ui/README.md, honesty rules).
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path

from src.common.schema import MIN_CELL_N, SATURATION
from src.ui import theme

PRIOR_CAVEAT = "This may reflect the model's prior, not the population."
PRIOR_CAVEAT_TR = "Bu sonuç nüfusu değil, modelin ön kabulünü yansıtıyor olabilir."
NO_EFFECT = "Gürültünün üstünde ölçülebilir etki yok"
NOT_SCORED = "Track C bu senaryoyu henüz puanlamadı"
SMALL_CELL = f"n < {MIN_CELL_N}, not tested"

ARM_LABELS = {"treatment": "Treatment", "placebo": "Placebo", "vanilla": "Vanilla"}
METHOD_LABELS = {
    "real": "Gerçek veri",
    "engine": "Engine",
    "vanilla": "Vanilla (personasız)",
    "equation_baseline": "Denklem baseline",
    "ml_baseline": "ML baseline",
    "engine_calibrated": "Engine (kalibre)",
    "stacked": "Engine + ML",
}
# Never rendered: income needs Track C's confirmation in real data (no contract
# field for that yet), and province-level cells are too thin by rule.
HIDDEN_DIMENSIONS = ("income", "province", "city", "district")

_TURKEY = Path(__file__).parent / "assets" / "turkey.json"


def esc(value) -> str:
    return html.escape(str(value))


def share(x: float) -> str:
    return f"%{round(x * 100)}"


def points(x: float) -> str:
    n = round(x * 100)
    return f"{n:+d} puan" if n else "0 puan"


def dec(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def tip(text: str) -> str:
    """A small "i" that explains a technical term on hover or keyboard focus."""
    return f'<i class="pt-tip" tabindex="0" data-tip="{esc(text)}">i</i>' if text else ""


TIPS = {
    "effect": "Treatment kolundaki pay eksi placebo kolundaki pay. Nüfustaki oran değil, senaryonun yarattığı fark.",
    "noise": "Aynı ayar iki kez çalıştırıldığında kendiliğinden çıkan fark. Bundan küçük etkiler rastlantıdan ayırt edilemez.",
    "arms": "Treatment: personalara senaryo gösterilir. Placebo: aynı personalara ilgisiz bir metin gösterilir. "
            "Vanilla: persona olmadan modelin kendi yanıtı.",
    "subgroups": "Alt gruplarda yalnızca yön gösterilir. Hücredeki kişi sayısı azsa yön test edilmez.",
    "tvd": "Total variation distance: iki dağılımın ne kadar ayrıştığı. 0 aynı, 1 tamamen farklı.",
    "probe": "Gerçek anketteki yanıtı bilinen bir soru. Simülasyonun ne kadar isabetli olduğunu ölçmek için kullanılır.",
    "rank": "Kendall tau: maddelerin sıralaması gerçek sıralamayla ne kadar örtüşüyor. 1 aynı sıra, 0 ilişkisiz.",
    "models": "Aynı deney farklı dil modelleriyle tekrarlanır. Ayrıştıkları yerde sonuç modele bağlıdır.",
}
MODEL_NOTE = "Model tabanlı simülasyon. Gerçek kişileri ya da nüfustaki kesin oranları göstermez; eğilimleri karşılaştırır."


def footnote() -> str:
    return f'<div class="pt pt-foot">{esc(MODEL_NOTE)}</div>'


def card(inner: str, eyebrow: str = "", title: str = "", hint: str = "") -> str:
    head = f'<div class="pt-eyebrow">{esc(eyebrow)}{tip(hint)}</div>' if eyebrow else ""
    head += f'<div class="pt-title">{esc(title)}</div>' if title else ""
    return f'<div class="pt pt-card">{head}{inner}</div>'


def _legend(items: list[tuple[str, str, str]]) -> str:
    """items: (colour, label, 'tick' | '')."""
    spans = "".join(
        f'<span><i class="pt-sw {kind}" style="background:{c}"></i>{esc(label)}</span>'
        for c, label, kind in items
    )
    return f'<div class="pt-legend">{spans}</div>'


# ---------------------------------------------------------------- chat chrome

def user_bubble(text: str) -> str:
    return f'<div class="pt pt-user"><div>{esc(text)}</div></div>'


def assistant_label() -> str:
    return '<div class="pt pt-who"><i></i>Perspectome</div>'


# ------------------------------------------------------------------- warnings

def warnings(items: list[str], scenario_caveat: bool = False) -> str:
    """Track C's warnings verbatim, plus the model-prior caveat on scenarios."""
    lis = ""
    if scenario_caveat:
        lis += f"<li>{esc(PRIOR_CAVEAT_TR)} <i>({esc(PRIOR_CAVEAT)})</i></li>"
    lis += "".join(f"<li>{esc(w)}</li>" for w in items)
    if not lis:
        return ""
    return f'<div class="pt pt-warn"><div class="pt-eyebrow">Uyarılar</div><ul>{lis}</ul></div>'


# ------------------------------------------------------------- scenario views

def effect_headline(scored: dict | None, noise_floor: float | None) -> str:
    """The headline is the effect (treatment − placebo), never an absolute share."""
    eyebrow = "Etki · treatment − placebo"
    if scored is None:
        return card(
            f'<div class="pt-big null">{NOT_SCORED}</div>'
            '<div class="pt-note">Etki bu panelde hesaplanmaz; aşağıda yalnızca kolların '
            "dağılımı karşılaştırılır.</div>",
            eyebrow, hint=TIPS["effect"],
        )
    if not scored.get("measurable"):
        note = ""
        if scored.get("saturated"):
            note = (
                f'<div class="pt-note">Madde doygun: placebo payı %{SATURATION[0] * 100:.0f}–%{SATURATION[1] * 100:.0f} aralığının dışında, '
                "bu yüzden etki gösteremez.</div>"
            )
        return card(f'<div class="pt-big null">{NO_EFFECT}</div>{note}', eyebrow, hint=TIPS["effect"])

    effects = scored.get("effect_vs_placebo") or {}
    body = ""
    if effects:
        top = max(effects, key=lambda k: abs(effects[k]))
        colour = theme.ABOVE if effects[top] >= 0 else theme.BELOW
        body += (
            f'<div class="pt-big">{esc(top)} '
            f'<span class="num" style="color:{colour}">{points(effects[top])}</span></div>'
        )
        biggest = max(abs(v) for v in effects.values()) or 1
        rows = ""
        for opt, v in effects.items():
            side = "pos" if v >= 0 else "neg"
            width = abs(v) / biggest * 46
            rows += (
                f"<div>{esc(opt)}</div>"
                f'<div class="trk"><div class="bar {side}" style="width:{width:.1f}%"></div></div>'
                f'<div class="v num">{points(v)}</div>'
            )
        body += f'<div class="pt-eff">{rows}</div>'

    tvd = scored.get("effect_tvd")
    if tvd is not None and noise_floor:
        full = max(tvd, noise_floor) * 1.25
        body += (
f'<div class="pt-noise"><div class="pt-eyebrow">Etki ve gürültü tabanı (TVD){tip(TIPS["noise"])}</div>'
            '<div class="trk" style="margin-bottom:28px">'
            f'<div class="band" style="width:{noise_floor / full * 100:.1f}%"></div>'
            f'<div class="eff" style="width:{tvd / full * 100:.1f}%"></div>'
            f'<div class="lab e num" style="left:{tvd / full * 100:.1f}%">etki {dec(tvd)}</div>'
            f'<div class="lab num" style="top:28px;left:0">gürültü tabanı {dec(noise_floor)}'
            " — bunun altındaki fark raporlanmaz</div>"
            "</div></div>"
        )

    eq = scored.get("equation_baseline_effect")
    if eq:
        parts = " · ".join(f"{esc(k)} {points(v)}" for k, v in eq.items())
        body += f'<div class="pt-note">Denklem baseline aynı senaryoda: <span class="num">{parts}</span></div>'
    return card(body, eyebrow, hint=TIPS["effect"])


def arm_bars(run: dict) -> str:
    arms = run["arms"]
    treatment = (arms.get("treatment") or {}).get("response_distribution") or {}
    placebo = (arms.get("placebo") or {}).get("response_distribution") or {}
    vanilla = (arms.get("vanilla") or {}).get("response_distribution") or {}
    rows = ""
    for opt in run["options"]:
        tracks = ""
        if opt in placebo:
            p = placebo[opt] * 100
            tracks += (
                f'<div class="trk" style="--w:{p:.1f}%"><div class="bar" '
                f'style="background:{theme.SERIES["placebo"]}"></div>'
                f'<span class="v num">{share(placebo[opt])}</span></div>'
            )
        if opt in treatment:
            t = treatment[opt] * 100
            start = f"--from:{placebo[opt] * 100:.1f}%;" if opt in placebo else ""
            tracks += (
                f'<div class="trk" style="--w:{t:.1f}%"><div class="bar shift" '
                f'style="{start}background:{theme.SERIES["treatment"]}"></div>'
                f'<span class="v num">{share(treatment[opt])}</span></div>'
            )
        if opt in vanilla:
            tracks += (
                f'<div class="tick" style="--v:{vanilla[opt] * 100:.1f}%" '
                f'title="Vanilla {share(vanilla[opt])}"></div>'
            )
        rows += f'<div>{esc(opt)}</div><div class="tracks">{tracks}</div>'
    legend = _legend([
        (theme.SERIES["placebo"], "Placebo", ""),
        (theme.SERIES["treatment"], "Treatment", ""),
        (theme.SERIES["vanilla"], "Vanilla — personasız referans", "tick"),
    ])
    note = (
        '<div class="pt-note">Paylar yalnızca kolları karşılaştırmak içindir; '
        "nüfus tahmini olarak okunmaz.</div>"
    )
    return card(f'<div class="pt-bars">{rows}</div>{legend}{note}', "Treatment ve placebo, yan yana", hint=TIPS["arms"])


def arm_dots(run: dict) -> str:
    """Both arms on one 0–100 scale: where placebo sits, and where treatment moved to."""
    arms = run["arms"]
    treatment = (arms.get("treatment") or {}).get("response_distribution") or {}
    placebo = (arms.get("placebo") or {}).get("response_distribution") or {}
    vanilla = (arms.get("vanilla") or {}).get("response_distribution") or {}
    rows = ""
    for opt in run["options"]:
        marks, values = "", []
        if opt in vanilla:
            marks += f'<div class="van" style="--x:{vanilla[opt] * 100:.1f}%" title="Vanilla {share(vanilla[opt])}"></div>'
        if opt in placebo and opt in treatment:
            a, b = sorted((placebo[opt] * 100, treatment[opt] * 100))
            marks += f'<div class="seg" style="--a:{a:.1f}%;--len:{b - a:.1f}%"></div>'
        if opt in placebo:
            marks += f'<div class="dot" style="--x:{placebo[opt] * 100:.1f}%;background:{theme.SERIES["placebo"]}"></div>'
            values.append(share(placebo[opt]))
        if opt in treatment:
            start = f"--from:{placebo[opt] * 100:.1f}%;" if opt in placebo else ""
            marks += (
                f'<div class="dot{" move" if start else ""}" '
                f'style="{start}--x:{treatment[opt] * 100:.1f}%;background:{theme.SERIES["treatment"]}"></div>'
            )
            values.append(f"<b>{share(treatment[opt])}</b>")
        rows += f'<div>{esc(opt)}</div><div class="trk">{marks}</div><div class="v num">{" → ".join(values)}</div>'
    axis = "".join(f'<span style="left:{x}%">%{x}</span>' for x in (0, 25, 50, 75, 100))
    rows += f'<div></div><div class="axis num">{axis}</div><div></div>'
    legend = _legend([
        (theme.SERIES["placebo"], "Placebo", "dot"),
        (theme.SERIES["treatment"], "Treatment", "dot"),
        (theme.SERIES["vanilla"], "Vanilla — personasız referans", "tick"),
    ])
    note = (
        '<div class="pt-note">Paylar yalnızca kolları karşılaştırmak içindir; '
        "nüfus tahmini olarak okunmaz.</div>"
    )
    return card(f'<div class="pt-dots">{rows}</div>{legend}{note}', "Aynı ölçekte: placebo'dan treatment'a", hint=TIPS["arms"])


def _spread(ys: list[float], gap: float = 16) -> list[float]:
    """Push label positions apart so they don't overlap; order is kept."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    return out


def slope(run: dict, scored: dict | None) -> str:
    arms = run["arms"]
    placebo = (arms.get("placebo") or {}).get("response_distribution")
    treatment = (arms.get("treatment") or {}).get("response_distribution")
    if not placebo or not treatment:
        return card('<div class="pt-note">Bu çalıştırmada placebo kolu yok.</div>', "Placebo → treatment")
    options = run["options"]
    effects = (scored or {}).get("effect_vs_placebo") if (scored or {}).get("measurable") else None

    w, h, xl, xr, top, bottom = 640, 250, 210, 430, 34, 226
    ymax = max(max(placebo.values()), max(treatment.values()), 0.1)
    y = lambda v: bottom - v / ymax * (bottom - top)  # noqa: E731
    ly = _spread([y(placebo.get(o, 0)) for o in options])
    ry = _spread([y(treatment.get(o, 0)) for o in options])

    marks = (
        f'<line class="grid" x1="{xl}" y1="{top - 8}" x2="{xl}" y2="{bottom + 8}"/>'
        f'<line class="grid" x1="{xr}" y1="{top - 8}" x2="{xr}" y2="{bottom + 8}"/>'
        f'<text class="ink" x="{xl}" y="12" text-anchor="middle">Placebo</text>'
        f'<text class="ink" x="{xr}" y="12" text-anchor="middle">Treatment</text>'
    )
    for i, opt in enumerate(options):
        colour = theme.option_color(i)
        y1, y2 = y(placebo.get(opt, 0)), y(treatment.get(opt, 0))
        length = math.hypot(xr - xl, y2 - y1)
        right = share(treatment.get(opt, 0))
        if effects and opt in effects:
            right += f"  ({points(effects[opt])})"
        marks += (
            f'<line class="ln" x1="{xl}" y1="{y1:.1f}" x2="{xr}" y2="{y2:.1f}" '
            f'style="stroke:{colour};stroke-width:2.5;stroke-dasharray:{length:.1f};'
            f'stroke-dashoffset:{length:.1f};animation-delay:{i * .15:.2f}s"/>'
            f'<circle class="pt-late" cx="{xl}" cy="{y1:.1f}" r="4" fill="{colour}"/>'
            f'<circle class="pt-late" cx="{xr}" cy="{y2:.1f}" r="4" fill="{colour}"/>'
            f'<text class="pt-late" x="{xl - 12}" y="{ly[i] + 4:.1f}" text-anchor="end">'
            f"{esc(opt)}  {share(placebo.get(opt, 0))}</text>"
            f'<text class="ink pt-late" x="{xr + 12}" y="{ry[i] + 4:.1f}">{right}</text>'
        )
    legend = _legend([(theme.option_color(i), o, "") for i, o in enumerate(options)])
    return card(
        f'<svg class="pt-svg" viewBox="0 0 {w} {h}" role="img">{marks}</svg>{legend}',
        "Placebo → treatment: her seçenek nereye kaydı",
        hint=TIPS["arms"],
    )


def turkey_outline() -> tuple[str, int, int]:
    """SVG path data for the Natural Earth outline, plus its viewBox size."""
    geo = json.loads(_TURKEY.read_text(encoding="utf-8"))
    d = "".join("M" + "L".join(f"{x},{y}" for x, y in ring) + "Z" for ring in geo["rings"])
    return d, geo["width"], geo["height"]


def turkey_map(scored: dict | None) -> str:
    """Region directions go here once the contracts carry a region breakdown."""
    d, w, h = turkey_outline()
    has_region = "region" in ((scored or {}).get("subgroup_direction") or {})
    msg = (
        "Bölge yönleri aşağıdaki alt grup kartlarında."
        if has_region
        else "Bu çalıştırmada bölge kırılımı yok. Track B ve Track C bölge düzeyinde sonuç "
        "ürettiğinde bölgeler burada yalnızca yön olarak görünecek. İl düzeyi hiçbir zaman gösterilmez."
    )
    return card(
        '<div class="pt-map">'
        f'<svg class="pt-svg" viewBox="0 0 {w} {h}" role="img"><path d="{d}"/></svg>'
        f'<div class="msg">{esc(msg)}</div></div>',
        "Bölgesel görünüm",
    )


_ARROWS = {"+": ("↑", "up"), "-": ("↓", "down"), "0": ("→", "flat")}


def subgroups(scored: dict | None) -> str:
    """Direction arrows only — never a percentage. Small cells are greyed, not tested."""
    directions = (scored or {}).get("subgroup_direction") or {}
    small = set((scored or {}).get("small_cells") or [])
    blocks = ""
    for dim, cells in directions.items():
        if dim.lower().startswith(HIDDEN_DIMENSIONS):
            continue
        chips = ""
        for i, (cell, sign) in enumerate(cells.items()):
            delay = f'style="animation-delay:{i * .05:.2f}s"'
            if cell in small:
                chips += f'<div class="pt-cell small" {delay}><b>{esc(cell)}</b><span>{SMALL_CELL}</span></div>'
            else:
                arrow, cls = _ARROWS.get(str(sign), ("?", "flat"))
                chips += (
                    f'<div class="pt-cell" {delay}><b>{esc(cell)}</b>'
                    f'<span class="arrow {cls}">{arrow}</span></div>'
                )
        blocks += f'<div class="pt-eyebrow" style="margin-top:6px">{esc(dim)}</div><div class="pt-cells">{chips}</div>'
    if not blocks:
        return ""
    note = '<div class="pt-note">↑ artış · → değişim yok · ↓ azalış. Alt gruplarda yalnızca yön gösterilir.</div>'
    return card(blocks + note, "Alt gruplar — yalnızca yön", hint=TIPS["subgroups"])


# ----------------------------------------------------------- validation views

def _method_label(name: str) -> str:
    return METHOD_LABELS.get(name, name)


def dist_lines(probe: dict) -> str:
    options = probe["options"]
    methods = probe.get("methods") or {}
    series = [(name, m.get("distribution") or {}) for name, m in methods.items()]
    series.append(("real", probe.get("real") or {}))

    w, h, ml, mr, mt, mb = 640, 270, 44, 16, 14, 34
    peak = max((v for _, dist in series for v in dist.values()), default=0.1)
    ymax = max(math.ceil(peak * 5) / 5, 0.2)  # gridlines land on multiples of 5%
    step = (w - ml - mr) / max(len(options) - 1, 1)
    x = lambda i: ml + i * step  # noqa: E731
    y = lambda v: h - mb - v / ymax * (h - mt - mb)  # noqa: E731

    marks = ""
    for g in range(5):
        gv = ymax * g / 4
        marks += (
            f'<line class="grid" x1="{ml}" y1="{y(gv):.1f}" x2="{w - mr}" y2="{y(gv):.1f}"/>'
            f'<text x="{ml - 8}" y="{y(gv) + 4:.1f}" text-anchor="end">{share(gv)}</text>'
        )
    for i, opt in enumerate(options):
        marks += f'<text x="{x(i):.1f}" y="{h - 10}" text-anchor="middle">{esc(opt)}</text>'

    legend = []
    for k, (name, dist) in enumerate(series):
        colour = theme.series_color(name, k)
        pts = [(x(i), y(dist.get(o, 0))) for i, o in enumerate(options)]
        length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        width = 3.2 if name == "real" else 2.2
        marks += (
            f'<polyline class="ln" points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts)}" '
            f'style="stroke:{colour};stroke-width:{width};stroke-dasharray:{length:.1f};'
            f'stroke-dashoffset:{length:.1f};animation-delay:{k * .15:.2f}s"/>'
        )
        if name == "real":
            marks += "".join(
                f'<circle class="pt-late" cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{colour}"/>'
                for px, py in pts
            )
        legend.append((colour, _method_label(name), ""))
    legend.insert(0, legend.pop())  # real first
    return card(
        f'<svg class="pt-svg" viewBox="0 0 {w} {h}" role="img">{marks}</svg>{_legend(legend)}',
        f"Probe · {probe['item']}",
        "Gerçek dağılım ve her yöntemin tahmini",
        hint=TIPS["probe"],
    )


def tvd_bars(probe: dict, noise_floor: float | None) -> str:
    methods = probe.get("methods") or {}
    tvds = {name: m["tvd"] for name, m in methods.items() if m.get("tvd") is not None}
    if not tvds:
        return ""
    full = max(list(tvds.values()) + [noise_floor or 0]) * 1.1 or 1
    floor = f'<div class="floor" style="--f:{noise_floor / full * 100:.1f}%"></div>' if noise_floor else ""
    rows = ""
    for k, (name, tvd) in enumerate(tvds.items()):
        rows += (
            f"<div>{esc(_method_label(name))}</div>"
            f'<div class="trk" style="--w:{tvd / full * 100:.1f}%">'
            f'<div class="bar" style="background:{theme.series_color(name, k)};animation-delay:{k * .1:.1f}s"></div>'
            f'{floor}<span class="v num">{dec(tvd)}</span></div>'
        )
    note = "TVD: gerçek dağılıma uzaklık — düşük olan gerçeğe daha yakın."
    if noise_floor:
        note += f" Kesikli çizgi gürültü tabanı ({dec(noise_floor)})."
    return card(
        f'<div class="pt-tvd">{rows}</div><div class="pt-note num">{note}</div>',
        f"Probe · {probe['item']}",
        "Gerçeğe uzaklık (TVD)",
        hint=TIPS["tvd"],
    )


def rank_table(rank: dict | None) -> str:
    if not rank or not rank.get("methods"):
        return ""
    rows = "".join(
        f'<tr><td>{esc(_method_label(name))}</td><td class="r num">{dec(v)}</td></tr>'
        for name, v in rank["methods"].items()
    )
    return card(
        f'<table class="pt-table"><tr><th>Yöntem</th><th class="r">{esc(rank.get("metric", ""))}</th></tr>'
        f"{rows}</table>"
        f'<div class="pt-note">{esc(rank.get("n_items", "?"))} madde üzerinden. 1 = gerçek sıralamayla '
        "aynı, 0 = ilişkisiz.</div>",
        "Sıralama uyumu",
        "Maddeleri doğru sıraya koyuyor mu?",
        hint=TIPS["rank"],
    )


def models(comparison: dict) -> str:
    """Side-by-side models; disagreement is flagged, never averaged away."""
    probes = comparison.get("probes") or []
    names: list[str] = []
    for p in probes:
        names += [m for m in (p.get("models") or {}) if m not in names]
    scenarios = comparison.get("scenarios") or []

    body = ""
    if len(names) > 1:
        head = "".join(f'<th class="r">{esc(n)}</th>' for n in names)
        rows = ""
        for p in probes:
            cells = "".join(
                f'<td class="r num">{dec(p["models"][n]["tvd"])}</td>' if n in (p.get("models") or {}) else '<td class="r">—</td>'
                for n in names
            )
            rows += f"<tr><td>{esc(p['item'])}</td>{cells}</tr>"
        body += f'<table class="pt-table"><tr><th>Probe (TVD)</th>{head}</tr>{rows}</table>'
    else:
        only = names[0] if names else "bilinmiyor"
        body += f'<div>Tek model: <b>{esc(only)}</b>. Modeller arası karşılaştırma için en az iki model gerekir.</div>'

    if scenarios:
        states = {True: "Uyumlu", False: '<span class="pt-flag">⚠ Modeller ayrışıyor</span>', None: "Ölçülmedi"}
        rows = "".join(
            f"<tr><td>{esc(s['scenario_id'])}</td><td>{states.get(s.get('models_agree'), 'Ölçülmedi')}</td></tr>"
            for s in scenarios
        )
        body += (
            '<table class="pt-table" style="margin-top:14px"><tr><th>Senaryo</th>'
            f"<th>Modeller arası uyum</th></tr>{rows}</table>"
        )
    return card(body, "Modeller", "Modeller aynı şeyi mi söylüyor?", hint=TIPS["models"])


# ---------------------------------------------------------------- run details

def run_details(run: dict) -> str:
    meta = run.get("metadata") or {}
    fields = [
        ("Run", run.get("run_id")),
        ("Tür", run.get("run_type")),
        ("Senaryo", run.get("scenario_id")),
        ("Hedef madde", run.get("target_item")),
        ("Persona sayısı", run.get("n_personas")),
        ("Model", meta.get("model")),
        ("Model snapshot", meta.get("model_snapshot")),
        ("Seed", meta.get("seed")),
        ("persona_set_hash", meta.get("persona_set_hash")),
        ("Seçenek sırası", meta.get("option_order")),
        ("Tur sayısı", meta.get("n_rounds")),
        ("Zaman", meta.get("timestamp")),
    ]
    dl = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in fields if v is not None)

    arms = [a for a in ARM_LABELS if (run["arms"].get(a) or {}).get("option_usage")]
    table = ""
    if arms:
        head = "".join(f'<th class="r">{ARM_LABELS[a]}</th>' for a in arms)
        rows = "".join(
            f"<tr><td>{esc(o)}</td>"
            + "".join(f'<td class="r num">{esc(run["arms"][a]["option_usage"].get(o, 0))}</td>' for a in arms)
            + "</tr>"
            for o in run["options"]
        )
        table = (
            '<div class="pt-eyebrow" style="margin-top:16px">option_usage — her seçenek kaç kez seçildi</div>'
            f'<table class="pt-table"><tr><th>Seçenek</th>{head}</tr>{rows}</table>'
        )
    return f'<div class="pt"><dl class="pt-dl">{dl}</dl>{table}</div>'


# --------------------------------------------------------------- answer texts

def scenario_text(run: dict, scored: dict | None, noise_floor: float | None) -> str:
    sid = run["scenario_id"]
    if scored is None:
        return (
            f"**{sid}** çalıştırılmış ama Track C henüz puanlamamış. Etkiyi ben hesaplamıyorum; "
            "aşağıda yalnızca kolların dağılımı var."
        )
    if not scored.get("measurable"):
        return f"**{sid}** senaryosunda treatment ile placebo arasında gürültünün üstünde ölçülebilir bir etki yok."
    text = f"**{sid}** senaryosunda treatment, placebo'dan gürültü tabanının üstünde ayrışıyor"
    tvd = scored.get("effect_tvd")
    if tvd is not None and noise_floor:
        text += f" (toplam kayma {dec(tvd)}, gürültü tabanı {dec(noise_floor)})"
    text += "."
    effects = scored.get("effect_vs_placebo") or {}
    if effects:
        top = max(effects, key=lambda k: abs(effects[k]))
        text += f" En büyük hareket *{top}* seçeneğinde: {points(effects[top])}."
    return text + " Bu bir fark; nüfustaki mutlak oran değil."


def validation_text(comparison: dict) -> str:
    n = len(comparison.get("probes") or [])
    return (
        f"Güven sorusunun cevabı doğrulama ekranında: {n} probe için gerçek dağılımı, engine'i, "
        "personasız vanilla'yı ve iki baseline'ı yan yana koydum. Engine'in gerçeğe uzaklığı (TVD) "
        "vanilla ve baseline'lardan küçükse persona katmanı işe yarıyor demektir."
    )


def details_text(n: int) -> str:
    return f"{n} çalıştırmanın kaydı aşağıda: model sürümü, seed, persona seti ve seçenek kullanımı."


UNKNOWN_TEXT = (
    "Bu soruya karşılık gelen bir çalıştırma yok ve personalara şu an ulaşılamıyor "
    "(API anahtarı ya da sentetik persona dosyası eksik). Hazır çalıştırmalardan sorabileceklerin:"
)

STANCE_TR = {"OLUMLU": ("Olumlu", "olumlu"), "OLUMSUZ": ("Olumsuz", "olumsuz"), "KARARSIZ": ("Kararsız", "kararsiz")}


def comments_intro(msg: dict) -> str:
    return (
        f"Bu soruyu nüfusa göre ağırlıklı seçilmiş **{msg['n_asked']} sentetik persona** yanıtladı "
        f"({msg['model']}). Her biri kendi profiline göre konuşuyor. Bunlar gerçek kişiler değil; "
        "yorumlar örnek amaçlıdır, *nüfus tahmini değildir*."
    )


def persona_comments(msg: dict) -> str:
    """Synthetic personas' comments: who said it, their stance, what they said. Never a share."""
    shown = msg["comments"]
    dropped = sum(msg["dropped"].values())
    counts = " · ".join(f"{STANCE_TR[s][0]} {n}" for s, n in msg["stances"].items())
    note = f"{counts} — {len(shown)} yorum, oran değil."
    if dropped:
        parts = [f"{n} {label}" for key, label in (("inconsistent", "profiliyle çelişen"), ("unreadable", "okunamayan"),
                                                     ("duplicate", "tekrar eden")) if (n := msg["dropped"][key])]
        note += " Gösterilmeyen: " + ", ".join(parts) + "."
    cards = ""
    for c in shown:
        label, cls = STANCE_TR[c["stance"]]
        who, rest = " · ".join(c["facts"][:3]), c["facts"][3:]
        chips = "".join(f"<span>{esc(f)}</span>" for f in rest)
        cards += (f'<article class="pc"><div class="pc-head"><b>{esc(who)}</b>'
                  f'<span class="pc-stance {cls}">{esc(label)}</span></div>'
                  f'<div class="pc-facts">{chips}</div><p>{esc(c["text"])}</p></article>')
    return (f'<p class="pt-note pc-note">{esc(note)}</p>'
            f'<div class="pc-grid">{cards}</div>')
