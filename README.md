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

`add_subdirectory(project-config)` needs CMake 3.20 or newer (it uses `cmake_path`), and the
preset files use preset schema version 7, which needs CMake 3.27.

---

## CMake Integration

To enable the docs and clang-tidy targets, add `project-config` as a subdirectory in your `CMakeLists.txt`. Two options control which features are enabled:

| Option | Description |
|--------|-------------|
| `PROJECT_CONFIG_ENABLE_DOCS` | Enable `docs` target and install generated HTML docs when Doxygen is available |
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

Provides base configure, build, and test presets for three configurations:

- `default-debug` - Debug build
- `default-release` - Release build
- `default-relwithdebinfo` - Optimized build with debug info, for measuring release-level
  performance locally

Each configure preset builds in `build/<name>`, where `<name>` is the name of your preset that
inherits it, so a preset named `debug` builds in `build/debug`.

### `cmake-presets/conan.json`

Provides Conan package manager integration via [cmake-conan](https://github.com/tnt-coders/cmake-conan). Including this preset sets `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` to load cmake-conan's `conan_provider.cmake`, which hooks into CMake's `find_package` calls to automatically run `conan install` during configuration. Dependencies listed in your `conanfile.txt` or `conanfile.py` are resolved transparently — no changes to your `CMakeLists.txt` are required.

- `conan-debug` - Conan settings for debug builds
- `conan-release` - Conan settings for release builds
- `conan-relwithdebinfo` - Conan settings for RelWithDebInfo builds

Each build tree keeps its own Conan cache: `cmake-presets/conan-provider.cmake`, which loads the
provider, defaults the `CONAN_HOME` cache variable to `.conan2` in the build folder. Set
`-DCONAN_HOME=<path>` to choose another home, or `-DCONAN_HOME=` to leave it to Conan's own
resolution.

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

When `PROJECT_CONFIG_ENABLE_DOCS` is `ON` and [Doxygen](https://www.doxygen.nl/) is found, a `docs`
target generates the project's documentation into `${CMAKE_BINARY_DIR}/docs/html` as part of every
build. It reruns Doxygen only when one of its inputs changes, so a build that touches no documented
file pays nothing for it. The HTML installs to `${CMAKE_INSTALL_DOCDIR}` in the `Development`
component, so API docs ship exactly when a project ships its development files, and never in an
end-user package that leaves `Development` out.

`PROJECT_CONFIG_DOCS_INPUT` is required when the option is `ON`: the folders and files, relative to
the source root, that Doxygen reads. The optional `PROJECT_CONFIG_DOCS_DEPENDS` adds generated
inputs, such as files a Doxyfile `@INCLUDE`s, and the targets that produce them. Set both before
adding `project-config`:

```cmake
set(PROJECT_CONFIG_DOCS_INPUT README.md include)
add_subdirectory(project-config)
```

### Prerequisites

- Doxygen installed and available on `PATH`
- Python 3, which runs the [GitHub Markdown Filter](#github-markdown-filter); with Doxygen found,
  configuring fails without it
- A Doxygen configuration file at one of the following locations (checked in order):
  - `docs/Doxyfile.in` — a CMake template, configured via `configure_file()` with `@ONLY` substitution
  - `docs/Doxyfile` — a static Doxygen configuration file

The call runs Doxygen on a small wrapper Doxyfile that sets the house tags below, then includes
yours, then sets `INPUT`, `OUTPUT_DIRECTORY` and `HTML_OUTPUT`. Doxygen keeps the last assignment
of a tag, so your Doxyfile overrides the house tags, and the call's three tags override your
Doxyfile: delete those three from it, since they no longer decide anything there.

### House Look

Every docs target gets the `project-config` look without its Doxyfile saying so. The house tags
point into `project-config` wherever it sits:

| Tag | House value |
|-----|-------------|
| `HTML_EXTRA_STYLESHEET` | `doxygen-awesome-css/doxygen-awesome.css`, the [doxygen-awesome-css](https://github.com/jothepro/doxygen-awesome-css) theme |
| `HTML_EXTRA_FILES` | `doxygen-mermaid/mermaid.min.js`, which draws the Mermaid diagrams the filter below converts |
| `FILTER_PATTERNS` | `*.md` through the [GitHub Markdown Filter](#github-markdown-filter) |
| `GENERATE_TREEVIEW` | `YES` |
| `GENERATE_LATEX` | `NO` |

Your Doxyfile keeps only its project's own tags. To override a house tag, set it there; to keep
the house value, leave the tag out entirely. A Doxyfile written by `doxygen -g` lists every tag,
even empty ones such as `HTML_EXTRA_FILES =`, and each of those overrides the house value, so
delete the house tags from it. A list tag takes `+=` to add to the house value instead of
replacing it, as in `HTML_EXTRA_STYLESHEET += docs/extra.css`.

The house tags are only ones every Doxygen from 1.10 on reads, since a tag a Doxygen does not know
draws a warning on every run.

You can also use your `README.md` as the Doxygen main page and pull project metadata from CMake variables:

```
PROJECT_NAME           = "@CMAKE_PROJECT_NAME@"
PROJECT_BRIEF          = "@CMAKE_PROJECT_DESCRIPTION@"
USE_MDFILE_AS_MAINPAGE = README.md
```

Since `docs/Doxyfile.in` is processed with `@ONLY` substitution, any `@VAR@` references are replaced with CMake variable values at configure time. Doxygen runs from the source root, so relative paths in the Doxyfile resolve against it.

### Further Documentation Targets

The `docs` target is one call to `project_config_add_docs`, which `project-config` defines for the
consuming project as well. Call it after `add_subdirectory(project-config)` to add another Doxygen
run, such as a user guide beside the API docs:

```cmake
project_config_add_docs(<target> DOXYFILE <file|file.in> OUTPUT_DIR <dir> INPUT <path>...
                        [DEPENDS <dep>...] [DESTINATION <dir>] [COMPONENT <name>])
```

Relative paths follow CMake's usual rule: `DOXYFILE` and `INPUT` resolve against the calling
directory's source folder (`CMAKE_CURRENT_SOURCE_DIR`), `OUTPUT_DIR` against its build folder
(`CMAKE_CURRENT_BINARY_DIR`), as a custom command's output does.

- `DOXYFILE` — the Doxygen configuration. A path ending in `.in` is configured with `@ONLY`
  substitution to a file of the target's own, with the caller's variables in scope.
- `OUTPUT_DIR` — the HTML folder the run writes. It belongs to the target: each run deletes it and
  replaces it with exactly what that run generated, since Doxygen never deletes a page it stops
  generating, so give every docs target a folder of its own. It must be a folder inside
  `CMAKE_BINARY_DIR`, and configuring fails otherwise, so a mistyped path can never delete sources.
- `INPUT` — the folders and files that Doxygen reads. Each must exist when the project is
  configured, since the run depends on every file under them and so repeats exactly when one
  changes. Generated content therefore reaches the run through `DEPENDS` and the Doxyfile's
  `EXAMPLE_PATH` or `@INCLUDE`, never through `INPUT`.
- `DEPENDS` — generated inputs and the targets that produce them.
- `DESTINATION` and `COMPONENT` — where the HTML installs, by default `${CMAKE_INSTALL_DOCDIR}` in
  the `Development` component.

The target is part of every build. Nothing is added when Doxygen is not found, so guard any
dependency on the target with `if(TARGET <target>)`.

### GitHub Markdown Filter

`project-config` includes a Doxygen input filter at `scripts/doxygen-github-markdown-filter.py` that converts GitHub Flavored Markdown into Doxygen-compatible markup. This is useful when using a repository's `README.md` as the Doxygen main page, since GitHub-specific syntax would otherwise be rendered incorrectly or lost.

The filter handles:

- **GFM admonitions** (`> [!NOTE]`, `> [!WARNING]`, etc.) — converted to Doxygen `@note`, `@warning`, and similar commands
- **CI badge lines** — stripped out (they show stale status outside GitHub)
- **Heading anchors** — adds GitHub-style `{#slug}` IDs so fragment links (e.g. `#section-name`) resolve correctly in the generated HTML
- **Mermaid fences** (` ```mermaid `) — converted to diagrams drawn in the browser by the vendored
  `doxygen-mermaid/mermaid.min.js`, so they render offline

The house look runs it on every Markdown input, and only on those, with the Python 3 interpreter
CMake finds.

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

---

## Upgrading from 3768b27

A project pinned at `3768b27` acts on these changes when it moves to the current version:

- **The docs input is stated in CMake.** With `PROJECT_CONFIG_ENABLE_DOCS` on, configuring fails
  unless `PROJECT_CONFIG_DOCS_INPUT` is set, so move the Doxyfile's `INPUT` there. The call sets
  `INPUT`, `OUTPUT_DIRECTORY` and `HTML_OUTPUT` itself, so delete them from the Doxyfile; the HTML
  still lands in `build/<name>/docs/html`.
- **The house look comes from `project-config`.** Delete `HTML_EXTRA_STYLESHEET`,
  `HTML_EXTRA_FILES`, `FILTER_PATTERNS`, `GENERATE_TREEVIEW` and `GENERATE_LATEX` from the
  Doxyfile, empty ones included, so that it keeps only the project's own tags (see
  [House Look](#house-look)).
- **`DOXYGEN_HAVE_DOT` is gone.** `project-config` no longer looks for Graphviz, so
  `HAVE_DOT = @DOXYGEN_HAVE_DOT@` configures to an empty value, which Doxygen silently reads as
  `NO`. Set `HAVE_DOT` in the Doxyfile.
- **Docs build and install by default.** `docs` is part of every build, and its HTML installs to
  `${CMAKE_INSTALL_DOCDIR}` in the `Development` component, so a package that lists its components
  decides whether `Development` ships.
- **The configured Doxyfile moved** from `build/<name>/Doxyfile` to
  `build/<name>/project-config/docs.Doxyfile`, for anything that ran Doxygen on it directly.
- **`CONAN_HOME` is a cache variable,** defaulting to `.conan2` in the build folder, no longer an
  environment variable of the preset. A preset of the project's own that set `CONAN_HOME` in
  `environment` sets it in `cacheVariables` instead.
- **Build folders follow the preset name** (see [Presets](#presets)): presets named `debug` and
  `release` keep their folders, and a preset of any other name moves to `build/<name>`.
