cmake_minimum_required(VERSION 3.14)
project(pyquota C)

set(CMAKE_C_STANDARD 99)

add_library(pyquota SHARED pyquota.c)
find_package(PythonLibs REQUIRED)
target_include_directories(pyquota PRIVATE ${PYTHON_INCLUDE_DIRS})
target_link_libraries(pyquota ${PYTHON_LIBRARIES})
