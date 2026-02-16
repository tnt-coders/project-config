# Find doxygen
find_package(Doxygen QUIET)

# If docs exist for the current project and doxygen is found, add docs target
if (DOXYGEN_FOUND AND EXISTS "${CMAKE_SOURCE_DIR}/docs/Doxyfile")
add_custom_target(
        docs
        COMMAND ${DOXYGEN_EXECUTABLE} ${CMAKE_SOURCE_DIR}/docs/Doxyfile
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Generating API documentation with Doxygen"
        VERBATIM)
else()
    message(STATUS "Project-Config: doxygen or docs/Doxyfile not found, skipping docs target")
endif()

# Find clang-tidy
find_program(RUN_CLANG_TIDY_PROGRAM run-clang-tidy)

# If clang-tidy exists and the project has a config file, add clang-tidy targets
if(RUN_CLANG_TIDY_PROGRAM AND EXISTS "${CMAKE_SOURCE_DIR}/.clang-tidy")
    set(CMAKE_EXPORT_COMPILE_COMMANDS
        ON
        CACHE BOOL "Generate compile_commands.json for clang-tidy" FORCE)

    # On Windows, run-clang-tidy is a Python script that can't be executed directly
    set(RUN_CLANG_TIDY_COMMAND "${RUN_CLANG_TIDY_PROGRAM}")
    if(WIN32)
        find_package(
            Python3
            COMPONENTS Interpreter
            QUIET
            REQUIRED)
        set(RUN_CLANG_TIDY_COMMAND "${Python3_EXECUTABLE}" "${RUN_CLANG_TIDY_PROGRAM}")
    endif()

    # On Apple platforms, Homebrew LLVM's clang-tidy needs the SDK sysroot to find system headers
    set(CLANG_TIDY_EXTRA_ARGS "")
    if(APPLE)
        execute_process(
            COMMAND xcrun --show-sdk-path
            OUTPUT_VARIABLE APPLE_SDK_PATH
            OUTPUT_STRIP_TRAILING_WHITESPACE)
        if(APPLE_SDK_PATH)
            set(CLANG_TIDY_EXTRA_ARGS "-extra-arg=--sysroot=${APPLE_SDK_PATH}")
        endif()
    endif()

    # Add a target to run clang-tidy
    add_custom_target(
        clang-tidy
        COMMAND ${RUN_CLANG_TIDY_COMMAND} -p "${CMAKE_BINARY_DIR}" ${CLANG_TIDY_EXTRA_ARGS}
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        COMMENT "Running clang-tidy"
        USES_TERMINAL)

    # Add a target to run clang-tidy and apply fixes
    add_custom_target(
        clang-tidy-fix
        COMMAND ${RUN_CLANG_TIDY_COMMAND} -p "${CMAKE_BINARY_DIR}" ${CLANG_TIDY_EXTRA_ARGS} -fix
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        COMMENT "Running clang-tidy with fixes"
        USES_TERMINAL)
else()
    message(STATUS "Project-Config: run-clang-tidy or .clang-tidy not found, skipping clang-tidy targets")
endif()
