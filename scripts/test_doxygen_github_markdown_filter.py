"""Tests for doxygen-github-markdown-filter.py (imported by path; the filename has dashes)."""

import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).parent / "doxygen-github-markdown-filter.py"
_spec = importlib.util.spec_from_file_location("doxygen_github_markdown_filter", _SCRIPT)
_filter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_filter)

MERMAID_LOADER = _filter.MERMAID_LOADER

# The page the tests convert, unless a test names its own, and the prefix its heading IDs carry.
PAGE = "docs/page.md"
PREFIX = "gh_docs_page"


def convert(lines, page=PAGE):
    return _filter.convert(lines, page)


def test_mermaid_block_becomes_htmlonly_pre():
    out = convert(["```mermaid", "flowchart LR", "    a --> b", "```"])
    assert out[: len(out) - len(MERMAID_LOADER)] == [
        "\\htmlonly",
        '<pre class="mermaid">',
        "flowchart LR",
        "    a --&gt; b",
        "</pre>",
        "\\endhtmlonly",
    ]


def test_mermaid_page_gets_exactly_one_loader():
    out = convert(["```mermaid", "flowchart LR", "```", "text", "```mermaid", "pie", "```"])
    assert out[-len(MERMAID_LOADER) :] == MERMAID_LOADER
    assert out.count('<script src="mermaid.min.js"></script>') == 1


def test_page_without_mermaid_gets_no_loader():
    out = convert(["# Title", "", "```cpp", "int x = 0;", "```"])
    assert '<script src="mermaid.min.js"></script>' not in out
    assert "\\htmlonly" not in out


def test_html_in_diagram_body_is_escaped():
    out = convert(["```mermaid", 'a["label<br/>with & <chars>"]', "```"])
    assert 'a[&quot;label&lt;br/&gt;with &amp; &lt;chars&gt;&quot;]' in out


def test_non_mermaid_fence_with_mermaid_looking_content_is_untouched():
    # Fenced content passes through unchanged; the mermaid transform must not fire inside it.
    out = convert(["```text", "a --> b", "```"])
    assert "a --> b" in out
    assert "\\htmlonly" not in out


def test_mermaid_fence_with_tildes_and_longer_fences():
    out = convert(["~~~~mermaid", "flowchart TB", "~~~~"])
    assert '<pre class="mermaid">' in out
    assert "flowchart TB" in out


def test_unterminated_mermaid_block_still_closes_html():
    out = convert(["```mermaid", "flowchart LR"])
    assert out[: len(out) - len(MERMAID_LOADER)] == [
        "\\htmlonly",
        '<pre class="mermaid">',
        "flowchart LR",
        "</pre>",
        "\\endhtmlonly",
    ]


def test_headings_and_admonitions_still_convert():
    out = convert(["# My Heading", "> [!NOTE]", "> body text", "after"])
    assert out[0] == f"# My Heading {{#{PREFIX}-my-heading}}"
    assert "@note body text" in out
    assert "after" in out


def test_heading_transform_skips_mermaid_body():
    out = convert(["```mermaid", "# not a heading", "```"])
    assert "# not a heading" in out  # no {#anchor} appended


def test_same_heading_on_two_pages_gets_two_ids():
    a = convert(["## Vocabulary"], "docs/rules/a.md")
    b = convert(["## Vocabulary"], "docs/rules/b.md")
    assert a == ["## Vocabulary {#gh_docs_rules_a-vocabulary}"]
    assert b == ["## Vocabulary {#gh_docs_rules_b-vocabulary}"]


def test_repeated_heading_on_one_page_is_numbered_as_github_does():
    out = convert(["## Example", "## Example", "## Example"])
    assert out == [
        f"## Example {{#{PREFIX}-example}}",
        f"## Example {{#{PREFIX}-example-1}}",
        f"## Example {{#{PREFIX}-example-2}}",
    ]


def test_same_page_link_takes_the_page_qualified_id():
    out = convert(["See [the words](#vocabulary) below."])
    assert out == [f"See [the words](#{PREFIX}-vocabulary) below."]


def test_cross_page_link_takes_the_linked_page_qualified_id():
    out = convert(["See [rule](../rules/hand-rules.md#the-slide-rule)."], "docs/guide/page.md")
    assert out == ["See [rule](#gh_docs_rules_hand_rules-the-slide-rule)."]


def test_reference_definition_is_rewritten():
    out = convert(["[slide]: other.md#the-slide-rule"])
    assert out == ["[slide]: #gh_docs_other-the-slide-rule"]


def test_links_that_name_no_heading_are_untouched():
    lines = [
        "[page](other.md) [site](https://example.com/a.md#x) [img](pic.png) [root](/a.md#x)",
    ]
    assert convert(lines) == lines


def test_links_in_code_are_untouched():
    lines = ["Write `[x](#slug)` for a link to [x](#slug).", "```", "[x](#slug)", "```"]
    out = convert(lines)
    assert out[0] == f"Write `[x](#slug)` for a link to [x](#{PREFIX}-slug)."
    assert out[1:] == lines[1:]


def test_page_on_another_drive_is_named_by_its_absolute_path(monkeypatch):
    def no_relative_path(path, start=None):
        raise ValueError("path is on mount 'D:', start on mount 'C:'")

    monkeypatch.setattr(_filter.os.path, "relpath", no_relative_path)
    page = _filter.page_path("docs/other.md")
    assert page == _filter.os.path.abspath("docs/other.md")
    # A sibling's link to it resolves to the same prefix the page gives its own headings.
    sibling = _filter.os.path.join(_filter.os.path.dirname(page), "sibling.md")
    link = convert(["[x](other.md#scope)"], sibling)
    assert link == [f"[x](#{_filter.page_prefix(page)}-scope)"]


def test_admonition_body_links_are_rewritten_and_the_next_line_still_converts():
    out = convert(["> [!NOTE]", "> See [x](#slug).", "## Next"])
    assert out == [f"@note See [x](#{PREFIX}-slug).", f"## Next {{#{PREFIX}-next}}"]
