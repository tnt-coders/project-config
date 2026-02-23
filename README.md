# project-config

[![Build](https://github.com/tnt-coders/project-config/actions/workflows/build.yml/badge.svg)](https://github.com/tnt-coders/project-config/actions/workflows/build.yml)

Reusable project configuration and CMake presets that can be shared across projects via Git submodules.

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

These options are not declared by `project-config` itself — the consuming project must define them before calling `add_subdirectory`. If unset, both features are disabled.

```cmake
# Enable desired project-config features
option(PROJECT_CONFIG_ENABLE_DOCS "Enable docs target when Doxygen is available" ON)
option(PROJECT_CONFIG_ENABLE_CLANG_TIDY
       "Enable clang-tidy target when run-clang-tidy is available" ON)

add_subdirectory(project-config)
```

### Conan Packages

`project-config` is a development-only submodule and should **not** be exported as part of a Conan package. Since it won't be present during Conan builds, gate the `add_subdirectory` call behind an option so it can be disabled:

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

## Docs Target

When `PROJECT_CONFIG_ENABLE_DOCS` is `ON` and [Doxygen](https://www.doxygen.nl/) is found, a `docs` target is added that generates API documentation.

### Prerequisites

- Doxygen installed and available on `PATH`
- A Doxygen configuration file at one of the following locations (checked in order):
  - `docs/Doxyfile.in` — a CMake template, configured via `configure_file()` with `@ONLY` substitution
  - `docs/Doxyfile` — a static Doxygen configuration file
- Optionally, [Graphviz](https://graphviz.org/) `dot` for diagram generation

### Shared Doxygen Theme

`project-config` includes [doxygen-awesome-css](https://github.com/jothepro/doxygen-awesome-css) as a submodule. Projects that reference its stylesheet in their Doxygen configuration will get the theme automatically.

### GitHub Markdown Filter

`project-config` includes a Doxygen input filter at `scripts/doxygen-github-markdown-filter.py` that converts GitHub Flavored Markdown into Doxygen-compatible markup. This is useful when using a repository's `README.md` as the Doxygen main page, since GitHub-specific syntax would otherwise be rendered incorrectly or lost.

The filter handles:

- **GFM admonitions** (`> [!NOTE]`, `> [!WARNING]`, etc.) — converted to Doxygen `@note`, `@warning`, and similar commands
- **CI badge lines** — stripped out (they show stale status outside GitHub)
- **Heading anchors** — adds GitHub-style `{#slug}` IDs so fragment links (e.g. `#section-name`) resolve correctly in the generated HTML

To use it, set `INPUT_FILTER` in your `Doxyfile.in` to run the script on Markdown files:

```
INPUT_FILTER = "python @PROJECT_SOURCE_DIR@/project-config/scripts/doxygen-github-markdown-filter.py"
```

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
- On Windows: Python 3 (used to invoke `run-clang-tidy` which is a Python script)

### Usage

```bash
cmake --build build/debug --target clang-tidy
cmake --build build/debug --target clang-tidy-fix
```

> [!NOTE]
> `CMAKE_EXPORT_COMPILE_COMMANDS` is automatically set to `ON` when clang-tidy targets are enabled.

---

## Presets

The default presets use the [Ninja](https://ninja-build.org/) generator.

### `cmake-presets/default.json`

Provides base configure, build, and test presets for debug and release configurations:

- `default-debug` - Debug build with output in `build/debug`
- `default-release` - Release build with output in `build/release`

### `cmake-presets/conan.json`

Provides Conan package manager integration via [cmake-conan](https://github.com/tnt-coders/cmake-conan):

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
