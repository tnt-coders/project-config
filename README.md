# project-config

[![Build](https://github.com/tnt-music-studios/project-config/actions/workflows/build.yml/badge.svg)](https://github.com/tnt-music-studios/project-config/actions/workflows/build.yml)

Reusable project configuration and CMake presets that can be shared across projects via Git submodules. Bundles two key submodules:

- [**cmake-conan**](https://github.com/tnt-music-studios/cmake-conan) — A CMake dependency provider for the [Conan](https://conan.io/) C/C++ package manager. Automatically runs `conan install` during CMake configuration so dependencies are resolved without any changes to your `CMakeLists.txt`. Supports building private package recipes directly from Git when packages aren't available on a remote.
- [**doxygen-awesome-css**](https://github.com/jothepro/doxygen-awesome-css) — A modern, professional theme for [Doxygen](https://www.doxygen.nl/)-generated documentation, with a clean responsive layout that follows the system's dark mode. `project-config` applies its stylesheet to every docs target; the theme's optional JavaScript extensions, such as code copy buttons and an interactive table of contents, are left to a Doxyfile that wants them.

By adding `project-config` as a single submodule, your project gains Conan package management, professional documentation, linting targets, and standardized CMake presets with minimal setup.

## Setup

Add this repository as a submodule named `project-config` at your project root, then check out
its own submodules:

```bash
git submodule add https://github.com/tnt-music-studios/project-config.git
git submodule update --init --recursive
```

The folder must be `<repo>/project-config`: `conan.json` loads its provider from
`${sourceDir}/project-config`, and the examples below include the preset files and add the
subdirectory by that path. The submodule must be checked out before CMake configuration runs,
since `CMakePresets.json` includes its preset files at configure time. Its own submodules must be
checked out too: the Conan provider loads `cmake-conan`, and the house documentation look reads
`doxygen-awesome-css` (the Mermaid script in `doxygen-mermaid` is part of `project-config`
itself).

`add_subdirectory(project-config)` needs CMake 3.21 or newer (it sets policy `CMP0126`), and the
preset files use preset schema version 7, which needs CMake 3.27.

---

## CMake Integration

To enable the docs and clang-tidy targets, add `project-config` as a subdirectory in your `CMakeLists.txt`. Two options control which features are enabled:

| Option | Description |
|--------|-------------|
| `PROJECT_CONFIG_ENABLE_DOCS` | Enable `docs` target and install generated HTML docs when Doxygen is available |
| `PROJECT_CONFIG_ENABLE_CLANG_TIDY` | Enable `clang-tidy` and `clang-tidy-fix` targets when `run-clang-tidy` is available |

These options are not declared by `project-config` itself — the consuming project must define them before calling `add_subdirectory`. If unset, both features are disabled. Each feature reads further variables, described in the [Docs Target](#docs-target) and [Clang-Tidy Targets](#clang-tidy-targets) sections; the docs target requires `PROJECT_CONFIG_DOCS_INPUT`.

```cmake
# Enable desired project-config features
option(PROJECT_CONFIG_ENABLE_DOCS "Enable docs target when Doxygen is available" ON)
option(PROJECT_CONFIG_ENABLE_CLANG_TIDY
       "Enable clang-tidy target when run-clang-tidy is available" ON)
set(PROJECT_CONFIG_DOCS_INPUT README.md include)

add_subdirectory(project-config)
```

### Excluding from Conan Builds and Parent Projects

`project-config` is a development-only submodule and should **not** be exported as part of a Conan package. If you plan to export your project as a Conan package, gate the `add_subdirectory` call behind an option so it can be disabled during Conan builds.

Gate it on `PROJECT_IS_TOP_LEVEL` as well when another project may add yours as a subproject
(`add_subdirectory` or `FetchContent`). `project-config` reads the top-level source and build trees,
so a second copy run from inside another project resolves its docs input against the wrong root and
defines its targets twice. The option alone cannot tell: every project that copies this block shares
the one `INCLUDE_PROJECT_CONFIG` cache entry, which the outer project has already set.

**CMakeLists.txt:**

```cmake
option(INCLUDE_PROJECT_CONFIG "Include project-config for docs, linting, and CMake presets" ON)
if(PROJECT_IS_TOP_LEVEL AND INCLUDE_PROJECT_CONFIG)
    option(PROJECT_CONFIG_ENABLE_DOCS "Enable docs target when Doxygen is available" ON)
    option(PROJECT_CONFIG_ENABLE_CLANG_TIDY
           "Enable clang-tidy target when run-clang-tidy is available" ON)
    set(PROJECT_CONFIG_DOCS_INPUT README.md include)

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

The default presets use the [Ninja](https://ninja-build.org/) generator, which must be on `PATH`. Ninja is used because it can write a `compile_commands.json` compilation database on every platform, which clang-tidy and other tooling need; the Visual Studio generators cannot. This ensures consistent cross-platform behavior without relying on generator-specific workarounds.

### `cmake-presets/default.json`

Provides base configure, build, and test presets for three configurations:

- `default-debug` - Debug build
- `default-release` - Release build
- `default-relwithdebinfo` - Optimized build with debug info, for measuring release-level
  performance locally

Each configure preset builds in `build/<name>`, where `<name>` is the name of your preset that
inherits it, so a preset named `debug` builds in `build/debug`.

### `cmake-presets/conan.json`

Provides Conan package manager integration via [cmake-conan](https://github.com/tnt-music-studios/cmake-conan). Including this preset sets `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` to `cmake-presets/conan-provider.cmake`, which loads cmake-conan's `conan_provider.cmake`; that provider hooks into CMake's `find_package` calls to automatically run `conan install` during configuration. Dependencies listed in your `conanfile.txt` or `conanfile.py` are resolved transparently — no changes to your `CMakeLists.txt` are required. It needs Conan 2.0.5 or newer and Git at configure time.

- `conan-debug` - Conan settings for debug builds
- `conan-release` - Conan settings for release builds
- `conan-relwithdebinfo` - Conan settings for RelWithDebInfo builds

Each installs packages for its one configuration (`Debug`, `Release` or `RelWithDebInfo`), with
`CONAN_INSTALL_ARGS` set to
`--build=missing`, so packages without a matching binary build from source, and to
`-c tools.cmake.cmaketoolchain:user_presets=False`, so Conan writes no `CMakeUserPresets.json` into
the source tree. A project that sets `CONAN_INSTALL_ARGS` itself replaces both.

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

Including the `conan.json` presets automatically integrates [cmake-conan](https://github.com/tnt-music-studios/cmake-conan) into the project for dependency management.

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

`PROJECT_CONFIG_DOCS_INPUT` is required when the option is `ON`: the folders and files that Doxygen
reads, as absolute paths or relative to the source root. The optional `PROJECT_CONFIG_DOCS_DEPENDS` adds generated
inputs, such as files a Doxyfile `@INCLUDE`s, and the targets that produce them; name files in it
by absolute path, since `project-config` passes it on from its own folder, which is where a
relative path would resolve. Set both before adding `project-config`:

```cmake
set(PROJECT_CONFIG_DOCS_INPUT README.md include)
add_subdirectory(project-config)
```

### Prerequisites

- Doxygen 1.9.6 or newer, installed and available on `PATH`: the house tags need 1.9.5, and the
  theme does not support that one release
- Python 3, which runs the [GitHub Markdown Filter](#github-markdown-filter); with Doxygen found,
  configuring fails without it
- A Doxygen configuration file at one of the following locations (checked in order):
  - `docs/Doxyfile.in` — a CMake template, configured via `configure_file()` with `@ONLY` substitution
  - `docs/Doxyfile` — a static Doxygen configuration file

The call runs Doxygen on a small wrapper Doxyfile that sets the house tags below, then includes
yours, then sets `INPUT`, `OUTPUT_DIRECTORY` and `HTML_OUTPUT`. Doxygen keeps the last assignment
of a tag, so your Doxyfile overrides the house tags, and the call's three tags override your
Doxyfile: delete those three from it, since they no longer decide anything there. Every other
tag, such as `RECURSIVE`, `FILE_PATTERNS` and `EXCLUDE`, stays with your Doxyfile.

### House Look

Every docs target gets the `project-config` look without its Doxyfile saying so. The house tags
point into `project-config` wherever it sits:

| Tag | House value |
|-----|-------------|
| `HTML_EXTRA_STYLESHEET` | `doxygen-awesome-css/doxygen-awesome.css`, the [doxygen-awesome-css](https://github.com/jothepro/doxygen-awesome-css) theme |
| `HTML_COLORSTYLE` | `LIGHT`, which the theme requires in place of Doxygen's default `AUTO_LIGHT`; the theme still follows the system's dark mode itself |
| `HTML_EXTRA_FILES` | `doxygen-mermaid/mermaid.min.js`, which draws the Mermaid diagrams the filter below converts |
| `FILTER_PATTERNS` | `*.md` through the [GitHub Markdown Filter](#github-markdown-filter) |
| `GENERATE_TREEVIEW` | `YES` |
| `GENERATE_LATEX` | `NO` |
| `HAVE_DOT` | `NO`, stated because Doxygen's default differs by build: Ubuntu's draws graphs, the others do not. Set `HAVE_DOT = YES` in your Doxyfile to draw them, with Graphviz's `dot` on `PATH` wherever the docs build |

Your Doxyfile keeps only its project's own tags. To override a house tag, set it there; to keep
the house value, leave the tag out entirely. A Doxyfile written by `doxygen -g` lists every tag,
even empty ones such as `HTML_EXTRA_FILES =`, and each of those overrides the house value, so
delete the house tags from it. A list tag takes `+=` to add to the house value instead of
replacing it, as in `HTML_EXTRA_STYLESHEET += docs/extra.css`.

The house tags are only ones every Doxygen from 1.9.5 on reads, since a tag a Doxygen does not know
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
consuming project as well, whatever `PROJECT_CONFIG_ENABLE_DOCS` says. Call it after
`add_subdirectory(project-config)` to add another Doxygen run, such as a user guide beside the API
docs:

```cmake
project_config_add_docs(<target> DOXYFILE <file|file.in> OUTPUT_DIR <dir> INPUT <path>...
                        [DEPENDS <dep>...] [DESTINATION <dir>] [COMPONENT <name>])
```

Relative paths follow CMake's usual rule: `DOXYFILE` and `INPUT` resolve against the calling
directory's source folder (`CMAKE_CURRENT_SOURCE_DIR`), `OUTPUT_DIR` against its build folder
(`CMAKE_CURRENT_BINARY_DIR`), as a custom command's output does.

- `DOXYFILE` — the Doxygen configuration. A path ending in `.in` is configured with `@ONLY`
  substitution to a file of the target's own, with the caller's variables in scope. It gets the
  house look and the wrapper exactly as the `docs` target's Doxyfile does, and Doxygen runs from the
  source root, so relative paths inside it resolve against that root, not the calling folder.
- `OUTPUT_DIR` — the HTML folder the run writes. It belongs to the target: each run deletes it and
  replaces it with exactly what that run generated, since Doxygen never deletes a page it stops
  generating, so give every docs target a folder of its own. It must be a folder inside
  `CMAKE_BINARY_DIR`, and configuring fails otherwise, so a mistyped path can never delete sources.
  The target records the folder, as an absolute path, in its `PROJECT_CONFIG_DOCS_OUTPUT_DIR`
  property, so code that copies or links to the HTML reads it with `get_target_property` instead of
  restating the path.
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
- **Heading anchors** — gives each heading its GitHub slug as an ID, numbering a repeated heading
  on one page as GitHub does. Doxygen's IDs are global to the site, so each ID is qualified by the
  page's path, and the filter rewrites the links that name a heading, `[x](#slug)` on the same
  page and `[x](other.md#slug)` across pages, to match; the source still reads correctly on
  GitHub. A heading that states its own `{#id}` keeps it: link to it with Doxygen's `\ref id`,
  since the filter reads every `#...` link as a GitHub slug.
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
| `clang-tidy` | Run clang-tidy on every file in `compile_commands.json` that matches `PROJECT_CONFIG_CLANG_TIDY_FILE_REGEX` and report diagnostics |
| `clang-tidy-fix` | Run clang-tidy the same way and automatically apply suggested fixes |

### Prerequisites

- `run-clang-tidy` installed and available on `PATH` (ships with LLVM/Clang)
- A `.clang-tidy` configuration file at the project root; without one, configuring warns and adds
  neither target
- A generator that writes `compile_commands.json`, such as the Ninja of the default
  [Presets](#presets); `project-config` turns the database on (see the note below)
- On Windows: Python 3 (used to invoke `run-clang-tidy` which is a Python script); configuring
  fails without it

### Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_CONFIG_CLANG_TIDY_FILE_REGEX` | `[.](c\|cc\|cpp\|cxx\|m\|mm)$` | The file regex `run-clang-tidy` selects files with (Python `re.search` over each path). The default takes C, C++ and Objective-C sources, since the compile database also lists files clang-tidy cannot parse, such as a Windows resource script |
| `PROJECT_CONFIG_CLANG_TIDY_EXTRA_ARGS` | the two flags below | Additional arguments passed to `run-clang-tidy` |

Set them with a plain `set()` before adding `project-config`, or as cache entries on the command
line or in a preset's `cacheVariables`. A value of
`PROJECT_CONFIG_CLANG_TIDY_EXTRA_ARGS` replaces the defaults, so keep them in it where they still
apply. On macOS, the SDK path from `xcrun --show-sdk-path` is also passed as `--sysroot`, so
Homebrew LLVM's clang-tidy finds the system headers.

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
> A target takes that setting when it is created, so add `project-config` before the project's own
> targets; one created earlier is missing from `compile_commands.json` until the next configure.

---

## Upgrading from 3768b27

A project pinned at `3768b27` acts on these changes when it moves to the current version:

- **The docs input is stated in CMake.** With `PROJECT_CONFIG_ENABLE_DOCS` on, configuring fails
  unless `PROJECT_CONFIG_DOCS_INPUT` is set, so move the Doxyfile's `INPUT` there. The call sets
  `INPUT`, `OUTPUT_DIRECTORY` and `HTML_OUTPUT` itself, so delete them from the Doxyfile; the HTML
  still lands in `build/<name>/docs/html`.
- **The house look comes from `project-config`.** Delete `HTML_EXTRA_STYLESHEET`,
  `HTML_COLORSTYLE`, `HTML_EXTRA_FILES`, `FILTER_PATTERNS`, `GENERATE_TREEVIEW` and
  `GENERATE_LATEX` from the Doxyfile, empty ones included, so that it keeps only the project's own
  tags (see [House Look](#house-look)). A Doxyfile written by `doxygen -g` sets `HTML_COLORSTYLE`
  to `AUTO_LIGHT`, which the theme does not support.
- **CMake 3.21 or newer** runs `add_subdirectory(project-config)`, which now sets policy
  `CMP0126`, so a plain `set()` of its clang-tidy variables takes effect on the first configure.
- **Gate `project-config` on `PROJECT_IS_TOP_LEVEL`** in a project that others may add as a
  subproject (see [Excluding from Conan Builds and Parent Projects](#excluding-from-conan-builds-and-parent-projects)).
- **`DOXYGEN_HAVE_DOT` is gone.** `project-config` no longer looks for Graphviz, and the house
  look turns graphs off, so delete `HAVE_DOT = @DOXYGEN_HAVE_DOT@` from the Doxyfile. To keep
  graphs, set `HAVE_DOT = YES` there instead.
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
- **clang-tidy checks only C, C++ and Objective-C sources by default.** The default
  `PROJECT_CONFIG_CLANG_TIDY_FILE_REGEX` was `.*`, which also handed clang-tidy the Windows
  resource script an executable's compile database lists; a project with sources of other
  extensions sets the variable itself.
- **Recipe annotations are read more strictly** by the bundled `cmake-conan`: a commented-out
  requirement no longer has its recipe created, and an annotation it cannot use (on a tool
  requirement, on a reference built at runtime, or with a URL that does not end in `.git`) draws a
  warning where it was skipped or misread before.
