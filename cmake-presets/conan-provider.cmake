# The Conan provider, with each build tree owning its Conan home by default. A CONAN_HOME already in
# the cache is kept, and an empty one leaves the home to Conan's own resolution.
set(CONAN_HOME
    "${CMAKE_BINARY_DIR}/.conan2"
    CACHE PATH "Conan home (cache and config) for this build tree")
include("${CMAKE_CURRENT_LIST_DIR}/../cmake-conan/conan_provider.cmake")
