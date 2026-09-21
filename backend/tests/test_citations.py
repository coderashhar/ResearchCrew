import pytest

from research.citations import (
    build_sources_section,
    clean_citations,
    format_sources_block,
    used_ids,
)
from research.schemas import Source


def src(i, **kw):
    fields = dict(
        id=i,
        url=f"https://site{i}.com/a",
        title=f"Title {i}",
        domain=f"site{i}.com",
        content=f"content {i}",
    )
    return Source(**{**fields, **kw})


@pytest.mark.parametrize(
    "report, expected",
    [
        ("A fact [1].", [1]),
        ("Two sources [1, 3].", [1, 3]),
        ("Adjacent [2][4].", [2, 4]),
        ("Spacing [3 ,1].", [1, 3]),
        ("Repeat [2] and [2] and [1, 2].", [1, 2]),
        ("No citations here.", []),
    ],
)
def test_used_ids(report, expected):
    assert used_ids(report) == expected


def test_used_ids_ignores_markdown_links():
    assert used_ids("See [1](https://x.com) and [2].") == [2]


def test_clean_strips_unknown_id():
    assert clean_citations("Claim [9].", {1, 2}) == "Claim."


def test_clean_keeps_valid_ids_in_group():
    assert clean_citations("Claim [1, 9].", {1}) == "Claim [1]."


def test_clean_collapses_duplicate_ids_in_group():
    assert clean_citations("Claim [2, 2].", {2}) == "Claim [2]."


def test_clean_leaves_valid_report_untouched():
    report = "One [1]. Two [1, 2] . Keep odd spacing."
    assert clean_citations(report, {1, 2}) == report


def test_sources_section_lists_only_cited_in_id_order():
    section = build_sources_section([src(3), src(1), src(2)], used=[3, 1])
    assert section.startswith("## Sources")
    assert "[1] [Title 1](https://site1.com/a) · site1.com" in section
    assert "[3] [Title 3]" in section
    assert "Title 2" not in section
    assert section.index("[1]") < section.index("[3]")


def test_sources_section_empty_without_citations():
    assert build_sources_section([src(1)], used=[]) == ""


def test_sources_section_escapes_brackets_in_title():
    section = build_sources_section([src(1, title="A [draft] paper")], used=[1])
    assert "[A \\[draft\\] paper]" in section


def test_sources_section_falls_back_to_url_for_blank_title():
    section = build_sources_section([src(1, title="")], used=[1])
    assert "[https://site1.com/a](https://site1.com/a)" in section


def test_sources_block_numbers_and_truncates():
    block = format_sources_block([src(2, content="y" * 50), src(1, content="x" * 50)], max_chars=10)
    assert block.startswith("[1] Title 1 (https://site1.com/a)\n" + "x" * 10)
    assert "[2] Title 2" in block
    assert "x" * 11 not in block


def test_clean_only_touches_spacing_of_removed_citation():
    report = "Kept spacing [1] . Dropped [9]."
    assert clean_citations(report, {1}) == "Kept spacing [1] . Dropped."
