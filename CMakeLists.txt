cmake_minimum_required(VERSION 3.24)

# Copy shared formatter/linter config files to the project root
configure_file(${CMAKE_CURRENT_LIST_DIR}/.clang-format ${CMAKE_SOURCE_DIR}/.clang-format COPYONLY)
configure_file(${CMAKE_CURRENT_LIST_DIR}/.clang-tidy ${CMAKE_SOURCE_DIR}/.clang-tidy COPYONLY)
configure_file(${CMAKE_CURRENT_LIST_DIR}/.cmake-format.py ${CMAKE_SOURCE_DIR}/.cmake-format.py
               COPYONLY)
