"""Run one research topic from the terminal.

Same graph the API serves, so a run can be reproduced without the web
stack: `python cli.py "your topic"`.
"""

import sys
from typing import Any

from rich.console import Console

from research.agents import build_chains
from research.config import get_settings, load_env
from research.graph import ResearchTools, build_graph
from research.schemas import Draft
from research.tools import make_client

LABELS = {
    "plan": "Planning queries",
    "search_and_read": "Searching and reading sources",
    "write": "Writing the report",
    "critique": "Checking the report against its sources",
    "finalize": "Finalizing",
}


def stream_run(graph: Any, topic: str, console: Console) -> str:
    """Print each node's result as it lands; return the final report."""
    report = ""
    for update in graph.stream({"topic": topic}, stream_mode="updates"):
        for node, state in update.items():
            console.print(f"[bold cyan]{LABELS.get(node, node)}[/bold cyan]")
            for line in _describe(node, state):
                console.print(f"  {line}")
            report = state.get("report") or report
    return report


def _describe(node: str, state: dict) -> list[str]:
    if node == "plan":
        return [f"{q.topic}: {q.query}" for q in state.get("queries", [])]
    if node == "search_and_read":
        return [f"[{s.id}] {s.domain} — {s.title}" for s in state.get("sources", [])]
    if node == "write":
        drafts: list[Draft] = state.get("drafts", [])
        return [f"draft v{d.version}, {len(d.report.split())} words" for d in drafts]
    if node == "critique":
        lines = []
        for d in state.get("drafts", []):
            if d.critique:
                lines.append(f"score {d.critique.overall}/10")
                lines += [f"gap: {g}" for g in d.critique.gaps]
        return lines
    return []


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    console = Console()
    topic = " ".join(argv).strip() or console.input("\nResearch topic: ").strip()
    if not topic:
        console.print("[red]No topic given.[/red]")
        return 2

    load_env()
    settings = get_settings()
    chains = build_chains(settings)
    graph = build_graph(chains, ResearchTools.from_client(make_client(settings)), settings)

    report = stream_run(graph, topic, console)
    console.print("\n[bold green]Final report[/bold green]\n")
    console.print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
