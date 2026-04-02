#include <iostream>
#include <string>
#include <vector>
#include <filesystem>
#include <fstream>
#include <chrono>
#include <iomanip>
#include <sstream>

#include <openssl/sha.h>

#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <mongocxx/uri.hpp>
#include <bsoncxx/json.hpp>
#include <bsoncxx/builder/stream/document.hpp>

namespace fs = std::filesystem;
using bsoncxx::builder::stream::document;
using bsoncxx::builder::stream::finalize;
using bsoncxx::builder::stream::open_document;
using bsoncxx::builder::stream::close_document;

// Global instance must exist for mongocxx driver
mongocxx::instance inst{};

std::string get_file_hash(const fs::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) return "";

    SHA256_CTX sha256;
    SHA256_Init(&sha256);

    char buffer[32768];
    while (file.read(buffer, sizeof(buffer))) {
        SHA256_Update(&sha256, buffer, file.gcount());
    }
    SHA256_Update(&sha256, buffer, file.gcount());

    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256_Final(hash, &sha256);

    std::stringstream ss;
    for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
        ss << std::hex << std::setw(2) << std::setfill('0') << (int)hash[i];
    }
    return ss.str();
}

void ensure_indexes(mongocxx::database& db) {
    auto files = db["files"];
    auto folders = db["folders"];
    auto tags = db["tags"];
    auto file_tags = db["file_tags"];
    auto accessLog = db["accessLog"];
    auto trash = db["trash"];

    // Equivalent to create_index
    try {
        files.create_index(document{} << "name" << "text" << finalize);
        folders.create_index(document{} << "path" << 1 << finalize); // unique todo
        tags.create_index(document{} << "name" << 1 << finalize);
    } catch (const std::exception& e) {
        // Indexes might already exist
    }
}

int main() {
    mongocxx::client client{mongocxx::uri{"mongodb://localhost:27017"}};
    auto db = client["fileManager"];

    std::string path_input;
    std::cout << "Folder to index: ";
    std::getline(std::cin, path_input);
    
    fs::path root = path_input.empty() ? fs::current_path() : fs::path(path_input);
    if (!fs::exists(root)) {
        std::cerr << "Path does not exist!" << std::endl;
        return 1;
    }

    ensure_indexes(db);
    
    std::string owner = "me";
    auto files_coll = db["files"];
    auto folders_coll = db["folders"];

    std::cout << "Scanning " << root << "..." << std::endl;

    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_directory()) {
            auto folder_path = fs::absolute(entry.path());
            
            bsoncxx::builder::stream::document builder{};
            builder << "path" << folder_path.string()
                    << "name" << folder_path.filename().string()
                    << "owner" << owner;

            // Upsert folder
            bsoncxx::builder::stream::document filter{};
            filter << "path" << folder_path.string();
            
            mongocxx::options::replace opts;
            opts.upsert(true);
            folders_coll.replace_one(filter.view(), builder.view(), opts);
        }
        else if (entry.is_regular_file()) {
            auto full_path = fs::absolute(entry.path());
            
            // Generate UID similar to Python: inode_mtime (simplified here)
            // Windows doesn't easily give inode in integer form without OS calls, using hash or path as proxy
            // For simplicity, let's use path hash or similar, BUT Python code used stat.st_ino
            // We will just use path + mtime to be unique enough for this demo or stick to pure path logic if needed.
            // Let's try to simulate Python's unique ID if possible, otherwise rely on path.
            
            auto ftime = fs::last_write_time(entry);
            auto timestamp = std::chrono::duration_cast<std::chrono::seconds>(ftime.time_since_epoch()).count();
            
            std::string uid = std::to_string(std::hash<std::string>{}(full_path.string())) + "_" + std::to_string(timestamp);

            // Find parent folder ID
            auto parent_path = full_path.parent_path().string();
            auto parent_doc = folders_coll.find_one(document{} << "path" << parent_path << finalize);
            
            bsoncxx::types::b_oid folder_id;
            if (parent_doc) {
                folder_id = parent_doc->view()["_id"].get_oid();
            } else {
                // If parent not found (recursion order?), creates it or skip?
                // Recursive iterator goes top-down usually.
                continue; 
            }

            auto size = entry.file_size();
            std::string ext = full_path.extension().string(); 
            // Normalize extension (lowercase)
            std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);

            bsoncxx::builder::stream::document doc{};
            doc << "uid" << uid
                << "name" << full_path.filename().string()
                << "ext" << ext
                << "size" << (int64_t)size
                << "path" << full_path.string()
                << "folderId" << folder_id
                << "owner" << owner
                << "hash" << get_file_hash(full_path);
            
            // Dates to be added...

             mongocxx::options::replace opts;
             opts.upsert(true);
             files_coll.replace_one(document{} << "uid" << uid << finalize, doc.view(), opts);
        }
    }

    std::cout << "Scan complete." << std::endl;
    return 0;
}
