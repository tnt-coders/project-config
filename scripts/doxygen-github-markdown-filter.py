"""Doxygen input filter that converts GitHub Flavored Markdown for Doxygen compatibility.

- Converts GFM admonitions (> [!NOTE], etc.) to Doxygen @-commands
- Strips CI badge lines (they show stale status outside GitHub)
- Adds anchor IDs to headings so GitHub-style fragment links (#slug) resolve in Doxygen
- Converts ```mermaid fences to client-rendered HTML (GitHub renders them natively; Doxygen
  has no Mermaid support, so pages that contain diagrams carry their own loader script)
"""

import html
import re
import sys

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
# doxygen-mermaid/, copied beside the pages by the consumer's Doxyfile HTML_EXTRA_FILES; the
# relative src works because Doxygen's HTML output directory is flat, and a classic script (not
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


def github_slug(text):
    """Convert heading text to a GitHub-style anchor slug."""
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)  # bold / italic
    text = re.sub(r"`(.+?)`", r"\1", text)                # inline code
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)       # links
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def is_badge(line):
    return re.match(r"^\[!\[.*\]\(.*badge.*\)\]\(.*\)$", line)


def convert(lines):
    out = []
    it = iter(range(len(lines)))
    in_fence = False
    fence_pattern = None
    saw_mermaid = False

    for i in it:
        line = lines[i]

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

        # --- GFM admonitions: convert to Doxygen @-commands ---
        admonition = re.match(r"^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$", line)
        if admonition:
            command = ADMONITION_MAP[admonition.group(1)]
            body_lines = []
            for j in it:  # consume continuation lines
                cont = re.match(r"^>\s?(.*)$", lines[j])
                if not cont:
                    out.append(f"@{command} {' '.join(body_lines).strip()}")
                    out.append(lines[j])
                    break
                if cont.group(1):
                    body_lines.append(cont.group(1))
            else:
                out.append(f"@{command} {' '.join(body_lines).strip()}")
            continue

        # --- Headings: add GitHub-style anchor IDs ---
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading and "{#" not in line:
            hashes, text = heading.groups()
            out.append(f"{hashes} {text} {{#{github_slug(text)}}}")
            continue

        out.append(line)

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
    for line in convert(lines):
        print(line)


if __name__ == "__main__":
    main()
