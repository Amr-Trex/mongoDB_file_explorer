project(MongoFileManager)
cmake_minimum_required(VERSION 3.16)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_PREFIX_PATH "C:/Qt/6.8.0/msvc2019_64") # Example path, user might need to adjust

find_package(Qt6 REQUIRED COMPONENTS Widgets)
find_package(mongocxx REQUIRED)
find_package(libbsoncxx REQUIRED)
find_package(OpenSSL REQUIRED)

# ---------------- Scan Tool ----------------
add_executable(scanner scan.cpp)
target_link_libraries(scanner PRIVATE mongo::mongocxx_shared OpenSSL::SSL OpenSSL::Crypto)

# ---------------- GUI Tool ----------------
add_executable(gui gui.cpp)
target_link_libraries(gui PRIVATE Qt6::Widgets mongo::mongocxx_shared)
