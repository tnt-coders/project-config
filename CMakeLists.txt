list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
set(CMAKE_MODULE_PATH
    "${CMAKE_MODULE_PATH}"
    PARENT_SCOPE)
include(GNUInstallDirs)

# Adds <target>, which brings OUTPUT_DIR up to date with a Doxygen run over DOXYFILE in every build:
#
# ~~~
# project_config_add_docs(<target> DOXYFILE <file|file.in> OUTPUT_DIR <dir> INPUT <path>...
#                         [DEPENDS <dep>...] [DESTINATION <dir>] [COMPONENT <name>])
# ~~~
#
# Relative paths follow CMake's usual rule: DOXYFILE and INPUT resolve against the calling
# directory's source folder, OUTPUT_DIR against its build folder.
#
# INPUT names the folders and files Doxygen reads, each of which must exist at configure time, and
# the run depends on every file under them, so a build reruns Doxygen exactly when one of them
# changes. DEPENDS adds generated inputs and the targets that produce them. The call states Doxygen's
# INPUT, OUTPUT_DIRECTORY and HTML_OUTPUT itself, overriding any the Doxyfile sets. A DOXYFILE ending
# in .in is configured with @ONLY substitution, with the caller's variables in scope.
#
# OUTPUT_DIR belongs to the target: every run deletes it and replaces it with exactly what that run
# generated, so it must lie inside the build tree and be a folder of its own, never one that holds
# another docs target's folder. The HTML installs to DESTINATION, by default the
# docdir, in COMPONENT, by default Development, so API docs ship with a project's development files
# and never in an end-user package.
#
# Nothing is added when Doxygen is not found, so callers guard with if(TARGET <target>).
function(project_config_add_docs target)
    cmake_parse_arguments(PARSE_ARGV 1 arg "" "DOXYFILE;OUTPUT_DIR;DESTINATION;COMPONENT"
                          "INPUT;DEPENDS")
    if(DEFINED arg_UNPARSED_ARGUMENTS
       OR NOT DEFINED arg_DOXYFILE
       OR NOT DEFINED arg_OUTPUT_DIR
       OR NOT DEFINED arg_INPUT)
        message(FATAL_ERROR "project_config_add_docs(${target}) takes DOXYFILE, OUTPUT_DIR and "
                            "INPUT, and only the optional arguments it documents.")
    endif()

    # Checked before Doxygen is looked for, so a bad call fails on every machine. Each run deletes
    # OUTPUT_DIR, so it must be a named folder whose parent lies in the build tree; one anywhere
    # else could take sources, or the whole build, with it.
    cmake_path(ABSOLUTE_PATH arg_OUTPUT_DIR BASE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}" NORMALIZE
               OUTPUT_VARIABLE output_dir)
    cmake_path(GET output_dir PARENT_PATH output_parent)
    cmake_path(GET output_dir FILENAME output_leaf)
    cmake_path(IS_PREFIX CMAKE_BINARY_DIR "${output_parent}" NORMALIZE output_in_build)
    if(NOT output_in_build OR output_leaf STREQUAL "")
        message(FATAL_ERROR "project_config_add_docs(${target}): OUTPUT_DIR ${output_dir} is not "
                            "a folder inside the build tree ${CMAKE_BINARY_DIR}.")
    endif()

    set(input_paths "")
    set(input_files "")
    foreach(input IN LISTS arg_INPUT)
        cmake_path(ABSOLUTE_PATH input BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" NORMALIZE
                   OUTPUT_VARIABLE input_path)
        if(IS_DIRECTORY "${input_path}")
            file(GLOB_RECURSE folder_files CONFIGURE_DEPENDS "${input_path}/*")
            list(APPEND input_files ${folder_files})
        elseif(EXISTS "${input_path}")
            list(APPEND input_files "${input_path}")
        else()
            message(FATAL_ERROR "project_config_add_docs(${target}): INPUT ${input} does not "
                                "exist.")
        endif()
        list(APPEND input_paths "\"${input_path}\"")
    endforeach()

    # Found per call because a find_package result stays in the scope that ran it, and callers live
    # in other directories; the executable path is cached after the first call.
    find_package(Doxygen QUIET)
    if(NOT DOXYGEN_FOUND)
        message(STATUS "Project-Config: doxygen not found, skipping ${target} target")
        return()
    endif()

    cmake_path(ABSOLUTE_PATH arg_DOXYFILE BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" NORMALIZE
               OUTPUT_VARIABLE doxyfile)
    if(doxyfile MATCHES "\\.in$")
        set(configured "${CMAKE_CURRENT_BINARY_DIR}/${target}.Doxyfile")
        configure_file("${doxyfile}" "${configured}" @ONLY)
        set(doxyfile "${configured}")
    endif()

    # Doxygen keeps the last assignment of a tag, so the wrapper's INPUT and output folder override
    # whatever the included Doxyfile says. file(CONFIGURE) rewrites the wrapper only when its
    # content changes, which is when the run must repeat.
    list(JOIN input_paths " \\\n                         " input_lines)
    set(wrapper "${CMAKE_CURRENT_BINARY_DIR}/${target}.wrapper.Doxyfile")
    file(
        CONFIGURE
        OUTPUT "${wrapper}"
        CONTENT [=[
@INCLUDE               = "@doxyfile@"
INPUT                  = @input_lines@
OUTPUT_DIRECTORY       = "@output_parent@"
HTML_OUTPUT            = "@output_leaf@"
]=]
        @ONLY)

    # Every run replaces OUTPUT_DIR, because Doxygen never deletes a page it stops generating, and
    # makes its parent first, because Doxygen creates only the last folder of its output path.
    add_custom_command(
        OUTPUT "${output_dir}/index.html"
        COMMAND "${CMAKE_COMMAND}" -E rm -rf "${output_dir}"
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${output_parent}"
        COMMAND Doxygen::doxygen "${wrapper}"
        DEPENDS ${input_files} ${arg_DEPENDS} "${doxyfile}" "${wrapper}"
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        COMMENT "Generating ${target} with Doxygen"
        VERBATIM)
    add_custom_target(${target} ALL DEPENDS "${output_dir}/index.html")

    if(NOT DEFINED arg_DESTINATION)
        set(arg_DESTINATION "${CMAKE_INSTALL_DOCDIR}")
    endif()
    if(NOT DEFINED arg_COMPONENT)
        set(arg_COMPONENT Development)
    endif()
    install(
        DIRECTORY "${output_dir}/"
        DESTINATION "${arg_DESTINATION}"
        COMPONENT "${arg_COMPONENT}")
