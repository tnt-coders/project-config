# doxygen-mermaid

Vendored single-file UMD build of [Mermaid](https://mermaid.js.org/) used to render
` ```mermaid ` fences in generated Doxygen HTML (see
`scripts/doxygen-github-markdown-filter.py`, which converts the fences and emits the loader).

- File: `mermaid.min.js`
- Version: 11.6.0 (MIT license)
- Source: `https://cdn.jsdelivr.net/npm/mermaid@11.6.0/dist/mermaid.min.js`

Consumers copy it beside the generated pages via `HTML_EXTRA_FILES` in their Doxyfile. Vendored
(rather than CDN-loaded) so locally built docs render diagrams offline, including over `file://`.
To update: replace the file from the same URL pattern at the new version and update this README.
