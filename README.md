# project-config

[![Build](https://github.com/tnt-coders/project-config/actions/workflows/build.yml/badge.svg)](https://github.com/tnt-coders/project-config/actions/workflows/build.yml)

Reusable project configuration and CMake presets that can be shared across projects via Git submodules. Bundles two key submodules:

- [**cmake-conan**](https://github.com/tnt-coders/cmake-conan) — A CMake dependency provider for the [Conan](https://conan.io/) C/C++ package manager. Automatically runs `conan install` during CMake configuration so dependencies are resolved without any changes to your `CMakeLists.txt`. Supports building private package recipes directly from Git when packages aren't available on a remote.
- [**doxygen-awesome-css**](https://github.com/jothepro/doxygen-awesome-css) — A modern, professional theme for [Doxygen](https://www.doxygen.nl/)-generated documentation. Provides a clean responsive layout with dark mode support, code fragment copy buttons, and an interactive table of contents.

By adding `project-config` as a single submodule, your project gains Conan package management, professional documentation, linting targets, and standardized CMake presets with minimal setup.

## Setup

Add this repository as a submodule in your project root:

```bash
git submodule add https://github.com/tnt-coders/project-config.git
```

The submodule must be checked out before CMake configuration runs, since `CMakePresets.json` includes are resolved at configure time.

---

## CMake Integration

To enable the docs and clang-tidy targets, add `project-config` as a subdirectory in your `CMakeLists.txt`. Two options control which features are enabled:

| Option | Description |
|--------|-------------|
| `PROJECT_CONFIG_ENABLE_DOCS` | Enable `docs` target when Doxygen is available |
| `PROJECT_CONFIG_ENABLE_CLANG_TIDY` | Enable `clang-tidy` and `clang-tidy-fix` targets when `run-clang-tidy` is available |
| `PROJECT_CONFIG_CLANG_TIDY_EXTRA_ARGS` | Additional arguments passed to `run-clang-tidy` |

These options are not declared by `project-config` itself — the consuming project must define them before calling `add_subdirectory`. If unset, both features are disabled.

```cmake
# Enable desired project-config features
option(PROJECT_CONFIG_ENABLE_DOCS "Enable docs target when Doxygen is available" ON)
option(PROJECT_CONFIG_ENABLE_CLANG_TIDY
       "Enable clang-tidy target when run-clang-tidy is available" ON)

add_subdirectory(project-config)
```

### Excluding from Conan Builds

`project-config` is a development-only submodule and should **not** be exported as part of a Conan package. If you plan to export your project as a Conan package, gate the `add_subdirectory` call behind an option so it can be disabled during Conan builds:

**CMakeLists.txt:**

```cmake
option(INCLUDE_PROJECT_CONFIG "Include project-config for docs, linting, and CMake presets" ON)
if(INCLUDE_PROJECT_CONFIG)
    option(PROJECT_CONFIG_ENABLE_DOCS "Enable docs target when Doxygen is available" ON)
    option(PROJECT_CONFIG_ENABLE_CLANG_TIDY
           "Enable clang-tidy target when run-clang-tidy is available" ON)

    add_subdirectory(project-config)
endif()
```

**conanfile.py:**

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.variables["INCLUDE_PROJECT_CONFIG"] = False
    tc.generate()
```

---

## Presets

The default presets use the [Ninja](https://ninja-build.org/) generator. Ninja is used because it natively generates a `compile_commands.json` compilation database on all platforms, which is required by clang-tidy and other tooling. This ensures consistent cross-platform behavior without relying on generator-specific workarounds.

### `cmake-presets/default.json`

Provides base configure, build, and test presets for debug and release configurations:

- `default-debug` - Debug build with output in `build/debug`
- `default-release` - Release build with output in `build/release`

### `cmake-presets/conan.json`

Provides Conan package manager integration via [cmake-conan](https://github.com/tnt-coders/cmake-conan). Including this preset sets `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` to point to `conan_provider.cmake`, which hooks into CMake's `find_package` calls to automatically run `conan install` during configuration. Dependencies listed in your `conanfile.txt` or `conanfile.py` are resolved transparently — no changes to your `CMakeLists.txt` are required.

- `conan-debug` - Conan settings for debug builds
- `conan-release` - Conan settings for release builds

### Usage

Include the desired preset files in your project's `CMakePresets.json` and inherit from them.

### Basic Example

```json
{
  "version": 7,
  "include": [
    "project-config/cmake-presets/default.json"
  ],
  "configurePresets": [
    {
      "name": "debug",
      "inherits": [
        "default-debug"
      ]
    },
    {
      "name": "release",
      "inherits": [
        "default-release"
      ]
    }
  ],
  "buildPresets": [
    {
      "name": "debug",
      "configurePreset": "debug",
      "inherits": [
        "default-debug"
      ]
    },
    {
      "name": "release",
      "configurePreset": "release",
      "inherits": [
        "default-release"
      ]
    }
  ],
  "testPresets": [
    {
      "name": "debug",
      "configurePreset": "debug",
      "inherits": [
        "default-debug"
      ]
    },
    {
      "name": "release",
      "configurePreset": "release",
      "inherits": [
        "default-release"
      ]
    }
  ]
}
```

### Example with Conan

Including the `conan.json` presets automatically integrates [cmake-conan](https://github.com/tnt-coders/cmake-conan) into the project for dependency management.

```json
{
  "version": 7,
  "include": [
    "project-config/cmake-presets/default.json",
    "project-config/cmake-presets/conan.json"
  ],
  "configurePresets": [
    {
      "name": "debug",
      "inherits": [
        "default-debug",
        "conan-debug"
      ]
    },
    {
      "name": "release",
      "inherits": [
        "default-release",
        "conan-release"
      ]
    }
  ],
  "buildPresets": [
    {
      "name": "debug",
      "configurePreset": "debug",
      "inherits": [
        "default-debug",
        "conan-debug"
      ]
    },
    {
      "name": "release",
      "configurePreset": "release",
      "inherits": [
        "default-release",
        "conan-release"
      ]
    }
  ],
  "testPresets": [
    {
      "name": "debug",
      "configurePreset": "debug",
      "inherits": [
        "default-debug",
        "conan-debug"
      ]
    },
    {
      "name": "release",
      "configurePreset": "release",
      "inherits": [
        "default-release",
        "conan-release"
      ]
    }
  ]
}
```

---

## Docs Target

When `PROJECT_CONFIG_ENABLE_DOCS` is `ON` and [Doxygen](https://www.doxygen.nl/) is found, a `docs` target is added that generates API documentation.

### Prerequisites

- Doxygen installed and available on `PATH`
- A Doxygen configuration file at one of the following locations (checked in order):
  - `docs/Doxyfile.in` — a CMake template, configured via `configure_file()` with `@ONLY` substitution
  - `docs/Doxyfile` — a static Doxygen configuration file
- Optionally, [Graphviz](https://graphviz.org/) `dot` for diagram generation

### Shared Doxygen Theme

`project-config` includes [doxygen-awesome-css](https://github.com/jothepro/doxygen-awesome-css) as a submodule. To use the theme, set the following in your `docs/Doxyfile.in`:

```
# Use doxygen-awesome-css theme
HTML_EXTRA_STYLESHEET  = project-config/doxygen-awesome-css/doxygen-awesome.css

# Recommended settings for doxygen-awesome-css
HTML_COLORSTYLE        = AUTO_LIGHT
DISABLE_INDEX          = NO
GENERATE_TREEVIEW      = YES
PAGE_OUTLINE_PANEL     = YES
FULL_SIDEBAR           = NO
```

These settings enable the sidebar navigation tree, a per-page outline panel, and automatic light/dark mode switching based on the user's system preference. The theme is included as part of the `project-config` submodule, so no additional setup is required.

You can also use your `README.md` as the Doxygen main page and pull project metadata from CMake variables:

```
PROJECT_NAME           = "@CMAKE_PROJECT_NAME@"
PROJECT_BRIEF          = "@CMAKE_PROJECT_DESCRIPTION@"
OUTPUT_DIRECTORY       = @CMAKE_BINARY_DIR@/docs

INPUT                  = include/mylib \
                         README.md
USE_MDFILE_AS_MAINPAGE = README.md
```

Since `docs/Doxyfile.in` is processed with `@ONLY` substitution, any `@VAR@` references are replaced with CMake variable values at configure time.

### GitHub Markdown Filter

`project-config` includes a Doxygen input filter at `scripts/doxygen-github-markdown-filter.py` that converts GitHub Flavored Markdown into Doxygen-compatible markup. This is useful when using a repository's `README.md` as the Doxygen main page, since GitHub-specific syntax would otherwise be rendered incorrectly or lost.

The filter handles:

- **GFM admonitions** (`> [!NOTE]`, `> [!WARNING]`, etc.) — converted to Doxygen `@note`, `@warning`, and similar commands
- **CI badge lines** — stripped out (they show stale status outside GitHub)
- **Heading anchors** — adds GitHub-style `{#slug}` IDs so fragment links (e.g. `#section-name`) resolve correctly in the generated HTML

To use it, set `FILTER_PATTERNS` in your `Doxyfile.in` to run the script on Markdown files:

```
FILTER_PATTERNS = *.md="python @CMAKE_SOURCE_DIR@/project-config/scripts/doxygen-github-markdown-filter.py"
```

Using `FILTER_PATTERNS` rather than `INPUT_FILTER` ensures the filter only runs on Markdown files, leaving source code and other inputs unaffected.

### Usage

```bash
cmake --build build/debug --target docs
```

---

## Clang-Tidy Targets

When `PROJECT_CONFIG_ENABLE_CLANG_TIDY` is `ON` and `run-clang-tidy` is found, two targets are added:

| Target | Description |
|--------|-------------|
| `clang-tidy` | Run clang-tidy on all source files and report diagnostics |
| `clang-tidy-fix` | Run clang-tidy and automatically apply suggested fixes |

### Prerequisites

- `run-clang-tidy` installed and available on `PATH` (ships with LLVM/Clang)
- A `.clang-tidy` configuration file at the project root
- A `compile_commands.json` compilation database (automatically generated when using the default [Presets](#presets), which use the Ninja generator)
- On Windows: Python 3 (used to invoke `run-clang-tidy` which is a Python script)

By default, `PROJECT_CONFIG_CLANG_TIDY_EXTRA_ARGS` passes two defensive Clang parser flags:

- `-extra-arg=-Wno-unknown-warning-option`: keeps clang-tidy from failing on warning flags that
  are valid for the compiler recorded in `compile_commands.json` but unknown to Clang's parser.
- `-extra-arg=-Wno-unused-command-line-argument`: keeps clang-tidy from failing on build or codegen
  flags that are legitimate for the recorded compiler but unused during clang-tidy's AST analysis.
  This commonly applies to MSVC flags such as `/MP` and `/GL`.

These arguments affect only clang-tidy's replay of `compile_commands.json`. They do not remove or
weaken the flags used by the real build.

### Usage

```bash
cmake --build build/debug --target clang-tidy
cmake --build build/debug --target clang-tidy-fix
```

> [!NOTE]
> `CMAKE_EXPORT_COMPILE_COMMANDS` is automatically set to `ON` when clang-tidy targets are enabled.
