"""Doxygen input filter that converts GitHub Flavored Markdown for Doxygen compatibility.

- Converts GFM admonitions (> [!NOTE], etc.) to Doxygen @-commands
- Strips CI badge lines (they show stale status outside GitHub)
- Adds anchor IDs to headings so GitHub-style fragment links resolve in Doxygen
- Converts ```mermaid fences to client-rendered HTML (GitHub renders them natively; Doxygen
  has no Mermaid support, so pages that contain diagrams carry their own loader script)

Doxygen's anchor IDs are global to a site, where GitHub's are per page, so the same heading on two
pages would claim one ID. Each heading ID is therefore the GitHub slug qualified by the page's path,
and the filter rewrites the GitHub links that name a heading, `(#slug)` on the same page and
`(other.md#slug)` across pages, to that qualified ID.
"""

import html
import os
import re
import sys
import urllib.parse

ADMONITION_MAP = {
    "NOTE": "note",
    "TIP": "remark",
    "IMPORTANT": "attention",
    "WARNING": "warning",
    "CAUTION": "warning",
}

# Emitted once at the end of any page that contains at least one Mermaid block. Each generated
# Doxygen page is a standalone HTML document, so the page carries its own loader instead of the
# site needing a customized Doxygen header. The script is the vendored single-file UMD bundle in
# doxygen-mermaid/, which project_config_add_docs copies beside the pages through HTML_EXTRA_FILES;
# the relative src works because Doxygen's HTML output directory is flat, and a classic script (not
# an ES module) is required so pages also render over file:// with no network. HTML output only
# (GENERATE_LATEX is off).
MERMAID_LOADER = [
    "\\htmlonly",
    '<script src="mermaid.min.js"></script>',
    "<script>",
    '  const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;',
    '  mermaid.initialize({ startOnLoad: false, theme: dark ? "dark" : "neutral" });',
    "  mermaid.run();",
    "</script>",
    "\\endhtmlonly",
]

# A code span, which passes through untouched, or a link target: inline after "](" or in a
# reference definition "[label]: ".
CODE_SPAN_OR_LINK = re.compile(r"(`+).*?\1|(\]\(\s*<?|^\s{0,3}\[[^\]]+\]:\s*<?)([^\s)>]+)")


def github_slug(text):
    """Convert heading text to a GitHub-style anchor slug."""
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)  # bold / italic
    text = re.sub(r"`(.+?)`", r"\1", text)                # inline code
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)       # links
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def page_path(file):
    """The page's path as heading IDs name it: relative to the folder Doxygen runs in, or absolute
    for a file on another drive, which no relative path reaches."""
    try:
        return os.path.relpath(file)
    except ValueError:
        return os.path.abspath(file)


def page_prefix(page):
    """Qualify a page's heading IDs: its path without the extension, in ID-safe characters.

    The prefix holds no "-", so the first "-" of a qualified ID ends it, and every ID starts with a
    letter, as Doxygen requires. It starts "gh_", which no ID of Doxygen's own does (its Markdown
    page IDs start "md_"), so a heading ID never meets a page ID.
    """
    stem = os.path.splitext(os.path.normpath(page))[0]
    return "gh_" + re.sub(r"[^A-Za-z0-9]+", "_", stem)


def heading_link(target, page):
    """Rewrite a link to a heading to the heading's qualified ID; leave any other link alone."""
    path, has_fragment, fragment = target.partition("#")
    if not has_fragment or not fragment:
        return target
    if not path:
        return f"#{page_prefix(page)}-{fragment}"
    if path.lower().endswith(".md") and not re.match(r"[A-Za-z][\w+.-]*:|/", path):
        linked = os.path.join(os.path.dirname(page), urllib.parse.unquote(path))
        return f"#{page_prefix(linked)}-{fragment}"
    return target


def rewrite_links(line, page):
    def rewrite(match):
        if match.group(1):
            return match.group(0)
        return match.group(2) + heading_link(match.group(3), page)

    return CODE_SPAN_OR_LINK.sub(rewrite, line)


def is_badge(line):
    return re.match(r"^\[!\[.*\]\(.*badge.*\)\]\(.*\)$", line)


def convert(lines, page):
    """Convert one page's lines; page is its path as page_path gives it."""
    out = []
    it = iter(range(len(lines)))
    in_fence = False
    fence_pattern = None
    saw_mermaid = False
    admonition = None  # (command, body lines) of the admonition being read
    slug_counts = {}

    for i in it:
        line = lines[i]
        if not in_fence:
            line = rewrite_links(line, page)

        # --- GFM admonition body: gather until the blockquote ends, then convert ---
        if admonition:
            cont = re.match(r"^>\s?(.*)$", line)
            if cont:
                if cont.group(1):
                    admonition[1].append(cont.group(1))
                continue
            out.append(f"@{admonition[0]} {' '.join(admonition[1]).strip()}")
            admonition = None

        # --- Mermaid blocks: emit HTML for client-side rendering ---
        mermaid_match = re.match(r"^(`{3,}|~{3,})\s*mermaid\s*$", line)
        if mermaid_match and not in_fence:
            chars = mermaid_match.group(1)
            close_pattern = re.compile(rf"^{re.escape(chars[0])}{{{len(chars)},}}\s*$")
            out.append("\\htmlonly")
            out.append('<pre class="mermaid">')
            for j in it:  # consume the diagram body
                if close_pattern.match(lines[j]):
                    break
                # Escape so Mermaid text (e.g. -->, <br/>) survives as textContent, which is
                # what mermaid.run() reads back before rendering.
                out.append(html.escape(lines[j]))
            out.append("</pre>")
            out.append("\\endhtmlonly")
            saw_mermaid = True
            continue

        # --- Fenced code blocks: pass through unchanged ---
        fence_match = re.match(r"^(`{3,}|~{3,})", line)
        if fence_match:
            if not in_fence:
                in_fence = True
                chars = fence_match.group(1)
                fence_pattern = re.compile(rf"^{re.escape(chars[0])}{{{len(chars)},}}\s*$")
            elif fence_pattern.match(line):
                in_fence = False
            out.append(line)
            continue

        if in_fence:
            out.append(line)
            continue

        # --- Badge lines: drop ---
        if is_badge(line):
            continue

        # --- GFM admonitions: start gathering the body ---
        start = re.match(r"^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$", line)
        if start:
            admonition = (ADMONITION_MAP[start.group(1)], [])
            continue

        # --- Headings: add page-qualified GitHub-style anchor IDs, numbered as GitHub numbers a
        # repeated heading on one page ---
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading and "{#" not in line:
            hashes, text = heading.groups()
            slug = github_slug(text)
            repeat = slug_counts.get(slug, 0)
            slug_counts[slug] = repeat + 1
            if repeat:
                slug = f"{slug}-{repeat}"
            out.append(f"{hashes} {text} {{#{page_prefix(page)}-{slug}}}")
            continue

        out.append(line)

    if admonition:
        out.append(f"@{admonition[0]} {' '.join(admonition[1]).strip()}")
    if saw_mermaid:
        out.extend(MERMAID_LOADER)

    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: doxygen-github-markdown-filter.py <file>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n\r") for line in f]

    sys.stdout.reconfigure(encoding="utf-8")
    for line in convert(lines, page_path(sys.argv[1])):
        print(line)


if __name__ == "__main__":
    main()
