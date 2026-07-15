"""Tests for doxygen-github-markdown-filter.py (imported by path; the filename has dashes)."""

import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).parent / "doxygen-github-markdown-filter.py"
_spec = importlib.util.spec_from_file_location("doxygen_github_markdown_filter", _SCRIPT)
_filter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_filter)

convert = _filter.convert
MERMAID_LOADER = _filter.MERMAID_LOADER


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
    assert out[0] == "# My Heading {#my-heading}"
    assert "@note body text" in out
    assert "after" in out


def test_heading_transform_skips_mermaid_body():
    out = convert(["```mermaid", "# not a heading", "```"])
    assert "# not a heading" in out  # no {#anchor} appended
