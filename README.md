# cmake-config

Reusable CMake preset configurations that can be shared across projects via Git submodules.

## Setup

Add this repository as a submodule in your project root:

```bash
git submodule add https://github.com/tnt-coders/cmake-config.git
```

The submodule must be checked out before CMake configuration runs, since `CMakePresets.json` includes are resolved at configure time.

## Available Presets

### `presets/default.json`

Provides base configure, build, and test presets for debug and release configurations:

- `default-debug` - Debug build with output in `build/debug`
- `default-release` - Release build with output in `build/release`

### `presets/conan.json`

Provides Conan package manager integration via [cmake-conan](https://github.com/tnt-coders/cmake-conan):

- `conan-debug` - Conan settings for debug builds
- `conan-release` - Conan settings for release builds

## Usage

Include the desired preset files in your project's `CMakePresets.json` and inherit from them.

### Basic Example (without Conan)

```json
{
  "version": 7,
  "include": [
    "cmake-config/presets/default.json"
  ],
  "configurePresets": [
    {
      "name": "debug",
      "inherits": ["default-debug"]
    },
    {
      "name": "release",
      "inherits": ["default-release"]
    }
  ],
  "buildPresets": [
    {
      "name": "debug",
      "inherits": ["default-debug"]
    },
    {
      "name": "release",
      "inherits": ["default-release"]
    }
  ],
  "testPresets": [
    {
      "name": "debug",
      "inherits": ["default-debug"]
    },
    {
      "name": "release",
      "inherits": ["default-release"]
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
    "cmake-config/presets/default.json",
    "cmake-config/presets/conan.json"
  ],
  "configurePresets": [
    {
      "name": "debug",
      "inherits": ["default-debug", "conan-debug"]
    },
    {
      "name": "release",
      "inherits": ["default-release", "conan-release"]
    }
  ],
  "buildPresets": [
    {
      "name": "debug",
      "inherits": ["default-debug", "conan-debug"]
    },
    {
      "name": "release",
      "inherits": ["default-release", "conan-release"]
    }
  ],
  "testPresets": [
    {
      "name": "debug",
      "inherits": ["default-debug", "conan-debug"]
    },
    {
      "name": "release",
      "inherits": ["default-release", "conan-release"]
    }
  ]
}
```
