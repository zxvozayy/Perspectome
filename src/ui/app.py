"""Perspectome dashboard (Track D). Run from this folder so the theme loads:

    cd src/ui && streamlit run app.py
"""

from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ui import answers, hero, store, theme, views  # noqa: E402
from src.ui.data import Bundle, load  # noqa: E402

CHART_VIEWS = ("Çubuk", "Nokta", "Eğim", "Harita")

st.set_page_config(page_title="Perspectome", page_icon=":material/groups:", layout="centered")
st.html(theme.CSS)

bundle = load()
ss = st.session_state
ss.setdefault("screen", "intro")
ss.setdefault("chats", store.load())  # newest first
ss.setdefault("current", None)  # id of the open chat; None = a new, empty one


def open_chat() -> dict | None:
    return next((c for c in ss.chats if c["id"] == ss.current), None)


def show(block: str) -> None:
    # st.html strips inline SVG; raw-HTML markdown keeps it.
    if block:
        st.markdown(block, unsafe_allow_html=True)


def ask(question: str) -> None:
    chat = open_chat()
    if chat is None:
        chat = {
            "id": uuid.uuid4().hex,
            "title": question[:60],
            "created": datetime.now().isoformat(timespec="minutes"),
            "messages": [],
        }
        ss.chats.insert(0, chat)
        ss.current = chat["id"]
    chat["messages"].append({"role": "user", "text": question})
    chat["messages"].append({"role": "assistant", "fresh": True, **answers.route(question, bundle)})
    store.save(ss.chats)


def chips(labels: list[str], key: str) -> None:
    cols = st.columns(len(labels)) if labels else []
    for col, label in zip(cols, labels):
        if col.button(label, key=f"{key}-{label}", use_container_width=True):
            ask(label)
            st.rerun()


def say(text: str, fresh: bool) -> None:
    """Assistant prose; streamed word by word the first time it appears."""
    if not fresh:
        st.markdown(text)
        return
    dots = st.empty()
    dots.markdown(views.typing(), unsafe_allow_html=True)
    time.sleep(0.6)
    dots.empty()

    def words():
        for word in text.split(" "):
            yield word + " "
            time.sleep(0.025)

    st.write_stream(words)


def details_expander(run: dict, expanded: bool = False) -> None:
    with st.expander(f"Çalıştırma detayı · {run['run_id']}", expanded=expanded):
        show(views.run_details(run))


def scenario_answer(i: str, msg: dict, bundle: Bundle, fresh: bool) -> None:
    run = bundle.results.get(msg["run_id"])
    if run is None:
        say("Bu çalıştırma artık veri klasöründe yok.", fresh)
        return
    scored = bundle.scored(run["scenario_id"])
    noise = (bundle.comparison or {}).get("noise_floor_tvd")
    say(views.scenario_text(run, scored, noise), fresh)
    show(views.warnings(bundle.warnings, scenario_caveat=True))
    show(views.effect_headline(scored, noise))

    view = st.segmented_control(
        "Grafik türü", CHART_VIEWS, default=CHART_VIEWS[0], key=f"view-{i}", label_visibility="collapsed"
    )
    if view == "Nokta":
        show(views.arm_dots(run))
    elif view == "Eğim":
        show(views.slope(run, scored))
    elif view == "Harita":
        show(views.turkey_map(scored))
    else:
        show(views.arm_bars(run))

    show(views.subgroups(scored))
    details_expander(run)
    show(views.footnote())


def validation_answer(msg: dict, bundle: Bundle, fresh: bool) -> None:
    comparison = bundle.comparison
    if not comparison:
        say("Track C'nin karşılaştırma raporu henüz yok.", fresh)
        return
    say(views.validation_text(comparison), fresh)
    show(views.warnings(bundle.warnings))
    noise = comparison.get("noise_floor_tvd")
    for probe in comparison.get("probes") or []:
        show(views.dist_lines(probe))
        show(views.tvd_bars(probe, noise))
        for run in bundle.runs("probe"):
            if run.get("target_item") == probe["item"]:
                details_expander(run)
    show(views.rank_table(comparison.get("rank_agreement")))
    show(views.models(comparison))
    show(views.footnote())


def details_answer(msg: dict, bundle: Bundle, fresh: bool) -> None:
    runs = [bundle.results[r] for r in msg["run_ids"] if r in bundle.results]
    say(views.details_text(len(runs)), fresh)
    for run in runs:
        details_expander(run, expanded=len(runs) == 1)


def render(i: str, msg: dict, last: bool) -> None:
    if msg["role"] == "user":
        show(views.user_bubble(msg["text"]))
        return
    fresh = msg.pop("fresh", False)
    show(views.assistant_label())
    kind = msg["kind"]
    if kind == "scenario":
        scenario_answer(i, msg, bundle, fresh)
        if last and bundle.comparison:
            chips([answers.VALIDATION_QUESTION], key=f"next-{i}")
    elif kind == "validation":
        validation_answer(msg, bundle, fresh)
    elif kind == "details":
        details_answer(msg, bundle, fresh)
    else:
        say(views.UNKNOWN_TEXT, fresh)
        if last:
            chips(answers.suggestions(bundle), key=f"unknown-{i}")


# ------------------------------------------------------------------ intro

if ss.screen == "intro":
    # Black page, no margins: the intro's glow fades into it, so no frame shows around the scene.
    st.html(
        "<style>.stApp { background: #000; } "
        'header[data-testid="stHeader"] { display: none; } '
        ".block-container { max-width: none; padding: 0 0 2rem; } "
        '[data-testid="stHorizontalBlock"] { padding: 0 20px; } '
        # The frame grows with the window; its wrapper must grow with it, or the button would ride up over the title.
        "iframe, div:has(> iframe) { height: max(500px, calc(100vh - 150px)) !important; }</style>"
    )
    # The title lives inside the intro's frame and the button below it, so the two can never overlap.
    components.html(hero.html(), height=640)
    _, mid, _ = st.columns([2, 1, 2])
    if mid.button("Analiz et", type="primary", use_container_width=True):
        ss.screen, ss.current = "chat", None
        st.rerun()
    st.stop()

# ------------------------------------------------------------------- chat

prompt = st.chat_input("Fikrini dinliyorum…")
if prompt:
    ask(prompt)

with st.sidebar:
    if st.button("＋  Yeni sohbet", key="new-chat", use_container_width=True):
        ss.current = None
        st.rerun()
    show(views.panel_heading("Geçmiş sohbetler"))
    if not ss.chats:
        st.caption("Henüz sohbet yok.")
    for chat in ss.chats:
        kind = "primary" if chat["id"] == ss.current else "secondary"
        if st.button(chat["title"], key=f"chat-{chat['id']}", type=kind, use_container_width=True):
            ss.current = chat["id"]
            st.rerun()
    show(views.panel_heading(""))
    if st.button("←  Tanıtım ekranı", key="to-intro", use_container_width=True):
        ss.screen = "intro"
        st.rerun()

chat = open_chat()
if chat is None:
    show(views.listening())
    chips(answers.suggestions(bundle), key="start")
else:
    show(views.top_bar(bundle.is_fixture, chat["title"]))
    messages = chat["messages"]
    for i, msg in enumerate(messages):
        render(f"{chat['id']}-{i}", msg, last=i == len(messages) - 1)
