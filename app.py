import patch
import streamlit as st
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from database.memory import (
    initialize_db, save_run,
    get_all_runs, get_all_startups,
    get_all_seen_startup_names, clear_memory
)
from export import markdown_to_pdf

st.set_page_config(
    page_title="Together Fund | AI Deal Sourcing",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_db()

st.markdown("""
<style>
.main-header {
    font-size: 2rem;
    font-weight: 700;
    color: #1a1a2e;
}
.sub-header {
    font-size: 0.95rem;
    color: #6b7280;
    margin-bottom: 1.5rem;
}
.memory-pill {
    display: inline-block;
    background: #ede9fe;
    color: #5b21b6;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    margin: 2px;
}
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Together Fund")
    st.markdown("*AI Deal Sourcing Agent*")
    st.divider()

    st.markdown("#### Scan Filters")
    sector = st.selectbox(
        "Sector focus",
        [
            "Any AI sector",
            "B2B SaaS / Dev Tools",
            "FinTech / InsurTech",
            "HealthTech / BioTech",
            "EdTech",
            "AgriTech",
            "Climate / GreenTech",
            "Consumer AI",
            "Enterprise AI Infrastructure"
        ],
    )
    stage = st.selectbox(
        "Stage",
        ["Pre-seed or Seed", "Seed to Series A", "Any stage"],
    )
    geo = st.selectbox(
        "Geography",
        [
            "India or the US",
            "India only",
            "US only (Indian founders)",
            "Global"
        ],
    )

    st.divider()

    # ── MEMORY PANEL ─────────────────────────────────────
    st.markdown("#### Agent Memory")
    seen_names = get_all_seen_startup_names()
    if seen_names:
        st.caption(
            f"{len(seen_names)} startups remembered. "
            f"Agent will find new ones automatically."
        )
        memory_html = "".join(
            f'<span class="memory-pill">{n}</span>'
            for n in seen_names
        )
        st.markdown(memory_html, unsafe_allow_html=True)

        st.markdown("")
        if st.button(
            "Clear Memory",
            type="secondary",
            use_container_width=True,
            help="Wipe history so agent can find previously seen startups again"
        ):
            clear_memory()
            st.success("Memory cleared!")
            st.rerun()
    else:
        st.caption("No startups in memory yet. Run your first scan.")

    st.divider()

    # ── API STATUS ───────────────────────────────────────
    st.markdown("#### API Status")
    groq_key = os.getenv("GROQ_API_KEY", "")
    serper_key = os.getenv("SERPER_API_KEY", "")

    if groq_key and groq_key != "your_groq_key_here":
        st.success("Groq API connected")
    else:
        st.error("Groq API key missing")

    if serper_key and serper_key != "your_serper_key_here":
        st.success("Serper API connected")
    else:
        st.error("Serper API key missing")

    st.divider()
    st.markdown("**Model:** llama-3.3-70b-versatile")
    st.markdown("**Finds:** 1 new startup per scan")
    st.markdown("**Memory:** SQLite (auto-dedup)")

# ── MAIN TABS ────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["New Scan", "Run History", "All Startups"])

with tab1:
    st.markdown(
        '<p class="main-header">Autonomous Deal Sourcing</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p class="sub-header">'
        'Finds 1 new under-the-radar startup per scan. '
        'Never repeats a startup it has already seen.'
        '</p>',
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("This scan finds", "1 startup")
    col2.metric("Total seen so far", len(seen_names))
    col3.metric("Model", "Llama 3.3 70B")

    st.divider()

    can_run = (
        groq_key and groq_key != "your_groq_key_here" and
        serper_key and serper_key != "your_serper_key_here"
    )

    if not can_run:
        st.warning("Add API keys to your .env file to run scans.")

    if seen_names:
        st.info(
            f"Memory active: Agent will skip {len(seen_names)} "
            f"previously seen startup(s) and find something new."
        )

    run_button = st.button(
        "Run Scan — Find 1 New Startup",
        type="primary",
        disabled=not can_run,
        use_container_width=True
    )

    if run_button:
        os.environ["OPENAI_API_KEY"] = groq_key
        os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
        os.environ["OPENAI_MODEL_NAME"] = "llama-3.3-70b-versatile"
        os.environ["SERPER_API_KEY"] = serper_key

        filters = {"sector": sector, "stage": stage, "geo": geo}

        from crew import run_pipeline

        with st.status(
            "Agent scanning for a new startup...",
            expanded=True
        ) as status:
            st.write(f"Sector: **{sector}** | Stage: **{stage}** | Geo: **{geo}**")
            if seen_names:
                st.write(
                    f"Skipping previously seen: "
                    f"{', '.join(seen_names)}"
                )
            st.write("Searching for under-the-radar startup...")
            st.write("This takes 2 to 5 minutes. Please wait...")

            memo_result = None
            error = None

            try:
                memo_result = run_pipeline(filters)
                status.update(
                    label="Scan complete!",
                    state="complete",
                    expanded=False
                )
            except Exception as e:
                error = str(e)
                status.update(label="Error occurred", state="error")

        if error:
            st.error(f"Error: {error}")
            if "429" in error or "rate" in error.lower():
                st.warning(
                    "Groq rate limit hit. "
                    "Wait a few minutes then run again. "
                    "The auto-retry will handle it next time."
                )
            else:
                st.info("Check your API keys in the .env file.")

        elif memo_result:
            st.success("New startup found and analyzed!")
            st.markdown("---")
            st.markdown(memo_result)
            st.markdown("---")

            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button(
                    "Download Memo (.md)",
                    data=memo_result,
                    file_name=(
                        f"memo_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
                    ),
                    mime="text/markdown",
                    use_container_width=True
                )
            with col_b:
                try:
                    pdf_path = (
                        f"memo_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    )
                    markdown_to_pdf(memo_result, pdf_path)
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "Download Memo (.pdf)",
                            data=f.read(),
                            file_name=pdf_path,
                            mime="application/pdf",
                            use_container_width=True
                        )
                except Exception as e:
                    st.warning(f"PDF export unavailable: {e}")

            # Save to memory
            try:
                score_pattern = re.findall(
                    r"###\s+(.+?)\s+-\s+([\d.]+)/10\s+-\s+(.+?)(?:\n|$)",
                    memo_result
                )
                parsed = []
                for name, score, rec in score_pattern:
                    parsed.append({
                        "name": name.strip(),
                        "score": float(score),
                        "recommendation": rec.strip(),
                        "sector": sector,
                        "one_line_summary": ""
                    })
                if parsed:
                    save_run(sector, stage, geo, memo_result, parsed)
                    st.caption(
                        f"Saved to memory. "
                        f"Next scan will find a different startup."
                    )
                    st.rerun()
            except Exception as e:
                st.caption(f"Could not save to memory: {e}")

with tab2:
    st.markdown("### Run History")
    runs = get_all_runs()
    if not runs:
        st.info("No runs yet.")
    else:
        for run in runs:
            ts = run["run_timestamp"][:19].replace("T", " ")
            with st.expander(
                f"{ts} | {run['sector_filter']} | "
                f"{run['total_startups_found']} startup(s)"
            ):
                if run["raw_memo"]:
                    st.markdown(run["raw_memo"])
                    st.download_button(
                        "Download",
                        data=run["raw_memo"],
                        file_name=f"memo_{ts.replace(' ','_')}.md",
                        key=f"dl_{run['id']}"
                    )

with tab3:
    st.markdown("### All Startups Found")
    st.caption(
        "Every startup ever analyzed. "
        "Agent will never find these again unless you clear memory."
    )
    startups = get_all_startups()
    if not startups:
        st.info("No startups yet. Run your first scan.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total found", len(startups))
        scores = [s["score"] for s in startups if s["score"]]
        avg = sum(scores) / len(scores) if scores else 0
        col2.metric("Avg score", f"{avg:.1f}/10")
        fast = sum(
            1 for s in startups
            if "Fast" in (s["recommendation"] or "")
        )
        col3.metric("Fast Track", fast)
        st.divider()

        for s in startups:
            score = s["score"] or 0
            color = (
                "#d1fae5" if score >= 7
                else "#fef3c7" if score >= 5
                else "#fee2e2"
            )
            url = s["website_url"] or "#"
            st.markdown(
                f"**{s['name']}** &nbsp;|&nbsp;"
                f"<span style='background:{color};"
                f"padding:2px 8px;border-radius:10px'>"
                f"{score:.1f}/10</span> &nbsp;"
                f"{s['recommendation'] or ''} &nbsp;|&nbsp;"
                f"{s['sector'] or ''} &nbsp;|&nbsp;"
                f"[website]({url})",
                unsafe_allow_html=True
            )