# =============================================================================
# CMakeLists.txt  —  SIL Project build coordinator
# =============================================================================
#
# What this file does:
#   1. Compiles src/controller.c into a SHARED library
#      (libcontroller.so / controller.dll / libcontroller.dylib)
#   2. Builds a small sil_main stub executable to sanity-check the build
#   3. Copies the shared library into tests/ so Python can find it
#   4. Optionally enables CTest so `ctest` runs the Python test suite
#
# Usage:
#   cmake -B build -S .          # Configure (generates Makefile / Ninja)
#   cmake --build build          # Compile
#   ctest --test-dir build -V    # Run tests via CTest (optional)
# =============================================================================

cmake_minimum_required(VERSION 3.16)

project(sil_motor_controller
    VERSION     1.0.0
    DESCRIPTION "Software-in-the-Loop PID motor speed controller"
    LANGUAGES   C
)

# ── Compiler settings ────────────────────────────────────────────────────────
set(CMAKE_C_STANDARD          11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS        OFF)

# Enable more warnings in debug builds to catch bugs early
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    if(MSVC)
        add_compile_options(/W4 /WX)
    else()
        add_compile_options(-Wall -Wextra -Wpedantic -Werror)
    endif()
endif()

# ── 1. Shared library (the SUT — System Under Test) ─────────────────────────
#
# SHARED means CMake produces a .so / .dll / .dylib instead of a .a / .lib.
# Python's ctypes can only load dynamic (shared) libraries.
add_library(controller SHARED
    src/controller.c
)

# Export the src/ directory so consumers can #include "controller.h"
target_include_directories(controller
    PUBLIC ${CMAKE_SOURCE_DIR}/src
)

# On Linux, math functions sometimes need -lm
if(UNIX AND NOT APPLE)
    target_link_libraries(controller PRIVATE m)
endif()

# ── 2. Stub executable ───────────────────────────────────────────────────────
add_executable(sil_main
    src/main_stub.c
)
target_link_libraries(sil_main PRIVATE controller)

# ── 3. Copy shared library → tests/ ─────────────────────────────────────────
#
# After the library is built, copy it next to run_tests.py so Python
# can load it with a simple relative path — no LD_LIBRARY_PATH gymnastics.
add_custom_command(TARGET controller POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        $<TARGET_FILE:controller>
        ${CMAKE_SOURCE_DIR}/tests/
    COMMENT "Copying ${CMAKE_SHARED_LIBRARY_PREFIX}controller${CMAKE_SHARED_LIBRARY_SUFFIX} → tests/"
)

# ── 4. CTest integration ─────────────────────────────────────────────────────
#
# `ctest --test-dir build` will invoke Python to run the test suite.
# Jenkins uses this so it can report test results in a standard way.
enable_testing()

find_package(Python3 COMPONENTS Interpreter REQUIRED)

add_test(
    NAME    SIL_PID_Tests
    COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_SOURCE_DIR}/tests/run_tests.py
            --output-dir ${CMAKE_SOURCE_DIR}/tests
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
)

# Set a generous timeout (seconds) — increase if your plant simulation is long
set_tests_properties(SIL_PID_Tests PROPERTIES TIMEOUT 120)

# ── Summary ──────────────────────────────────────────────────────────────────
message(STATUS "")
message(STATUS "=== SIL Project configured ===")
message(STATUS "  Build type   : ${CMAKE_BUILD_TYPE}")
message(STATUS "  C standard   : C${CMAKE_C_STANDARD}")
message(STATUS "  Install prefix: ${CMAKE_INSTALL_PREFIX}")
message(STATUS "  Python       : ${Python3_EXECUTABLE}")
message(STATUS "")
