"""Smoke-test a deployed ResearchCrew.

Runs one short topic against a live deployment and checks that the stream
finishes with a cited report. A green build says the code compiles; this
says the agents, Tavily, Mistral and Postgres all actually answered.

    python scripts/smoke.py https://your-deployment.vercel.app
"""

import json
import re
import sys

import httpx

TOPIC = "what is retrieval augmented generation"
TIMEOUT = httpx.Timeout(300.0, connect=15.0)


def check_health(client: httpx.Client, base: str) -> None:
    response = client.get(f"{base}/api/health")
    response.raise_for_status()
    print(f"health: {response.json()}")


def run_topic(client: httpx.Client, base: str) -> tuple[str | None, dict]:
    """Read the SSE stream, printing each event; return the run id and result."""
    seen: list[str] = []
    final: dict | None = None
    run_id: str | None = None
    name = ""

    with client.stream("POST", f"{base}/api/research", json={"topic": TOPIC}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
                seen.append(name)
                print(f"  {name}")
            elif line.startswith("data:") and name in ("run", "final", "error"):
                payload = json.loads(line.split(":", 1)[1].strip())
                if name == "error":
                    raise SystemExit(f"Run failed: {payload['message']}")
                if name == "run":
                    run_id = payload["id"]
                else:
                    final = payload

    if final is None:
        raise SystemExit(f"Stream ended without a final event; saw {seen}")
    return run_id, final


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    base = argv[0].rstrip("/")

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        check_health(client, base)
        run_id, final = run_topic(client, base)

        citations = re.findall(r"\[(\d+)\]", final["report"])
        print(
            f"score {final['score']}/10, {len(final['sources'])} sources, "
            f"{len(citations)} citations, {final['elapsed_s']}s"
        )

        if not citations:
            raise SystemExit("The report cites nothing.")
        if not final["sources"]:
            raise SystemExit("The report lists no sources.")

        # A permalink must serve the same report afterwards.
        if run_id:
            saved = client.get(f"{base}/api/runs/{run_id}")
            saved.raise_for_status()
            if saved.json()["final_report"] != final["report"]:
                raise SystemExit("The saved run does not match what was streamed.")
            print(f"permalink: {base}/r/{run_id}")

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
