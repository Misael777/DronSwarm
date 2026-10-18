cmake_minimum_required(VERSION 3.16)
project(dronswarm_tether_system LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(gz-sim7 REQUIRED)
find_package(gz-plugin2 REQUIRED COMPONENTS register)
find_package(gz-transport12 REQUIRED)

add_library(dronswarm-tether-system SHARED TetherSystem.cc)
target_link_libraries(dronswarm-tether-system
  PRIVATE gz-sim7::gz-sim7 gz-plugin2::register gz-transport12::gz-transport12)
