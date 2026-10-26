import re
import sys
import time
from contextlib import redirect_stdout

import streamlit as st

from src.pipelines.pipeline import run_research_pipeline

st.set_page_config(
    page_title="Multi-Agent Research System",
    page_icon="🔎",
    layout="wide",
)

# ---------------------------------------------------------------
# Styling (works in light and dark themes)
# ---------------------------------------------------------------
st.markdown(
    """
<style>
.block-container {padding-top: 2.2rem; max-width: 1100px;}
.hero h1 {font-size: 2.3rem; margin: 0 0 .2rem 0; letter-spacing: -0.02em;}
.hero p {opacity: .7; margin: 0 0 1.2rem 0; font-size: 1.05rem;}

.steps {display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 1.2rem 0 1.6rem;}
@media (max-width: 800px) {.steps {grid-template-columns: repeat(2, 1fr);}}
.step {
    border: 1px solid rgba(128,128,128,.28);
    border-radius: 14px;
    padding: 14px 16px;
    background: rgba(128,128,128,.06);
    transition: all .2s ease;
}
.step .num {font-size: .7rem; opacity: .55; letter-spacing: .08em; text-transform: uppercase;}
.step .name {font-weight: 650; font-size: 1.05rem; margin-top: 2px;}
.step .state {font-size: .82rem; margin-top: 6px; opacity: .65;}
.step.active {border-color: #6366f1; background: rgba(99,102,241,.13);}
.step.active .state {color: #6366f1; opacity: 1; font-weight: 600;}
.step.done {border-color: #22c55e; background: rgba(34,197,94,.10);}
.step.done .state {color: #22c55e; opacity: 1; font-weight: 600;}

div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 12px;
    padding: 12px 16px;
    background: rgba(128,128,128,.05);
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
STEPS = [
    ("Search", "Finds sources on the web"),
    ("Read", "Scrapes the best page"),
    ("Write", "Drafts the report"),
    ("Review", "Critic scores it"),
]

EXAMPLES = [
    "Latest advances in edge AI chips",
    "How LoRA fine-tuning works",
    "Solar power adoption in Kenya",
]


def steps_html(current: int, finished: bool = False) -> str:
    """Build the 4-card progress tracker. current: 0 = not started, 1-4 = running step."""
    cards = []
    for i, (name, desc) in enumerate(STEPS, start=1):
        if finished or i < current:
            cls, text = "done", "Done"
        elif i == current:
            cls, text = "active", "Working..."
        else:
            cls, text = "", desc
        cards.append(
            f'<div class="step {cls}"><div class="num">Step {i}</div>'
            f'<div class="name">{name}</div><div class="state">{text}</div></div>'
        )
    return '<div class="steps">' + "".join(cards) + "</div>"


def clean(text: str) -> str:
    """Remove <think> blocks that some models write before the answer."""
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


def extract_urls(text: str) -> list:
    found = re.findall(r"https?://[^\s)>\]\"']+", text or "")
    seen, urls = set(), []
    for u in found:
        u = u.rstrip(".,;:")
        if u not in seen:
            seen.add(u)
            urls.append(u)
    return urls


class LiveLog:
    """Catches the pipeline's print() output, watches for step messages,
    and still passes everything through to the terminal."""

    def __init__(self, on_step):
        self.on_step = on_step
        self.original = sys.stdout

    def write(self, text):
        self.original.write(text)
        m = re.match(r"\s*step\s*(\d)\s*(?:of\s*\d+\s*)?-", text, re.I)
        if m:
            self.on_step(int(m.group(1)))
        return len(text)

    def flush(self):
        self.original.flush()


def set_topic(value: str):
    st.session_state["topic_input"] = value


# ---------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------
with st.sidebar:
    st.header("How it works")
    st.markdown(
        "**1. Search** - an agent finds recent sources\n\n"
        "**2. Read** - an agent opens the best page\n\n"
        "**3. Write** - a writer drafts a structured report\n\n"
        "**4. Review** - a critic scores and critiques it"
    )
    st.divider()
    st.caption(
        "A run takes a few minutes on the free Groq tier. If you hit a rate "
        "limit error, wait a minute and run again."
    )
    if st.button("Clear results", use_container_width=True):
        for key in ("result", "topic", "elapsed"):
            st.session_state.pop(key, None)
        st.rerun()

# ---------------------------------------------------------------
# Header and input
# ---------------------------------------------------------------
st.markdown(
    '<div class="hero"><h1>Multi-Agent Research System</h1>'
    "<p>Enter a topic. Four agents search, read, write and review.</p></div>",
    unsafe_allow_html=True,
)

if "topic_input" not in st.session_state:
    st.session_state["topic_input"] = ""

with st.form("research_form", border=False):
    c1, c2 = st.columns([5, 1])
    topic = c1.text_input(
        "Research topic",
        key="topic_input",
        placeholder="e.g. Latest advances in edge AI chips",
        label_visibility="collapsed",
    )
    submitted = c2.form_submit_button("Run research", type="primary", use_container_width=True)

st.caption("Try an example:")
cols = st.columns(len(EXAMPLES))
for col, example in zip(cols, EXAMPLES):
    col.button(example, on_click=set_topic, args=(example,), use_container_width=True)

# ---------------------------------------------------------------
# Progress tracker + run
# ---------------------------------------------------------------
tracker = st.empty()
has_result = "result" in st.session_state

if has_result and not submitted:
    tracker.markdown(steps_html(4, finished=True), unsafe_allow_html=True)
else:
    tracker.markdown(steps_html(0), unsafe_allow_html=True)

if submitted:
    if not topic.strip():
        st.warning("Type a topic first.")
    else:
        st.session_state.pop("result", None)
        current = {"step": 0}

        def on_step(n: int):
            if n > current["step"]:
                current["step"] = n
                tracker.markdown(steps_html(n), unsafe_allow_html=True)

        tracker.markdown(steps_html(1), unsafe_allow_html=True)
        current["step"] = 1
        start = time.time()

        try:
            with st.spinner("Agents are working..."):
                with redirect_stdout(LiveLog(on_step)):
                    result = run_research_pipeline(topic.strip())

            st.session_state["result"] = result
            st.session_state["topic"] = topic.strip()
            st.session_state["elapsed"] = time.time() - start
            tracker.markdown(steps_html(4, finished=True), unsafe_allow_html=True)

        except Exception as e:
            msg = str(e)
            if any(k in msg for k in ("413", "429", "rate_limit")):
                st.error(
                    "Groq rate limit reached. Wait a minute and run again. "
                    "If it keeps happening, add a time.sleep() pause between steps in your pipeline."
                )
            else:
                st.error(f"Something went wrong: {msg}")

# ---------------------------------------------------------------
# Results
# ---------------------------------------------------------------
result = st.session_state.get("result")

if result:
    report = clean(result.get("report", ""))
    feedback = clean(result.get("feedback", ""))
    search_results = clean(result.get("search_results", ""))
    scraped = clean(result.get("scraped_content", ""))

    score_match = re.search(r"score:\s*\**\s*(\d+(?:\.\d+)?)\s*/\s*10", feedback, re.I)
    urls = extract_urls(report + "\n" + search_results)
    elapsed = st.session_state.get("elapsed", 0)

    st.subheader(st.session_state.get("topic", "Results"))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Critic score", f"{score_match.group(1)}/10" if score_match else "n/a")
    m2.metric("Time taken", f"{elapsed:.0f}s")
    m3.metric("Sources found", len(urls))
    m4.metric("Report length", f"{len(report.split())} words")

    tab_report, tab_review, tab_sources, tab_raw = st.tabs(
        ["Report", "Critic review", "Sources", "Raw research"]
    )

    with tab_report:
        st.markdown(report)
        st.download_button(
            "Download report (.md)",
            data=report,
            file_name="research_report.md",
            mime="text/markdown",
        )

    with tab_review:
        st.markdown(feedback)

    with tab_sources:
        if urls:
            for u in urls:
                st.markdown(f"- [{u}]({u})")
        else:
            st.write("No links found.")

    with tab_raw:
        with st.expander("Search agent output", expanded=False):
            st.markdown(search_results)
        with st.expander("Reader agent output", expanded=False):
            st.markdown(scraped)