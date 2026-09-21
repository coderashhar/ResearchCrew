"""Inline citation handling.

The writer cites sources as ``[n]`` or ``[n, m]``. The Sources section is
built here from the citations actually used, never by the model, so a
report can only list pages the reader agent actually read.
"""

import re
from collections.abc import Iterable

from research.schemas import Source

# [1] or [1, 3]; not a markdown link label like [1](http://...).
_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\](?!\()")
# Same, capturing the spaces before it so a dropped citation takes them along.
_CITATION_WITH_SPACE = re.compile(r"([ \t]*)" + _CITATION.pattern)


def _ids(group: str) -> list[int]:
    return [int(part) for part in group.split(",")]


def used_ids(report: str) -> list[int]:
    """Citation numbers used in the report, unique and ascending."""
    found: set[int] = set()
    for match in _CITATION.finditer(report):
        found.update(_ids(match.group(1)))
    return sorted(found)


def clean_citations(report: str, valid_ids: Iterable[int]) -> str:
    """Drop citation numbers that match no source.

    ``[1, 9]`` becomes ``[1]``; a citation with no valid number left is
    removed together with the space before it.
    """
    valid = set(valid_ids)

    def replace(match: re.Match[str]) -> str:
        kept: list[int] = []
        for i in _ids(match.group(2)):
            if i in valid and i not in kept:
                kept.append(i)
        if not kept:
            return ""
        return f"{match.group(1)}[{', '.join(map(str, kept))}]"

    return _CITATION_WITH_SPACE.sub(replace, report)


def _escape_link_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def build_sources_section(sources: Iterable[Source], used: Iterable[int]) -> str:
    """Markdown Sources section listing only cited sources, in id order."""
    used_set = set(used)
    cited = sorted((s for s in sources if s.id in used_set), key=lambda s: s.id)
    if not cited:
        return ""
    lines = [
        f"[{s.id}] [{_escape_link_text(s.title or s.url)}]({s.url}) · {s.domain}"
        for s in cited
    ]
    return "## Sources\n\n" + "  \n".join(lines) + "\n"


def format_sources_block(sources: Iterable[Source], max_chars: int = 4000) -> str:
    """Numbered source text for writer and critic prompts."""
    blocks = []
    for s in sorted(sources, key=lambda s: s.id):
        content = s.content[:max_chars]
        blocks.append(f"[{s.id}] {s.title} ({s.url})\n{content}")
    return "\n\n---\n\n".join(blocks)