endfunction()

# The project's own documentation, from docs/Doxyfile.in or else docs/Doxyfile, as the docs target.
# PROJECT_CONFIG_DOCS_INPUT, relative to the source root, and the optional
# PROJECT_CONFIG_DOCS_DEPENDS are its INPUT and DEPENDS.
if(PROJECT_CONFIG_ENABLE_DOCS)
    if(NOT DEFINED PROJECT_CONFIG_DOCS_INPUT)
        message(FATAL_ERROR "PROJECT_CONFIG_ENABLE_DOCS needs PROJECT_CONFIG_DOCS_INPUT, the "
                            "folders and files, relative to the source root, the docs document.")
    endif()
    list(TRANSFORM PROJECT_CONFIG_DOCS_INPUT PREPEND "${CMAKE_SOURCE_DIR}/"
         OUTPUT_VARIABLE _project_config_docs_input)
    set(_project_config_doxyfile "${CMAKE_SOURCE_DIR}/docs/Doxyfile.in")
    if(NOT EXISTS "${_project_config_doxyfile}")
        set(_project_config_doxyfile "${CMAKE_SOURCE_DIR}/docs/Doxyfile")
    endif()
    project_config_add_docs(
        docs
        DOXYFILE
        "${_project_config_doxyfile}"
        OUTPUT_DIR
        "${CMAKE_BINARY_DIR}/docs/html"
        INPUT
        ${_project_config_docs_input}
        DEPENDS
        ${PROJECT_CONFIG_DOCS_DEPENDS})
else()
    message(STATUS "Project-Config: PROJECT_CONFIG_ENABLE_DOCS=OFF, skipping docs target")
endif()

