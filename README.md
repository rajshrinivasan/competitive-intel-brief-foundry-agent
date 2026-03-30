# Project 06 — Startup Competitive Intelligence Brief

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

## Pattern
**Concurrent agents — parallel fan-out then sequential synthesis**

Two orchestration primitives are chained together:

1. **ConcurrentBuilder** — five researcher agents all receive the same company
   name simultaneously and run in parallel. Each specialises in exactly one
   intelligence signal.

2. **SequentialBuilder (single agent)** — once all researchers finish, their
   outputs are bundled into one message and fed to a synthesis agent that
   produces a one-page competitive intelligence brief.

---

## Architecture

```
User enters company name
        │
        ▼
── STAGE 1: CONCURRENT FAN-OUT ──────────────────────────────────
│
├─► [news_researcher]     "Research Stripe: news & announcements"
├─► [pricing_researcher]  "Research Stripe: pricing intelligence"  ← all run
├─► [jobs_researcher]     "Research Stripe: hiring signals"           in parallel
├─► [github_researcher]   "Research Stripe: OSS & dev activity"
└─► [patents_researcher]  "Research Stripe: patent & IP intelligence"
        │
        │  ConcurrentBuilder collects all 5 responses
        ▼
── STAGE 2: SEQUENTIAL SYNTHESIS ────────────────────────────────
│
└─► [synthesiser]   receives all 5 reports bundled into one message
                    produces: one-page competitive intelligence brief
                    saved to: brief_<company>_<date>.txt
```

---

## The six agents

| Agent | Runs | Speciality |
|---|---|---|
| `news_researcher` | Concurrent | Recent events, funding, launches, reputation |
| `pricing_researcher` | Concurrent | Pricing model, tiers, market position |
| `jobs_researcher` | Concurrent | Hiring patterns → strategic intent |
| `github_researcher` | Concurrent | OSS presence, developer ecosystem |
| `patents_researcher` | Concurrent | IP portfolio, R&D focus signals |
| `synthesiser` | Sequential (after all 5) | One-page brief with actions |

---

## Brief output format

```
COMPETITIVE INTELLIGENCE BRIEF
Company: Stripe
Date: 2026-03-29
==================================================
COMPANY SNAPSHOT        — 2-3 sentence overview
KEY FINDINGS            — one line per signal
STRATEGIC THEMES        — 3 bullets connecting signals
THREATS & OPPORTUNITIES — one threat, one opportunity
RECOMMENDED ACTIONS     — 30-day and 90-day actions
Confidence: High/Medium/Low
```

The brief is also saved to `brief_<company>_<date>.txt`.

---

## SDK: what's new vs Project 05

Both projects use `agent-framework`. The new primitive here is `ConcurrentBuilder`:

| | Project 05 (SequentialBuilder) | Project 06 (ConcurrentBuilder + SequentialBuilder) |
|---|---|---|
| Agents run | One at a time, in order | All at the same time |
| Output shape | Accumulated history | One response per agent, collected as a list |
| Context flow | Each agent sees all prior output | Each agent only sees the original prompt |
| Chaining | Built-in (framework handles it) | Manual — collect concurrent output, reformat, feed to synthesiser |

The manual chaining step is in `format_research_bundle()` — it packages all five
researcher responses into a single structured message that the synthesiser can parse.

---

## Prerequisites

- Python 3.11+
- An Azure AI Foundry project with a **gpt-4.1** (or gpt-4o) model deployment
- Azure CLI logged in (`az login`)

---

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate      # Windows
# source venv/bin/activate        # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env — fill in PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME
```

---

## Running

```bash
python agent.py
```

Enter a company name at the prompt. The five researchers run in parallel, their
outputs are printed as they arrive, then the synthesiser produces the brief.

Good companies to try:
- `Stripe` — well-documented, strong OSS presence
- `Notion` — pricing changes, interesting hiring patterns
- `Vercel` — heavy developer focus, active OSS
- `Figma` — post-Adobe acquisition news
- `Databricks` — strong patent and hiring signals

---

## Key concepts illustrated

### ConcurrentBuilder — fan-out
All five agents receive the same prompt at the same time. The framework dispatches
them in parallel and waits for all to complete before emitting the `output` event.
This is faster than sequential for independent research tasks.

### Manual chaining between workflows
`ConcurrentBuilder` and `SequentialBuilder` are separate workflows. The output
of the concurrent stage is not automatically passed to the sequential stage.
`format_research_bundle()` bridges them: it extracts each agent's text by name
and formats it into a single structured message for the synthesiser.

### Agent output addressed by name
`extract_agent_outputs()` iterates the message list and keys each response by
`msg.author_name`. This is how we know which report came from which researcher,
even though they all ran simultaneously.

---

## File structure

```
06-competitive-intel-brief/
├── agent.py                            # Concurrent + sequential pipeline runner
├── prompts/
│   ├── news_researcher_prompt.txt
│   ├── pricing_researcher_prompt.txt
│   ├── jobs_researcher_prompt.txt
│   ├── github_researcher_prompt.txt
│   ├── patents_researcher_prompt.txt
│   └── synthesis_prompt.txt
├── brief_<company>_<date>.txt          # Generated at runtime (gitignored)
├── requirements.txt
├── .env.example
├── .env                                # Your credentials — gitignored, never committed
├── LICENSE
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE)
