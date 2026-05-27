list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
set(CMAKE_MODULE_PATH
    "${CMAKE_MODULE_PATH}"
    PARENT_SCOPE)
include(GNUInstallDirs)

# Configure docs target if explicitly enabled
if(PROJECT_CONFIG_ENABLE_DOCS)
    set(PROJECT_CONFIG_DOCS_OUTPUT_DIR
        "${CMAKE_BINARY_DIR}/docs/html"
        CACHE PATH "Directory containing generated HTML documentation.")
    set(PROJECT_CONFIG_DOCS_INSTALL_DESTINATION
        "${CMAKE_INSTALL_DATADIR}/${PROJECT_NAME}/docs"
        CACHE STRING "Install destination for generated HTML documentation.")
    set(PROJECT_CONFIG_DOCS_INSTALL_COMPONENT
        "Runtime"
        CACHE STRING "Install component for generated HTML documentation.")

    # Find doxygen (and optionally dot for graph generation)
    find_package(Doxygen QUIET OPTIONAL_COMPONENTS dot)

    set(DOXYFILE_TEMPLATE_PATH "${CMAKE_SOURCE_DIR}/docs/Doxyfile.in")
    set(DOXYFILE_STATIC_PATH "${CMAKE_SOURCE_DIR}/docs/Doxyfile")
    set(DOXYFILE "")

    # If docs config exists for the current project and doxygen is found, add docs target
    if(Doxygen_FOUND)
        message(STATUS "Project-Config: doxygen found, enabling docs target")

        if(EXISTS "${DOXYFILE_TEMPLATE_PATH}")
            # Prefer template-based Doxygen config when available.
            configure_file("${DOXYFILE_TEMPLATE_PATH}" "${CMAKE_BINARY_DIR}/Doxyfile" @ONLY)
            set(DOXYFILE "${CMAKE_BINARY_DIR}/Doxyfile")
            message(STATUS "Project-Config: using docs/Doxyfile.in for docs target")
        elseif(EXISTS "${DOXYFILE_STATIC_PATH}")
            set(DOXYFILE "${DOXYFILE_STATIC_PATH}")
            message(STATUS "Project-Config: using docs/Doxyfile for docs target")
        endif()

        if(DOXYFILE)
            # If dot is found, enable diagrams
            if(Doxygen_dot_FOUND)
                set(DOXYGEN_HAVE_DOT "YES")
                message(STATUS "Project-Config: Graphviz dot found, enabling diagrams")
            else()
                set(DOXYGEN_HAVE_DOT "NO")
                message(STATUS "Project-Config: Graphviz dot not found, disabling diagrams")
            endif()

            add_custom_target(
                docs
                COMMAND ${DOXYGEN_EXECUTABLE} "${DOXYFILE}"
                WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                COMMENT "Generating API documentation with Doxygen"
                VERBATIM)

            set(_project_config_docs_development_script
                "${CMAKE_CURRENT_BINARY_DIR}/generate-docs-if-missing.cmake")
            file(
                WRITE "${_project_config_docs_development_script}"
                "if(NOT EXISTS \"${PROJECT_CONFIG_DOCS_OUTPUT_DIR}/index.html\")\n"
                "    execute_process(\n"
                "        COMMAND \"${DOXYGEN_EXECUTABLE}\" \"${DOXYFILE}\"\n"
                "        WORKING_DIRECTORY \"${CMAKE_SOURCE_DIR}\"\n"
                "        RESULT_VARIABLE _project_config_docs_result)\n"
                "    if(NOT _project_config_docs_result EQUAL 0)\n"
                "        message(FATAL_ERROR \"Doxygen failed while preparing development docs.\")\n"
                "    endif()\n"
                "endif()\n")

            # App targets can depend on this lightweight target to make local docs available from
            # development builds without rerunning Doxygen after the HTML tree already exists.
            add_custom_target(
                project_config_docs_for_development
                COMMAND "${CMAKE_COMMAND}" -P "${_project_config_docs_development_script}"
                COMMENT "Ensuring development documentation exists"
                VERBATIM)

            # Install generated docs with the configured component so CPack includes them when
            # that component is packaged. OPTIONAL keeps install usable before docs are built.
            install(
                DIRECTORY "${PROJECT_CONFIG_DOCS_OUTPUT_DIR}/"
                DESTINATION "${PROJECT_CONFIG_DOCS_INSTALL_DESTINATION}"
                COMPONENT "${PROJECT_CONFIG_DOCS_INSTALL_COMPONENT}"
                OPTIONAL)

            set(_project_config_docs_cpack_script
                "${CMAKE_CURRENT_BINARY_DIR}/generate-docs-for-cpack.cmake")
            file(
                WRITE "${_project_config_docs_cpack_script}"
                "execute_process(\n"
                "    COMMAND \"${DOXYGEN_EXECUTABLE}\" \"${DOXYFILE}\"\n"
                "    WORKING_DIRECTORY \"${CMAKE_SOURCE_DIR}\"\n"
                "    RESULT_VARIABLE _project_config_docs_result)\n"
                "if(NOT _project_config_docs_result EQUAL 0)\n"
                "    message(FATAL_ERROR \"Doxygen failed while preparing CPack docs.\")\n"
                "endif()\n")

            # CPack runs install scripts before staging install rules, so generated docs exist
            # before the directory install above tries to copy them into the package image.
            list(APPEND CPACK_INSTALL_SCRIPTS "${_project_config_docs_cpack_script}")
            set(CPACK_INSTALL_SCRIPTS
                "${CPACK_INSTALL_SCRIPTS}"
                PARENT_SCOPE)
        else()
            message(WARNING "Project-Config: no Doxyfile configuration found, skipping docs target")
        endif()
    else()
        message(STATUS "Project-Config: doxygen not found, skipping docs target")
    endif()
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
