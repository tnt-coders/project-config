list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
set(CMAKE_MODULE_PATH
    "${CMAKE_MODULE_PATH}"
    PARENT_SCOPE)
include(GNUInstallDirs)

# Adds <target>, which runs Doxygen over DOXYFILE:
#
# ~~~
# project_config_add_docs(<target> DOXYFILE <file> OUTPUT_DIR <dir>
#                         [INSTALL_DESTINATION <destination> COMPONENT <component>]
#                         [DEVELOPMENT_TARGET <name>])
# ~~~
#
# OUTPUT_DIR is the HTML directory that DOXYFILE writes; the Doxyfile decides it, and every run
# empties it first, so it holds exactly that run's pages. A DOXYFILE ending in .in is configured
# with @ONLY substitution to a file of the target's own, so two calls never share a configuration;
# the template sees the caller's variables.
#
# With INSTALL_DESTINATION, installing COMPONENT reruns Doxygen and then copies OUTPUT_DIR to the
# destination, so a package never needs a separate docs build. DEVELOPMENT_TARGET names a target
# that runs Doxygen only while OUTPUT_DIR/index.html is missing, for app targets that open the HTML
# from the build tree.
#
# Nothing is added when PROJECT_CONFIG_ENABLE_DOCS is off, Doxygen is not found or DOXYFILE does not
# exist, so callers guard with if(TARGET <target>).
function(project_config_add_docs target)
    cmake_parse_arguments(PARSE_ARGV 1 arg ""
                          "DOXYFILE;OUTPUT_DIR;INSTALL_DESTINATION;COMPONENT;DEVELOPMENT_TARGET" "")
    if(DEFINED arg_UNPARSED_ARGUMENTS
       OR NOT DEFINED arg_DOXYFILE
       OR NOT DEFINED arg_OUTPUT_DIR)
        message(FATAL_ERROR "project_config_add_docs(${target}) takes DOXYFILE and OUTPUT_DIR, "
                            "and only the optional arguments it documents.")
    endif()
    if((DEFINED arg_INSTALL_DESTINATION AND NOT DEFINED arg_COMPONENT)
       OR (DEFINED arg_COMPONENT AND NOT DEFINED arg_INSTALL_DESTINATION))
        message(FATAL_ERROR "project_config_add_docs(${target}) takes INSTALL_DESTINATION and "
                            "COMPONENT together.")
    endif()

    # Emptying OUTPUT_DIR must never reach the caller's sources or build files, which also covers
    # the top-level trees that contain them. A relative path resolves against the calling source
    # directory, as install(DIRECTORY) reads it, so the check sees the path every run uses. The
    # trailing / lets a path that normalizes to one, such as ".", still match its own directory.
    cmake_path(ABSOLUTE_PATH arg_OUTPUT_DIR)
    foreach(protected IN ITEMS "${CMAKE_CURRENT_SOURCE_DIR}" "${CMAKE_CURRENT_BINARY_DIR}")
        cmake_path(IS_PREFIX arg_OUTPUT_DIR "${protected}/" NORMALIZE output_dir_contains)
        if(output_dir_contains)
            message(FATAL_ERROR "project_config_add_docs(${target}) empties OUTPUT_DIR before "
                                "every run, so it must not contain ${protected}.")
        endif()
    endforeach()

    # For the same reason no two docs targets' OUTPUT_DIRs may nest: either target's run would wipe
    # the other's pages.
    get_property(docs_targets GLOBAL PROPERTY PROJECT_CONFIG_DOCS_TARGETS)
    foreach(other IN LISTS docs_targets)
        get_property(other_dir GLOBAL PROPERTY PROJECT_CONFIG_DOCS_OUTPUT_DIR_${other})
        cmake_path(IS_PREFIX arg_OUTPUT_DIR "${other_dir}/" NORMALIZE contains_other)
        cmake_path(IS_PREFIX other_dir "${arg_OUTPUT_DIR}/" NORMALIZE inside_other)
        if(contains_other OR inside_other)
            message(FATAL_ERROR "Docs targets ${target} and ${other} nest their OUTPUT_DIRs, "
                                "${arg_OUTPUT_DIR} and ${other_dir}.")
        endif()
    endforeach()
    set_property(GLOBAL APPEND PROPERTY PROJECT_CONFIG_DOCS_TARGETS ${target})
    set_property(GLOBAL PROPERTY PROJECT_CONFIG_DOCS_OUTPUT_DIR_${target} "${arg_OUTPUT_DIR}")

    if(NOT PROJECT_CONFIG_ENABLE_DOCS)
        message(STATUS "Project-Config: PROJECT_CONFIG_ENABLE_DOCS=OFF, skipping ${target} target")
        return()
    endif()

    # Found per call because a find_package result stays in the scope that ran it, and callers live
    # in other directories; the executable paths are cached after the first call.
    find_package(Doxygen QUIET)
    if(NOT Doxygen_FOUND)
        message(STATUS "Project-Config: doxygen not found, skipping ${target} target")
        return()
    endif()
    message(STATUS "Project-Config: doxygen found, enabling ${target} target")

    if(NOT EXISTS "${arg_DOXYFILE}")
        message(WARNING "Project-Config: ${arg_DOXYFILE} not found, skipping ${target} target")
        return()
    endif()
    message(STATUS "Project-Config: using ${arg_DOXYFILE} for ${target} target")

    set(doxyfile "${arg_DOXYFILE}")
    if(doxyfile MATCHES "\\.in$")
        set(doxyfile "${CMAKE_CURRENT_BINARY_DIR}/${target}.Doxyfile")
        configure_file("${arg_DOXYFILE}" "${doxyfile}" @ONLY)
    endif()

    # The one Doxygen run that the target, the development target and the install rule all execute.
    # It empties OUTPUT_DIR first, because Doxygen never deletes a page it no longer generates, and
    # remakes it with its parents, because Doxygen creates only the last folder of its output path.
    # It checks OUTPUT_DIR afterwards, because a Doxyfile writing elsewhere would otherwise pass
    # unnoticed, with the development check rerunning Doxygen on every build.
    set(generate "${CMAKE_CURRENT_BINARY_DIR}/${target}.cmake")
    file(
        WRITE "${generate}"
        "file(REMOVE_RECURSE \"${arg_OUTPUT_DIR}\")\n"
        "file(MAKE_DIRECTORY \"${arg_OUTPUT_DIR}\")\n"
        "execute_process(\n"
        "    COMMAND \"${DOXYGEN_EXECUTABLE}\" \"${doxyfile}\"\n"
        "    WORKING_DIRECTORY \"${CMAKE_SOURCE_DIR}\"\n"
        "    RESULT_VARIABLE _project_config_docs_result)\n"
        "if(NOT _project_config_docs_result EQUAL 0)\n"
        "    message(FATAL_ERROR \"Doxygen failed while generating ${target}.\")\n"
        "endif()\n"
        "if(NOT EXISTS \"${arg_OUTPUT_DIR}/index.html\")\n"
        "    message(FATAL_ERROR \"${target}'s Doxyfile did not write its HTML to its \"\n"
        "                        \"OUTPUT_DIR, ${arg_OUTPUT_DIR}.\")\n"
        "endif()\n")

    add_custom_target(
        ${target}
        COMMAND "${CMAKE_COMMAND}" -P "${generate}"
        COMMENT "Generating ${target} with Doxygen"
        VERBATIM)

    if(DEFINED arg_DEVELOPMENT_TARGET)
        set(development_script "${CMAKE_CURRENT_BINARY_DIR}/${arg_DEVELOPMENT_TARGET}.cmake")
        file(WRITE "${development_script}" "if(NOT EXISTS \"${arg_OUTPUT_DIR}/index.html\")\n"
                                           "    include(\"${generate}\")\n" "endif()\n")
        add_custom_target(
            ${arg_DEVELOPMENT_TARGET}
            COMMAND "${CMAKE_COMMAND}" -P "${development_script}"
            COMMENT "Ensuring ${target} output exists"
            VERBATIM)
    endif()

    if(DEFINED arg_INSTALL_DESTINATION)
        # A directory's install rules run in the order they are declared, so the HTML is regenerated
        # before it is copied, and only when its own component is installed.
        install(CODE "include(\"${generate}\")" COMPONENT "${arg_COMPONENT}")
        install(
            DIRECTORY "${arg_OUTPUT_DIR}/"
            DESTINATION "${arg_INSTALL_DESTINATION}"
            COMPONENT "${arg_COMPONENT}")
    endif()
