import patch
import os
from crewai import Agent
from crewai_tools import SerperDevTool
from tools.scrape_tool import SmartScrapeTool

# ─────────────────────────────────────────────────────────
# TOKEN PACING STRATEGY
#
# Groq free tier: 6,000 TPM for llama-3.3-70b-versatile
# Safe target:    4,000 TPM (67% of limit = comfortable buffer)
#
# max_rpm controls how many LLM calls per agent per minute.
# Each call ~= 800-1200 tokens average for this task size.
# At max_rpm=2, agent makes at most 2 calls/min = ~2400 tokens/min
# Two agents running sequentially = ~4800 TPM max — under limit.
#
# Agents with tools (researcher, analyst) get max_rpm=2
# Agents without tools (scorer, associate) get max_rpm=3
# because they make fewer, shorter calls.
# ─────────────────────────────────────────────────────────


def build_agents():
    search_tool = SerperDevTool()
    scrape_tool = SmartScrapeTool()

    researcher = Agent(
        role="Startup Sourcing Researcher",
        goal=(
            "Find exactly 1 real, lesser-known AI startup founded "
            "by Indian founders that matches the investment thesis. "
            "Do maximum 3 searches. Give Final Answer immediately after."
        ),
        backstory=(
            "You are a startup scout at Together Fund. "
            "You find under-the-radar startups that nobody else is "
            "looking at yet. You do exactly 3 searches maximum: "
            "Search 1: broad query to find candidates. "
            "Search 2: verify the best candidate. "
            "Search 3: find their real website URL if needed. "
            "Then write Final Answer immediately. "
            "You never make up company names or URLs. "
            "You never search more than 3 times."
        ),
        tools=[search_tool],
        verbose=True,
        max_iter=5,
        allow_delegation=False,
        max_rpm=2,
    )

    analyst = Agent(
        role="Technical Due Diligence Analyst",
        goal=(
            "Research the startup thoroughly using at most 3 searches. "
            "Extract technical details, founder background, competitors. "
            "Write Final Answer as soon as research is complete."
        ),
        backstory=(
            "You are a former Staff ML Engineer at Google turned VC. "
            "Your workflow is strict to save API calls: "
            "Step 1: Search for the startup name and product details. "
            "Step 2: Scrape their website if URL is available. "
            "Step 3: Search for founder backgrounds. "
            "Then write Final Answer immediately. "
            "You never exceed 3 tool calls total. "
            "You never use Action: None. "
            "If you have enough information, stop and write the answer."
        ),
        tools=[search_tool, scrape_tool],
        verbose=True,
        max_iter=6,
        allow_delegation=False,
        max_rpm=2,
    )

    scorer = Agent(
        role="Investment Scoring Specialist",
        goal=(
            "Apply the VC scoring rubric to the startup. "
            "Write your scored Final Answer immediately. "
            "No tools needed."
        ),
        backstory=(
            "You are a quantitative VC analyst. "
            "You read the research from previous agents "
            "and produce a scored output instantly. "
            "You use zero tools. "
            "Your entire response is your Final Answer."
        ),
        tools=[],
        verbose=True,
        max_iter=2,
        allow_delegation=False,
        max_rpm=3,
    )

    associate = Agent(
        role="Investment Associate",
        goal=(
            "Write the Investment Screening Memo using all previous research. "
            "Write Final Answer immediately. No tools needed."
        ),
        backstory=(
            "You are from Sequoia Capital India. "
            "You read all previous research and produce the memo instantly. "
            "You use zero tools. "
            "Your entire response is your Final Answer."
        ),
        tools=[],
        verbose=True,
        max_iter=2,
        allow_delegation=False,
        max_rpm=3,
    )

    return researcher, analyst, scorer, associate