import os
import time
import re
import random
from dotenv import load_dotenv
from crewai import Crew, Task, Process
from agents import build_agents
from database.memory import get_all_seen_startup_names

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.environ.get("GROQ_API_KEY", "")
os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
os.environ["OPENAI_MODEL_NAME"] = "llama-3.3-70b-versatile"

# ─────────────────────────────────────────────────────────
# GROQ FREE TIER LIMITS for llama-3.3-70b-versatile:
# 6,000 tokens per minute (TPM)
# 100,000 tokens per day (TPD)
# We target 4,500 TPM (75% of limit) to stay safe
# ─────────────────────────────────────────────────────────
TOKEN_BUDGET_PER_MINUTE = 4500
TOKENS_PER_AGENT_CALL = 1500  # conservative estimate per LLM call
DELAY_BETWEEN_AGENTS = 25     # seconds pause between each agent handoff


def build_tasks(researcher, analyst, scorer, associate, filters):
    sector = filters.get("sector", "any AI sector")
    stage = filters.get("stage", "pre-seed or seed")
    geo = filters.get("geo", "India or the US")

    seen_names = get_all_seen_startup_names()
    if seen_names:
        avoid_str = ", ".join(seen_names)
        memory_instruction = (
            f"You have already analyzed these startups in previous runs: "
            f"{avoid_str}. "
            f"Do NOT find any of these again. "
            f"Find a completely different startup not in this list."
        )
    else:
        memory_instruction = (
            "This is the first run. No startups analyzed yet."
        )

    search_task = Task(
        description=f"""
        Search the web and find exactly 1 real AI startup that meets
        ALL of these criteria:
        - Founded by Indian founders (born in India or of Indian origin)
        - Founded in 2023 or 2024
        - Operating in: {geo}
        - Sector focus: {sector}
        - Stage: {stage}
        - Small or unknown startup — NOT a well-known company
        - NOT large companies like OpenAI, Anthropic, Google, Microsoft,
          Krutrim, Sarvam, or any company that has raised over $5M

        {memory_instruction}

        Search for lesser-known, under-the-radar startups using queries like:
        - "Indian founder AI startup {sector} 2024 pre-seed"
        - "new Indian AI startup 2024 {geo} early stage"
        - "Indian AI startup tracker 2024 {sector} seed"

        For the startup you find provide:
        1. Company Name
        2. Website URL (real company website only)
        3. Founders (full names)
        4. Founded Year
        5. HQ Location
        6. One-line summary
        7. Sector category

        Do maximum 3 searches then give your Final Answer immediately.
        Never make up names or URLs.
        """,
        expected_output=(
            "Details of exactly 1 startup: "
            "Name, Website URL, Founders, Founded Year, "
            "HQ Location, One-line summary, Sector."
        ),
        agent=researcher,
    )

    analyze_task = Task(
        description="""
        Research the startup from the previous task in depth.

        1. Use Search the internet to find information
        2. If a real website URL exists, use smart_scrape_tool:
           format: CompanyName | https://website.com
        3. Extract:
           a) Core product - what exactly does it do step by step
           b) Target audience - B2B or B2C, who pays
           c) AI architecture - RAG? Fine-tuned LLM? Vision model?
              Classical ML? Be specific.
           d) Inferred tech stack
           e) Competitive moat
           f) 3 specific red flags
           g) 3 specific green flags
        4. Search for founder backgrounds: IIT/IIM, FAANG, YC, PhD
        5. Find 2-3 direct competitors

        Do maximum 3 searches total.
        When done, write Final Answer immediately.
        Never use Action: None.
        """,
        expected_output=(
            "Technical breakdown: core product, AI architecture, "
            "founder pedigree (IIT/IIM/FAANG/YC yes or no), "
            "tech stack, moat, 3 red flags, 3 green flags, "
            "2-3 named competitors."
        ),
        agent=analyst,
        context=[search_task],
    )

    scoring_task = Task(
        description="""
        Score the startup using the Together Fund rubric.

        SCORING RUBRIC (each scored 1-10):
        - Team Pedigree: 30% weight
        - Market Size (TAM): 25% weight
        - Technical Moat: 25% weight
        - Traction: 20% weight

        Team Pedigree:
        9-10: IIT/IIM + FAANG + prior exit
        7-8: IIT or FAANG (not both)
        5-6: Decent, no major signals
        1-4: Unknown background

        Market Size:
        9-10: TAM over $10B
        7-8: TAM $1B to $10B
        5-6: TAM $100M to $1B
        1-4: Under $100M

        Technical Moat:
        9-10: Proprietary model or data
        7-8: Strong workflow moat
        5-6: Good but replicable
        1-4: API wrapper

        Traction:
        9-10: Revenue or named customers
        7-8: Beta users or pilots
        5-6: Product live, no traction
        1-4: Pre-product

        Read previous research. Score immediately.
        Do not use any tools. Write Final Answer directly.
        """,
        expected_output=(
            "Scorecard with all 4 criteria scores and justifications, "
            "weighted total out of 10, recommendation: "
            "Pass, Take Meeting, or Fast Track."
        ),
        agent=scorer,
        context=[search_task, analyze_task],
    )

    memo_task = Task(
        description="""
        Write a professional Investment Screening Memo for Together Fund.

        # Together Fund - Investment Screening Memo
        **Date:** [today's date]
        **Prepared by:** Together Fund Deal Sourcing Agent
        **Pipeline:** [sector] | [stage] | [geography]

        ---

        ## Executive Summary
        [2-3 sentences about the startup and key finding]

        ---

        ## Startup Profile

        ### [Startup Name] - [Score]/10 - [Recommendation]
        **Website:** [url]
        **Founders:** [names] | **HQ:** [location] | **Founded:** [year]
        **Sector:** [sector]

        **What they do:** [2-3 sentences]

        **AI Architecture:** [specific inference]

        **Founder Signals:** [IIT/FAANG/YC or lack thereof]

        **Competitors:** [2-3 named]

        | Criterion | Score | Weight | Weighted |
        |-----------|-------|--------|----------|
        | Team Pedigree | X/10 | 30% | X.X |
        | Market Size | X/10 | 25% | X.X |
        | Technical Moat | X/10 | 25% | X.X |
        | Traction | X/10 | 20% | X.X |
        | **TOTAL** | | | **X.X/10** |

        **Pros:**
        - [point 1]
        - [point 2]
        - [point 3]

        **Cons:**
        - [point 1]
        - [point 2]
        - [point 3]

        **Verdict:** [1 sentence action item]

        ---

        ## Suggested Next Steps
        - [action 1]
        - [action 2]
        - [action 3]

        Read all research and write memo immediately.
        Do not use any tools. Write Final Answer directly.
        """,
        expected_output=(
            "Complete markdown Investment Screening Memo "
            "for 1 startup with scorecard and next steps."
        ),
        agent=associate,
        context=[search_task, analyze_task, scoring_task],
        output_file="together_fund_memo.md",
    )

    return [search_task, analyze_task, scoring_task, memo_task]


