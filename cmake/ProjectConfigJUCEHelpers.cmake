# project_config_juce_add_binary_data(<target> [NAMESPACE <ns>] [HEADER_NAME <name>] SOURCES
# <file>...)
#
# Wrapper around juce_add_binary_data() that also wires the resulting static library target into the
# clang-tidy and clang-tidy-fix targets (when they exist). Without this wiring, lint runs fail with
# "BinaryData.h file not found" because juce_add_binary_data() produces the header via
# add_custom_command — build time only — and the lint targets run run-clang-tidy without triggering
# a build.
#
# All arguments beyond <target> are forwarded verbatim to juce_add_binary_data().
function(project_config_juce_add_binary_data target)
    juce_add_binary_data(${target} ${ARGN})

    foreach(tidy_target IN ITEMS clang-tidy clang-tidy-fix)
        if(TARGET ${tidy_target})
            add_dependencies(${tidy_target} ${target})
        endif()
    endforeach()
endfunction()

# project_config_juce_generate_juce_header(<target>)
#
# Wrapper around juce_generate_juce_header() that also wires the generated JuceHeader.h into the
# clang-tidy and clang-tidy-fix targets (when they exist). Without this wiring, lint runs fail with
# "JuceHeader.h file not found" because juce_generate_juce_header() produces the header via
# add_custom_command — build time only — and the lint targets run run-clang-tidy without triggering
# a build.
#
# The "juce" appears twice because the name mirrors juce_generate_juce_header() directly, prefixed
# with project_config_ for consistency with project_config_juce_add_binary_data().
#
# The wrapper creates a lightweight named target (<target>_juce_header) that drives only the
# juceaide header-generation step, not a full compile. This keeps lint fast.
function(project_config_juce_generate_juce_header target)
    juce_generate_juce_header(${target})

    get_target_property(_gen_dir ${target} JUCE_GENERATED_SOURCES_DIRECTORY)
    add_custom_target(${target}_juce_header DEPENDS "${_gen_dir}/JuceHeader.h")

    foreach(tidy_target IN ITEMS clang-tidy clang-tidy-fix)
        if(TARGET ${tidy_target})
            add_dependencies(${tidy_target} ${target}_juce_header)
        endif()
    endforeach()
endfunction()
