"""
Startup Competitive Intelligence Brief
=======================================
Pattern : Concurrent agents — parallel fan-out then sequential synthesis

Stage 1 — CONCURRENT: five researcher agents all receive the same company
name simultaneously and run in parallel. Each specialises in one signal:
news, pricing, hiring, open-source activity, and patents.

Stage 2 — SEQUENTIAL: a synthesis agent receives all five research reports
and produces a single one-page competitive intelligence brief.

This combines two orchestration primitives from agent-framework:
  - ConcurrentBuilder  : fan-out, all agents run at the same time
  - SequentialBuilder  : the synthesiser runs after all researchers finish

The two workflows are chained manually: we collect the concurrent output,
format it as a single message, then feed it into the sequential synthesiser.
"""

import asyncio
import os
from datetime import date
from typing import cast
from pathlib import Path
from dotenv import load_dotenv

from agent_framework import Message, WorkflowEvent
from agent_framework.orchestrations import ConcurrentBuilder, SequentialBuilder
from agent_framework.azure import AzureAIAgentClient
from azure.identity import AzureCliCredential


# ---------------------------------------------------------------------------
# Load prompt from file
# ---------------------------------------------------------------------------
def load_prompt(filename: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / filename
    return prompt_path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def print_banner():
    print("=" * 60)
    print("   COMPETITIVE INTELLIGENCE BRIEF GENERATOR")
    print("   Powered by Azure AI Foundry — Concurrent + Sequential")
    print("=" * 60)
    print()


def extract_agent_outputs(messages: list[Message]) -> dict[str, str]:
    """Return a dict of {agent_name: response_text} from a concurrent run."""
    results = {}
    for msg in messages:
        if msg.role == "assistant" and msg.author_name:
            results[msg.author_name] = msg.text
    return results


def format_research_bundle(company: str, research: dict[str, str]) -> str:
    """Package all five research reports into a single message for the synthesiser."""
    section_labels = {
        "news_researcher":    "1. NEWS & ANNOUNCEMENTS",
        "pricing_researcher": "2. PRICING INTELLIGENCE",
        "jobs_researcher":    "3. HIRING SIGNALS",
        "github_researcher":  "4. OPEN SOURCE & DEVELOPER ACTIVITY",
        "patents_researcher": "5. PATENT & IP INTELLIGENCE",
    }
    parts = [
        f"Company under analysis: {company}",
        f"Research date: {date.today().isoformat()}",
        "",
        "The following five research reports were produced in parallel.",
        "Synthesise them into a one-page competitive intelligence brief.",
        "",
    ]
    for agent_name, label in section_labels.items():
        report = research.get(agent_name, "[No data received from this researcher]")
        parts.append(f"{label}\n{'─' * 40}\n{report}\n")

    return "\n".join(parts)


def save_brief(company: str, content: str):
    safe_name = company.lower().replace(" ", "_").replace("/", "-")
    filename = f"brief_{safe_name}_{date.today().isoformat()}.txt"
    output_path = Path(__file__).parent / filename
    output_path.write_text(content, encoding="utf-8")
    print(f"\n[Brief saved to {filename}]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    print_banner()
    load_dotenv()

    # -- Load all prompts -----------------------------------------------------
    news_instructions     = load_prompt("news_researcher_prompt.txt")
    pricing_instructions  = load_prompt("pricing_researcher_prompt.txt")
    jobs_instructions     = load_prompt("jobs_researcher_prompt.txt")
    github_instructions   = load_prompt("github_researcher_prompt.txt")
    patents_instructions  = load_prompt("patents_researcher_prompt.txt")
    synthesis_instructions = load_prompt("synthesis_prompt.txt")

    credential = AzureCliCredential()

    async with AzureAIAgentClient(
        credential=credential,
        project_endpoint=os.environ["PROJECT_ENDPOINT"],
        model_deployment_name=os.environ["MODEL_DEPLOYMENT_NAME"],
    ) as client:

        # -- Create five parallel researcher agents ---------------------------
        news_researcher    = client.as_agent(name="news_researcher",    instructions=news_instructions)
        pricing_researcher = client.as_agent(name="pricing_researcher", instructions=pricing_instructions)
        jobs_researcher    = client.as_agent(name="jobs_researcher",    instructions=jobs_instructions)
        github_researcher  = client.as_agent(name="github_researcher",  instructions=github_instructions)
        patents_researcher = client.as_agent(name="patents_researcher", instructions=patents_instructions)

        # -- Create the synthesis agent ---------------------------------------
        synthesiser = client.as_agent(name="synthesiser", instructions=synthesis_instructions)

        # -- Concurrent research workflow -------------------------------------
        research_workflow = ConcurrentBuilder(
            participants=[
                news_researcher,
                pricing_researcher,
                jobs_researcher,
                github_researcher,
                patents_researcher,
            ]
        ).build()

        # -- Synthesis workflow (single agent, sequential of one) -------------
        synthesis_workflow = SequentialBuilder(
            participants=[synthesiser]
        ).build()

        # -- Interactive loop --------------------------------------------------
        print("Enter a company name to research (e.g. 'Stripe', 'Notion', 'Vercel')")
        print("Type 'quit' to exit.\n")

        while True:
            try:
                company = input("Company: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break

            if company.lower() in ("quit", "exit", "q"):
                break
            if not company:
                print("Please enter a company name.\n")
                continue

            # ── Stage 1: Concurrent research ─────────────────────────────────
            print(f"\nResearching '{company}' across 5 signals in parallel...\n")

            research_prompt = (
                f"Research the following company and produce your specialist report: {company}"
            )

            raw_outputs: list[list[Message]] = []
            async for event in research_workflow.run(research_prompt, stream=True):
                if event.type == "output":
                    raw_outputs.append(cast(list[Message], event.data))

            if not raw_outputs:
                print("[Error] No research output received.\n")
                continue

            research_results = extract_agent_outputs(raw_outputs[-1])
            print(f"  Research complete. {len(research_results)}/5 signals received.")

            # Print each researcher's output as it arrives
            section_order = [
                ("news_researcher",    "NEWS"),
                ("pricing_researcher", "PRICING"),
                ("jobs_researcher",    "HIRING"),
                ("github_researcher",  "OSS/DEV"),
                ("patents_researcher", "PATENTS"),
            ]
            for agent_name, label in section_order:
                if agent_name in research_results:
                    print(f"\n{'─' * 50}")
                    print(f"  [{label}]")
                    print(f"{'─' * 50}")
                    print(research_results[agent_name])

            # ── Stage 2: Sequential synthesis ────────────────────────────────
            print(f"\n{'=' * 50}")
            print("  SYNTHESISING BRIEF...")
            print(f"{'=' * 50}\n")

            synthesis_input = format_research_bundle(company, research_results)

            synthesis_outputs: list[list[Message]] = []
            async for event in synthesis_workflow.run(synthesis_input, stream=True):
                if event.type == "output":
                    synthesis_outputs.append(cast(list[Message], event.data))

            brief_text = ""
            if synthesis_outputs:
                for msg in synthesis_outputs[-1]:
                    if msg.role == "assistant":
                        brief_text = msg.text
                        break

            if brief_text:
                print(brief_text)
                save_brief(company, brief_text)
            else:
                print("[Error] Synthesis produced no output.\n")

            print()
            again = input("Research another company? (yes / no): ").strip().lower()
            if again not in ("yes", "y"):
                break
            print()

    print("\nSession complete.")


if __name__ == "__main__":
    asyncio.run(main())