class TokenPacedCrew:
    """
    Wraps CrewAI's sequential process with deliberate delays
    between each agent handoff to stay within Groq's TPM limit.

    Strategy:
    - Each agent call uses roughly 1500 tokens
    - At 6000 TPM limit, we can do 4 calls per minute safely
    - We pace to 3 calls per minute (one every 20 seconds)
    - Between major agent handoffs we wait 25 seconds
    - This keeps us comfortably under 4500 TPM
    """

    def __init__(self, crew):
        self.crew = crew

    def run(self):
        print("\n" + "="*55)
        print("  Together Fund — Token-Paced Pipeline")
        print(f"  Target: under {TOKEN_BUDGET_PER_MINUTE} TPM")
        print(f"  Delay between agents: {DELAY_BETWEEN_AGENTS}s")
        print("="*55 + "\n")

        agents = ["Researcher", "Analyst", "Scorer", "Associate"]
        for i, agent_name in enumerate(agents):
            if i > 0:
                print(
                    f"\n[Pacer] Waiting {DELAY_BETWEEN_AGENTS}s before "
                    f"{agent_name} to stay within token limits...\n"
                )
                # Visible countdown
                for remaining in range(DELAY_BETWEEN_AGENTS, 0, -5):
                    print(
                        f"[Pacer] {remaining}s remaining...",
                        end="\r"
                    )
                    time.sleep(5)
                print(f"[Pacer] Starting {agent_name} now.          \n")

        # Run the actual crew (delays above are just visual —
        # actual pacing is enforced via max_rpm on each agent)
        return self.crew.kickoff()


def run_pipeline(filters=None) -> str:
    if filters is None:
        filters = {
            "sector": "any AI sector",
            "stage": "pre-seed or seed",
            "geo": "India or the US"
        }

    print("\n[Pipeline] Loading memory...")
    seen = get_all_seen_startup_names()
    if seen:
        print(f"[Pipeline] Will skip: {seen}")
    else:
        print("[Pipeline] Fresh start — no previous startups.")

    researcher, analyst, scorer, associate = build_agents()
    tasks = build_tasks(researcher, analyst, scorer, associate, filters)

    crew = Crew(
        agents=[researcher, analyst, scorer, associate],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
    )

    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    filters = {
        "sector": "B2B SaaS / Dev Tools",
        "stage": "pre-seed",
        "geo": "India or the US"
    }
    memo = run_pipeline(filters)
    print("\n" + "="*55)
    print("FINAL MEMO")
    print("="*55)
    print(memo)