# Together Fund — Autonomous AI Deal Sourcing Agent

> A production-grade, 4-agent AI pipeline that autonomously sources, evaluates, scores, and generates investment memos for early-stage AI startups — built for Together Fund's thesis of backing Indian founders in AI.

**[Live Demo →](https://together-fund-agent-xba3af8clrugxdrrgzpcfs.streamlit.app/)** &nbsp;|&nbsp; **[GitHub →](https://github.com/Garvit-Pahwa-03/together-fund-agent)**

---

## What It Does

VC analysts spend 4–6 hours per startup manually searching the web, evaluating technical architecture, scoring against a rubric, and writing memos. This system compresses that to **3–5 minutes** with no human input.

Each scan:
1. Finds one under-the-radar Indian AI startup via web search
2. Scrapes their website for technical details (with automatic fallback if blocked)
3. Scores them on a weighted VC rubric
4. Writes a complete partner-ready investment memo
5. Saves everything to your private cloud account — persistent across sessions

---

## The 4-Agent Pipeline

```
User Input (sector, stage, geography)
        │
        ▼
┌─────────────────────────┐
│  Agent 1: Researcher    │  SerperDevTool → finds 1 startup
│  max_rpm=2, max_iter=5  │  skips your previously seen startups
└────────────┬────────────┘
             │ startup details
             ▼
┌─────────────────────────┐
│  Agent 2: Analyst       │  SmartScrapeTool + SerperDevTool
│  max_rpm=2, max_iter=6  │  scrapes website, finds founders,
└────────────┬────────────┘  competitors, AI architecture
             │ technical breakdown
             ▼
┌─────────────────────────┐
│  Agent 3: Scorer        │  No tools — reasoning only
│  max_rpm=3, max_iter=2  │  applies weighted VC rubric
└────────────┬────────────┘  outputs score/10 + recommendation
             │ scorecard
             ▼
┌─────────────────────────┐
│  Agent 4: Associate     │  No tools — writing only
│  max_rpm=3, max_iter=2  │  writes full investment memo
└────────────┬────────────┘  in markdown format
             │
             ▼
     MongoDB Atlas (saved to your account)
     Streamlit UI (displayed + downloadable)
```

---

## Investment Scoring Rubric

| Criterion | Weight | 9–10 | 7–8 | 5–6 | 1–4 |
|-----------|--------|------|-----|-----|-----|
| Team Pedigree | **30%** | IIT/IIM + FAANG + exit | IIT or FAANG | Decent background | Unknown |
| Market Size (TAM) | **25%** | > $10B | $1B–$10B | $100M–$1B | < $100M |
| Technical Moat | **25%** | Proprietary model/data | Strong workflow moat | Good but replicable | API wrapper |
| Traction | **20%** | Revenue / named customers | Beta users / pilots | Product live | Pre-product |

- Score < 5.0 → **Pass**
- Score 5.0–7.0 → **Take Meeting**
- Score > 7.0 → **Fast Track**

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM | Llama 3.3 70B via Groq | Agent reasoning and generation |
| Agent Framework | CrewAI 0.28.8 | Multi-agent orchestration |
| Web Search | Serper API | Startup discovery and research |
| Web Scraping | BeautifulSoup4 + requests | Website content extraction |
| Database | MongoDB Atlas M0 | Persistent per-user cloud storage |
| Auth | SHA-256 password hashing | User account management |
| UI | Streamlit | Web interface |
| PDF Export | fpdf2 | Downloadable investment memos |
| Validation | Pydantic v2 | Structured output schemas |
| Deployment | Streamlit Cloud | Live public hosting |

**Total cost to run: $0** — all free tiers, no credit card required.

---

## Key Engineering Decisions

### 1. URL Hallucination Guard
LLM agents frequently returned LinkedIn profiles and news article URLs instead of company websites. Built a two-layer validation system in `tools/validator.py`:
- `is_valid_url()` checks structural validity
- `url_is_reachable()` makes a HEAD request and checks HTTP status
- `blocked_domains` list catches LinkedIn, Twitter, NDTV, Bloomberg before connection attempts
- `SmartScrapeTool` automatically falls back to web search if any validation step fails

### 2. Token Rate Limiting via max_rpm
Groq's free tier allows 6,000 tokens per minute. Instead of retry logic after hitting the limit, used CrewAI's built-in `max_rpm` parameter to pace requests proactively:
- Tool-using agents: `max_rpm=2` → ~2,000 TPM peak
- Reasoning-only agents: `max_rpm=3` → short single calls
- Sequential execution means peaks never overlap
- Result: pipeline never hits the rate limit

### 3. sys.modules Monkey-Patch for Streamlit Cloud
`crewai==0.28.8` imports `pkg_resources` in its telemetry module, which is absent from Streamlit Cloud's uv-based environment. `patch.py` pre-populates `sys.modules['pkg_resources']` with a fake module implementing the exact functions crewai calls (`get_distribution`, `require`). Imported as the first line in `app.py`, `crew.py`, and `agents/__init__.py`.

### 4. Per-User Data Isolation
Every MongoDB document has a `user_id` field. Every query filters by `WHERE user_id = str(user_id)`. Users can only see, modify, and clear their own data. The agent's memory — the list of startups to skip — is also scoped per user, so two users independently discover different startups.

### 5. Single-Startup-Per-Run Design
Early versions tried to find 3 startups per run, frequently producing incomplete results. Switching to 1 startup per run eliminated that problem. Combined with MongoDB memory, each run adds one new startup to the user's private pipeline — building a deal database organically over time.

### 6. Confidence Scoring
Each analysis gets a 0–10 confidence score measuring data quality:

| Signal | Points |
|--------|--------|
| Website successfully scraped (not fallback) | +3.0 |
| Founders named and verified | +2.0 |
| AI architecture description is specific | +2.0 |
| Founded year confirmed | +1.0 |
| Competitors named specifically | +1.0 |
| HQ location confirmed | +1.0 |

High confidence (8+) means most data came from real scraped sources. Low confidence means the analysis is largely inferred by the model.

---

## Project Structure

```
together_fund_agent/
│
├── patch.py                 # pkg_resources monkey-patch (import first)
├── app.py                   # Streamlit UI — auth + 5 tabs
├── crew.py                  # CrewAI pipeline orchestration
├── confidence.py            # Analysis confidence scoring
├── export.py                # Markdown → PDF conversion
├── runtime.txt              # Python 3.11.9 for Streamlit Cloud
├── requirements.txt
│
├── agents/
│   └── __init__.py          # 4 agent definitions with tuned parameters
│
├── tools/
│   ├── scrape_tool.py       # SmartScrapeTool with fallback
│   └── validator.py         # URL reachability validation
│
├── models/
│   └── schemas.py           # Pydantic output schemas
│
└── database/
    └── memory.py            # MongoDB Atlas — all DB operations
```

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- Git

### Step 1: Clone and install
```bash
git clone https://github.com/Garvit-Pahwa-03/together-fund-agent.git
cd together-fund-agent
pip install -r requirements.txt
```

### Step 2: Get free API keys

**Groq** (LLM inference — free, no credit card):
1. Sign up at [console.groq.com](https://console.groq.com)
2. API Keys → Create Key → copy it

**Serper** (web search — 2,500 free searches/month):
1. Sign up at [serper.dev](https://serper.dev)
2. Dashboard → copy API key

**MongoDB Atlas** (database — free M0 tier forever):
1. Sign up at [mongodb.com/atlas](https://mongodb.com/atlas)
2. Create free M0 cluster
3. Database Access → Add user with password
4. Network Access → Add IP → Allow Access from Anywhere (0.0.0.0/0)
5. Connect → Drivers → copy connection string

### Step 3: Configure environment
```bash
# Create .env file in project root
GROQ_API_KEY=your_groq_key_here
SERPER_API_KEY=your_serper_key_here
OPENAI_API_KEY=your_groq_key_here
OPENAI_API_BASE=https://api.groq.com/openai/v1
OPENAI_MODEL_NAME=llama-3.3-70b-versatile
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/together_fund
```

### Step 4: Run
```bash
# Terminal (test pipeline directly)
python crew.py

# Web UI
streamlit run app.py
```

---

## Deployment on Streamlit Cloud (Free)

1. Push to GitHub (ensure `.env` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → select repo
3. Set main file to `app.py`
4. Settings → Secrets → add all keys in TOML format:
```toml
GROQ_API_KEY = "your_key"
SERPER_API_KEY = "your_key"
OPENAI_API_KEY = "your_key"
OPENAI_API_BASE = "https://api.groq.com/openai/v1"
OPENAI_MODEL_NAME = "llama-3.3-70b-versatile"
MONGO_URI = "mongodb+srv://..."
```
5. Deploy → get public URL

---

## Problems Solved

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Hallucinated LinkedIn/NDTV URLs | LLM inventing URLs | URL validator + blocked_domains + fallback |
| `Action: None` crash | Agent didn't know how to signal completion | Backstory engineering + `tools=[]` for non-tool agents |
| crewai==0.28.8 not found on PyPI | Python 3.14 incompatibility | `runtime.txt` pinning Python 3.11.9 |
| `pkg_resources` missing | uv installer strips it | `patch.py` sys.modules injection |
| Groq 429 rate limit errors | Burst token consumption | `max_rpm` on every agent |
| Users seeing each other's data | No user_id filtering | `WHERE user_id = ?` on every query |
| MongoDB SSL handshake failure | TLS version mismatch on Streamlit Cloud | pymongo==4.7.3 + explicit `tls=True` |
| Data lost on redeployment | Streamlit Cloud ephemeral filesystem | Migrated SQLite → MongoDB Atlas |
| Only 2 of 3 startups found | Complex multi-result search task | Redesigned to 1 startup per run |
| Model decommissioned mid-project | Groq retired llama3-70b-8192 | Updated to llama-3.3-70b-versatile |

---

## Groq Free Tier Limits

| Metric | Limit | Our Usage |
|--------|-------|-----------|
| Tokens per minute (TPM) | 6,000 | ~2,000 peak (max_rpm=2) |
| Tokens per day | 100,000 | ~8,000 per full run |
| Requests per minute | 30 | ~6 per run |

---

## Features

- **Authentication** — create account, sign in, sign out with SHA-256 hashed passwords
- **Per-user memory** — agent skips startups you've already analyzed
- **5 tabs** — New Scan, Comparison View, Run History, All Startups, My Ratings
- **Confidence scoring** — 0–10 score measuring data quality of each analysis
- **Comparison view** — filter by recommendation/sector, sort by score or confidence
- **PDF + Markdown export** — download any investment memo
- **User ratings** — rate each startup 1–5 for relevance tracking
- **Clear memory** — wipe your history and start fresh anytime

---

## What I Would Add Next

- **Parallel agent execution** — run analyst and researcher concurrently to cut runtime from 5 min to ~90 seconds
- **Crunchbase API** — verified funding data instead of inferred traction signals  
- **Feedback loop** — use user ratings to tune search queries over time, making the pipeline adaptive
- **Confidence threshold filter** — only save analyses above a minimum confidence score

---

## API Keys Reference

| Service | Free Tier | Get Key |
|---------|-----------|---------|
| Groq | 100K tokens/day, 30 req/min | [console.groq.com](https://console.groq.com) |
| Serper | 2,500 searches/month | [serper.dev](https://serper.dev) |
| MongoDB Atlas | 512MB storage, forever free | [mongodb.com/atlas](https://mongodb.com/atlas) |
| Streamlit Cloud | Unlimited public apps | [share.streamlit.io](https://share.streamlit.io) |

---

*Built for Together Fund — a seed-stage VC firm backing Indian founders in AI.*