endfunction()

# The project's own documentation, from docs/Doxyfile.in or else docs/Doxyfile, as the docs target.
# Each default is cached only when the caller has not set the variable, because under older policy
# settings (CMP0077 before CMake 3.13, CMP0126 before 3.21) creating the cache entry would discard
# the caller's plain set().
if(NOT DEFINED PROJECT_CONFIG_DOCS_OUTPUT_DIR)
    set(PROJECT_CONFIG_DOCS_OUTPUT_DIR
        "${CMAKE_BINARY_DIR}/docs/html"
        CACHE PATH "Directory containing generated HTML documentation.")
endif()
if(NOT DEFINED PROJECT_CONFIG_DOCS_INSTALL_DESTINATION)
    set(PROJECT_CONFIG_DOCS_INSTALL_DESTINATION
        "${CMAKE_INSTALL_DATADIR}/${PROJECT_NAME}/docs"
        CACHE STRING "Install destination for generated HTML documentation.")
endif()
if(NOT DEFINED PROJECT_CONFIG_DOCS_INSTALL_COMPONENT)
    set(PROJECT_CONFIG_DOCS_INSTALL_COMPONENT
        "Runtime"
        CACHE STRING "Install component for generated HTML documentation.")
endif()
if(NOT DEFINED PROJECT_CONFIG_DOCS_INSTALL)
    option(PROJECT_CONFIG_DOCS_INSTALL
           "Install the docs target's HTML, regenerating it at install time" ON)
endif()

set(_project_config_doxyfile "${CMAKE_SOURCE_DIR}/docs/Doxyfile.in")
if(NOT EXISTS "${_project_config_doxyfile}")
    set(_project_config_doxyfile "${CMAKE_SOURCE_DIR}/docs/Doxyfile")
endif()

set(_project_config_docs_install)
if(PROJECT_CONFIG_DOCS_INSTALL)
    set(_project_config_docs_install
        INSTALL_DESTINATION "${PROJECT_CONFIG_DOCS_INSTALL_DESTINATION}" COMPONENT
        "${PROJECT_CONFIG_DOCS_INSTALL_COMPONENT}")
endif()

# App targets can depend on project_config_docs_for_development to open the HTML from the build tree
# without rerunning Doxygen once it exists.
project_config_add_docs(
    docs
    DOXYFILE
    "${_project_config_doxyfile}"
    OUTPUT_DIR
    "${PROJECT_CONFIG_DOCS_OUTPUT_DIR}"
    ${_project_config_docs_install}
    DEVELOPMENT_TARGET
    project_config_docs_for_development)

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