if(PROJECT_CONFIG_ENABLE_CLANG_TIDY)
    set(PROJECT_CONFIG_CLANG_TIDY_FILE_REGEX
        ".*"
        CACHE STRING "Regex of source files to run clang-tidy on (run-clang-tidy file regex).")
    set(PROJECT_CONFIG_CLANG_TIDY_EXTRA_ARGS
        # Some projects record compiler-specific warning flags in compile_commands.json. Clang-tidy
        # still uses Clang to parse each translation unit, so it can reject warning flags that are
        # valid for the real compiler but unknown to Clang.
        "-extra-arg=-Wno-unknown-warning-option"
        # MSVC compile databases can contain build/codegen flags such as /MP and /GL. Those flags
        # are legitimate for cl.exe, but clang-tidy does not consume them during AST analysis.
        "-extra-arg=-Wno-unused-command-line-argument"
        CACHE STRING "Additional arguments passed to run-clang-tidy.")

    # Find clang-tidy
    find_program(RUN_CLANG_TIDY_PROGRAM run-clang-tidy)

    # If clang-tidy exists and the project has a config file, add clang-tidy targets
    if(RUN_CLANG_TIDY_PROGRAM)
        message(STATUS "Project-Config: run-clang-tidy found, enabling clang-tidy targets")

        if(EXISTS "${CMAKE_SOURCE_DIR}/.clang-tidy")
            set(CMAKE_EXPORT_COMPILE_COMMANDS
                ON
                CACHE BOOL "Generate compile_commands.json for clang-tidy" FORCE)

            # On Windows, run-clang-tidy is a Python script that can't be executed directly
            set(RUN_CLANG_TIDY_COMMAND "${RUN_CLANG_TIDY_PROGRAM}")
            if(WIN32)
                find_package(
                    Python3
                    COMPONENTS Interpreter
                    QUIET REQUIRED)
                set(RUN_CLANG_TIDY_COMMAND "${Python3_EXECUTABLE}" "${RUN_CLANG_TIDY_PROGRAM}")
            endif()

            # Clang-tidy replays compile_commands.json through Clang, which may see warning flags
            # intended for a different compiler. Extra args keep those compiler-specific flags from
            # blocking lint while preserving the real build's warning policy.
            set(CLANG_TIDY_EXTRA_ARGS ${PROJECT_CONFIG_CLANG_TIDY_EXTRA_ARGS})

            # On Apple platforms, Homebrew LLVM's clang-tidy needs the SDK sysroot to find system
            # headers
            if(APPLE)
                execute_process(
                    COMMAND xcrun --show-sdk-path
                    OUTPUT_VARIABLE APPLE_SDK_PATH
                    OUTPUT_STRIP_TRAILING_WHITESPACE)
                if(APPLE_SDK_PATH)
                    list(APPEND CLANG_TIDY_EXTRA_ARGS "-extra-arg=--sysroot=${APPLE_SDK_PATH}")
                endif()
            endif()

            # Add a target to run clang-tidy
            add_custom_target(
                clang-tidy
                COMMAND ${RUN_CLANG_TIDY_COMMAND} -p "${CMAKE_BINARY_DIR}" ${CLANG_TIDY_EXTRA_ARGS}
                        "${PROJECT_CONFIG_CLANG_TIDY_FILE_REGEX}"
                WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
                COMMENT "Running clang-tidy"
                VERBATIM USES_TERMINAL)

            # Add a target to run clang-tidy and apply fixes
            add_custom_target(
                clang-tidy-fix
                COMMAND ${RUN_CLANG_TIDY_COMMAND} -p "${CMAKE_BINARY_DIR}" ${CLANG_TIDY_EXTRA_ARGS}
                        -fix "${PROJECT_CONFIG_CLANG_TIDY_FILE_REGEX}"
                WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
                COMMENT "Running clang-tidy with fixes"
                VERBATIM USES_TERMINAL)
        else()
            message(WARNING "Project-Config: no .clang-tidy found, skipping clang-tidy targets")
        endif()
    else()
        message(STATUS "Project-Config: run-clang-tidy not found, skipping clang-tidy targets")
    endif()
else()
    message(
        STATUS "Project-Config: PROJECT_CONFIG_ENABLE_CLANG_TIDY=OFF, skipping clang-tidy targets")
endif()
