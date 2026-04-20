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
    get_all_seen_startup_names, clear_memory,
    create_user, verify_user, update_user_rating
)
from confidence import (
    calculate_confidence, confidence_label, confidence_color
)
from export import markdown_to_pdf

st.set_page_config(
    page_title="Together Fund | AI Deal Sourcing",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_db()

# ── SESSION STATE ─────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None

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
.conf-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# ── AUTH SCREEN ───────────────────────────────────────────
def show_auth():
    st.markdown(
        '<p class="main-header" style="text-align:center">'
        'Together Fund</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p class="sub-header" style="text-align:center">'
        'AI Deal Sourcing Agent — Sign in to continue'
        '</p>',
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        mode = st.radio(
            "Mode",
            ["Login", "Create Account"],
            horizontal=True,
            label_visibility="collapsed"
        )
        st.markdown("---")

        if mode == "Login":
            st.markdown("#### Sign in")
            username = st.text_input(
                "Username", placeholder="Enter username"
            )
            password = st.text_input(
                "Password", type="password",
                placeholder="Enter password"
            )
            if st.button(
                "Sign In", type="primary",
                use_container_width=True
            ):
                if username and password:
                    user = verify_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                else:
                    st.warning("Please fill in both fields.")

        else:
            st.markdown("#### Create account")
            full_name = st.text_input(
                "Full name", placeholder="Your full name"
            )
            username = st.text_input(
                "Username", placeholder="Choose a username"
            )
            password = st.text_input(
                "Password", type="password",
                placeholder="Min 6 characters"
            )
            password2 = st.text_input(
                "Confirm password", type="password",
                placeholder="Repeat password"
            )
            if st.button(
                "Create Account", type="primary",
                use_container_width=True
            ):
                if not all([full_name, username, password, password2]):
                    st.warning("Please fill in all fields.")
                elif len(password) < 6:
                    st.warning("Password must be at least 6 characters.")
                elif password != password2:
                    st.error("Passwords do not match.")
                else:
                    ok = create_user(username, password, full_name)
                    if ok:
                        st.success("Account created! Please sign in.")
                    else:
                        st.error("Username already taken.")


# ── MAIN APP ──────────────────────────────────────────────
def show_app():
    user = st.session_state.user

    groq_key = os.getenv("GROQ_API_KEY", "")
    serper_key = os.getenv("SERPER_API_KEY", "")
    seen_names = get_all_seen_startup_names()

    # ── SIDEBAR — exactly as before + sign out ────────────
    with st.sidebar:
        st.markdown("### Together Fund")
        st.markdown(f"*Signed in as **{user['full_name']}***")
        if st.button("Sign Out", use_container_width=True):
            st.session_state.user = None
            st.rerun()
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

        # Memory panel — exactly as before
        st.markdown("#### Agent Memory")
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
                help="Wipe history so agent can find these again"
            ):
                clear_memory()
                st.success("Memory cleared!")
                st.rerun()
        else:
            st.caption("No startups in memory yet.")

        st.divider()

        # API status — exactly as before
        st.markdown("#### API Status")
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

    # ── TABS — original 3 + 2 new ones ───────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "New Scan",
        "Comparison View",
        "Run History",
        "All Startups",
        "My Ratings"
    ])

    # ── TAB 1: NEW SCAN — exactly as before ───────────────
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
            os.environ["OPENAI_API_BASE"] = (
                "https://api.groq.com/openai/v1"
            )
            os.environ["OPENAI_MODEL_NAME"] = "llama-3.3-70b-versatile"
            os.environ["SERPER_API_KEY"] = serper_key

            filters = {"sector": sector, "stage": stage, "geo": geo}

            from crew import run_pipeline

            with st.status(
                "Agent scanning for a new startup...",
                expanded=True
            ) as status:
                st.write(
                    f"Sector: **{sector}** | "
                    f"Stage: **{stage}** | Geo: **{geo}**"
                )
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
                    status.update(
                        label="Error occurred", state="error"
                    )

            if error:
                st.error(f"Error: {error}")
                if "429" in error or "rate" in error.lower():
                    st.warning(
                        "Groq rate limit hit. "
                        "Wait a few minutes then run again."
                    )
                else:
                    st.info("Check your API keys in the .env file.")

            elif memo_result:
                st.success("New startup found and analyzed!")
                st.markdown("---")
                st.markdown(memo_result)

                # ── Confidence score — new addition ───────
                score_pattern = re.findall(
                    r"###\s+(.+?)\s+-\s+([\d.]+)/10\s+-\s+(.+?)(?:\n|$)",
                    memo_result
                )

                url_match = re.search(
                    r"\*\*Website:\*\*\s*(https?://\S+)",
                    memo_result
                )
                founders_match = re.search(
                    r"\*\*Founders:\*\*\s*(.+?)\s*\|",
                    memo_result
                )
                arch_match = re.search(
                    r"\*\*AI Architecture:\*\*\s*(.+?)(?:\n|$)",
                    memo_result
                )
                hq_match = re.search(
                    r"\*\*HQ:\*\*\s*(.+?)\s*\|",
                    memo_result
                )
                year_match = re.search(
                    r"\*\*Founded:\*\*\s*(\d{4})",
                    memo_result
                )
                scrape_ok = (
                    "Website scrape: SUCCESS" in memo_result or
                    "successfully scraped" in memo_result.lower()
                )

                startup_data_for_conf = {
                    "website_url": (
                        url_match.group(1) if url_match else ""
                    ),
                    "founders": (
                        founders_match.group(1)
                        if founders_match else ""
                    ),
                    "ai_architecture": (
                        arch_match.group(1) if arch_match else ""
                    ),
                    "hq_location": (
                        hq_match.group(1) if hq_match else ""
                    ),
                    "founded_year": (
                        year_match.group(1) if year_match else ""
                    ),
                    "scrape_succeeded": scrape_ok,
                    "competitors": memo_result,
                }

                conf_score, conf_breakdown = calculate_confidence(
                    startup_data_for_conf
                )
                conf_lbl = confidence_label(conf_score)
                conf_col = confidence_color(conf_score)

                st.markdown("---")
                st.markdown("#### Analysis Confidence Score")
                st.markdown(
                    f"<span class='conf-badge' "
                    f"style='background:{conf_col}'>"
                    f"{conf_score}/10 — {conf_lbl} Confidence"
                    f"</span>",
                    unsafe_allow_html=True
                )
                st.caption(f"Breakdown: {conf_breakdown}")
                st.caption(
                    "Confidence measures how much data came from "
                    "real scraped sources vs model inference."
                )

                st.markdown("---")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.download_button(
                        "Download Memo (.md)",
                        data=memo_result,
                        file_name=(
                            f"memo_"
                            f"{datetime.now().strftime('%Y%m%d_%H%M')}"
                            f".md"
                        ),
                        mime="text/markdown",
                        use_container_width=True
                    )
                with col_b:
                    try:
                        pdf_path = (
                            f"memo_"
                            f"{datetime.now().strftime('%Y%m%d_%H%M')}"
                            f".pdf"
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

                # Save to memory — same as before + new fields
                try:
                    parsed = []
                    for name, score, rec in score_pattern:
                        parsed.append({
                            "name": name.strip(),
                            "score": float(score),
                            "recommendation": rec.strip(),
                            "sector": sector,
                            "one_line_summary": "",
                            "website_url": (
                                url_match.group(1)
                                if url_match else ""
                            ),
                            "founders": (
                                founders_match.group(1)
                                if founders_match else ""
                            ),
                            "hq_location": (
                                hq_match.group(1)
                                if hq_match else ""
                            ),
                            "founded_year": (
                                year_match.group(1)
                                if year_match else ""
                            ),
                            "ai_architecture": (
                                arch_match.group(1)
                                if arch_match else ""
                            ),
                            "competitors": "",
                            "confidence_score": conf_score,
                            "confidence_breakdown": conf_breakdown,
                        })
                    if parsed:
                        save_run(
                            sector, stage, geo,
                            memo_result, parsed
                        )
                        st.caption(
                            "Saved to memory. "
                            "Next scan will find a different startup."
                        )
                        st.rerun()
                except Exception as e:
                    st.caption(f"Could not save to memory: {e}")

    # ── TAB 2: COMPARISON VIEW — new ──────────────────────
    with tab2:
        st.markdown("### Startup Comparison")
        st.caption(
            "All startups analyzed so far, side by side. "
            "Filter and sort to compare."
        )

        all_startups = get_all_startups()

        if not all_startups:
            st.info(
                "No startups yet. "
                "Run your first scan in the New Scan tab."
            )
        else:
            # Filter and sort controls
            cf1, cf2, cf3 = st.columns(3)
            with cf1:
                filter_rec = st.selectbox(
                    "Filter by recommendation",
                    ["All", "Fast Track", "Take Meeting", "Pass"],
                    key="comp_filter_rec"
                )
            with cf2:
                sectors_available = list(set(
                    s["sector"] for s in all_startups if s["sector"]
                ))
                filter_sector = st.selectbox(
                    "Filter by sector",
                    ["All"] + sectors_available,
                    key="comp_filter_sector"
                )
            with cf3:
                sort_by = st.selectbox(
                    "Sort by",
                    [
                        "Score (high to low)",
                        "Score (low to high)",
                        "Confidence (high to low)",
                        "Name (A-Z)"
                    ],
                    key="comp_sort"
                )

            filtered = all_startups
            if filter_rec != "All":
                filtered = [
                    s for s in filtered
                    if filter_rec in (s["recommendation"] or "")
                ]
            if filter_sector != "All":
                filtered = [
                    s for s in filtered
                    if s["sector"] == filter_sector
                ]

            if sort_by == "Score (high to low)":
                filtered = sorted(
                    filtered,
                    key=lambda x: x["score"] or 0,
                    reverse=True
                )
            elif sort_by == "Score (low to high)":
                filtered = sorted(
                    filtered, key=lambda x: x["score"] or 0
                )
            elif sort_by == "Confidence (high to low)":
                filtered = sorted(
                    filtered,
                    key=lambda x: x.get("confidence_score") or 0,
                    reverse=True
                )
            elif sort_by == "Name (A-Z)":
                filtered = sorted(
                    filtered, key=lambda x: x["name"]
                )

            # Summary row
            if filtered:
                scores = [s["score"] for s in filtered if s["score"]]
                avg_s = sum(scores) / len(scores) if scores else 0
                confs = [
                    s.get("confidence_score") or 0
                    for s in filtered
                ]
                avg_c = sum(confs) / len(confs) if confs else 0
                fast = sum(
                    1 for s in filtered
                    if "Fast" in (s["recommendation"] or "")
                )
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Showing", len(filtered))
                m2.metric("Avg Score", f"{avg_s:.1f}/10")
                m3.metric("Avg Confidence", f"{avg_c:.1f}/10")
                m4.metric("Fast Track", fast)

            st.divider()

            # 2-column card grid
            for i in range(0, len(filtered), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j >= len(filtered):
                        break
                    s = filtered[i + j]
                    score = s["score"] or 0
                    conf = s.get("confidence_score") or 0
                    rec = s["recommendation"] or "—"
                    score_bg = (
                        "#d1fae5" if score >= 7
                        else "#fef3c7" if score >= 5
                        else "#fee2e2"
                    )
                    conf_bg = confidence_color(conf)

                    with col:
                        with st.container(border=True):
                            st.markdown(f"#### {s['name']}")
                            r1, r2 = st.columns(2)
                            r1.markdown(
                                f"<span style='background:{score_bg};"
                                f"padding:3px 10px;"
                                f"border-radius:10px;"
                                f"font-weight:600'>"
                                f"Score: {score:.1f}/10</span>",
                                unsafe_allow_html=True
                            )
                            r2.markdown(
                                f"<span style='background:{conf_bg};"
                                f"padding:3px 10px;"
                                f"border-radius:10px'>"
                                f"Conf: {conf:.1f}/10</span>",
                                unsafe_allow_html=True
                            )
                            st.markdown(
                                f"**Rec:** {rec}  \n"
                                f"**Sector:** {s['sector'] or '—'}  \n"
                                f"**Founded:** "
                                f"{s.get('founded_year') or '—'}  \n"
                                f"**HQ:** {s['hq_location'] or '—'}"
                            )
                            if s.get("website_url"):
                                st.markdown(
                                    f"[Visit website]"
                                    f"({s['website_url']})"
                                )
                            if s.get("ai_architecture"):
                                arch = s["ai_architecture"]
                                st.caption(
                                    f"AI: {arch[:80]}"
                                    f"{'...' if len(arch) > 80 else ''}"
                                )

    # ── TAB 3: RUN HISTORY — exactly as before ────────────
    with tab3:
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
                            file_name=(
                                f"memo_"
                                f"{ts.replace(' ','_')}.md"
                            ),
                            key=f"dl_{run['id']}"
                        )

    # ── TAB 4: ALL STARTUPS — exactly as before ───────────
    with tab4:
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
                conf = s.get("confidence_score") or 0
                color = (
                    "#d1fae5" if score >= 7
                    else "#fef3c7" if score >= 5
                    else "#fee2e2"
                )
                conf_col = confidence_color(conf)
                url = s["website_url"] or "#"
                st.markdown(
                    f"**{s['name']}** &nbsp;|&nbsp;"
                    f"<span style='background:{color};"
                    f"padding:2px 8px;border-radius:10px'>"
                    f"{score:.1f}/10</span> &nbsp;"
                    f"<span style='background:{conf_col};"
                    f"padding:2px 8px;border-radius:10px'>"
                    f"Conf:{conf:.1f}</span> &nbsp;"
                    f"{s['recommendation'] or ''} &nbsp;|&nbsp;"
                    f"{s['sector'] or ''} &nbsp;|&nbsp;"
                    f"[website]({url})",
                    unsafe_allow_html=True
                )

    # ── TAB 5: MY RATINGS — new ───────────────────────────
    with tab5:
        st.markdown("### Rate Startups")
        st.caption(
            "Rate each startup by relevance. "
            "Helps you track which ones are worth following up."
        )
        startups = get_all_startups()
        if not startups:
            st.info("No startups to rate yet.")
        else:
            for s in startups:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        score = s["score"] or 0
                        color = (
                            "#d1fae5" if score >= 7
                            else "#fef3c7" if score >= 5
                            else "#fee2e2"
                        )
                        st.markdown(
                            f"**{s['name']}** &nbsp;"
                            f"<span style='background:{color};"
                            f"padding:2px 8px;border-radius:10px'>"
                            f"{score:.1f}/10</span>",
                            unsafe_allow_html=True
                        )
                        st.caption(
                            f"{s['recommendation'] or '—'} | "
                            f"{s['sector'] or '—'}"
                        )
                    with c2:
                        current_rating = s.get("user_rating") or 3
                        new_rating = st.select_slider(
                            "Relevance",
                            options=[1, 2, 3, 4, 5],
                            value=current_rating,
                            key=f"rate_{s['id']}",
                            help=(
                                "1 = not relevant, "
                                "5 = very relevant"
                            )
                        )
                        if new_rating != current_rating:
                            update_user_rating(s["id"], new_rating)
                            st.caption("Saved.")


# ── ROUTER ────────────────────────────────────────────────
if st.session_state.user is None:
    show_auth()
else:
    show_app()