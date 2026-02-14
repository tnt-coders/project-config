# clang-tidy target
find_program(RUN_CLANG_TIDY_PROGRAM run-clang-tidy)

if(RUN_CLANG_TIDY_PROGRAM AND EXISTS "${CMAKE_SOURCE_DIR}/.clang-tidy")
    set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

    # On Windows, run-clang-tidy is a Python script that can't be executed directly
    set(RUN_CLANG_TIDY_COMMAND "${RUN_CLANG_TIDY_PROGRAM}")
    if(WIN32)
        find_package(
            Python3
            COMPONENTS Interpreter
            REQUIRED)
        set(RUN_CLANG_TIDY_COMMAND "${Python3_EXECUTABLE}" "${RUN_CLANG_TIDY_PROGRAM}")
    endif()

    add_custom_target(
        clang-tidy
        COMMAND ${RUN_CLANG_TIDY_COMMAND} -p "${CMAKE_BINARY_DIR}"
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        COMMENT "Running clang-tidy")

    add_custom_target(
        clang-tidy-fix
        COMMAND ${RUN_CLANG_TIDY_COMMAND} -p "${CMAKE_BINARY_DIR}" -fix
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        COMMENT "Running clang-tidy with fixes")
else()
    message(STATUS "run-clang-tidy or .clang-tidy not found, skipping clang-tidy targets")
endif()
