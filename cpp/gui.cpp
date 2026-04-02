#include <QApplication>
#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLineEdit>
#include <QPushButton>
#include <QTreeWidget>
#include <QLabel>
#include <QMessageBox>
#include <QDesktopServices>
#include <QUrl>
#include <QHeaderView>

#include <mongocxx/client.hpp>
#include <mongocxx/instance.hpp>
#include <mongocxx/uri.hpp>
#include <bsoncxx/json.hpp>
#include <bsoncxx/builder/stream/document.hpp>

// Forward declare for signal slots would usually go in .h with Q_OBJECT
// For single-file simplicity, we might not use Q_OBJECT macros heavily or need a separate moc step if we are careful,
// but idiomatic Qt usually needs them. I will write a simple class.
// Since I cannot easily run moc in this environment without proper CMake setup, I will rely on standard CMake to handle it
// or write it in a way that minimizes moc usage if possible (functors in connect) - Qt5/6 supports lambda connects.

using bsoncxx::builder::stream::document;
using bsoncxx::builder::stream::finalize;

class FileManagerApp : public QWidget {
public:
    FileManagerApp() {
        setWindowTitle("File Manager (C++)");
        resize(800, 500);

        auto* mainLayout = new QVBoxLayout(this);

        // Search Bar
        auto* searchLayout = new QHBoxLayout();
        auto* lbl = new QLabel("Search:", this);
        searchEntry = new QLineEdit(this);
        auto* btn = new QPushButton("Go", this);
        
        searchLayout->addWidget(lbl);
        searchLayout->addWidget(searchEntry);
        searchLayout->addWidget(btn);
        mainLayout->addLayout(searchLayout);

        // Tree View
        resultTree = new QTreeWidget(this);
        resultTree->setColumnCount(5);
        resultTree->setHeaderLabels({"Name", "Ext", "Size", "Folder", "Modified"});
        resultTree->header()->setSectionResizeMode(0, QHeaderView::Stretch);
        mainLayout->addWidget(resultTree);

        // DB Connection
        try {
            client = std::make_unique<mongocxx::client>(mongocxx::uri{"mongodb://localhost:27017"});
            db = (*client)["fileManager"];
        } catch (const std::exception& e) {
            QMessageBox::critical(this, "DB Error", e.what());
        }

        // Signals
        QObject::connect(btn, &QPushButton::clicked, this, &FileManagerApp::search);
        QObject::connect(searchEntry, &QLineEdit::returnPressed, this, &FileManagerApp::search);
        QObject::connect(resultTree, &QTreeWidget::itemDoubleClicked, this, &FileManagerApp::onItemDoubleClicked);

        // Initial load
        search();
    }

private:
    QLineEdit* searchEntry;
    QTreeWidget* resultTree;
    std::unique_ptr<mongocxx::client> client;
    mongocxx::database db;

    void search() {
        resultTree->clear();
        std::string kw = searchEntry->text().toStdString();
        
        mongocxx::cursor cursor = (kw.empty()) 
            ? db["files"].find(document{} << finalize) 
            : db["files"].find(document{} << "$text" << open_document << "$search" << kw << close_document << finalize);

        // Limit equivalent not directly on cursor object in C++ driver effectively without options
        // For simplicity we just iterate first 200
        int count = 0;
        for (auto&& doc : cursor) {
            if (count++ > 200) break;

            auto name = std::string(doc["name"].get_string().value);
            auto ext = std::string(doc["ext"].get_string().value);
            // Size might be int32 or int64 depending on Python
            int64_t size = 0;
            if (doc["size"].type() == bsoncxx::type::k_int32) size = doc["size"].get_int32().value;
            if (doc["size"].type() == bsoncxx::type::k_int64) size = doc["size"].get_int64().value;
            
            // Fetch folder name
            std::string folderName = "";
            if (doc["folderId"]) {
                 auto folderDoc = db["folders"].find_one(document{} << "_id" << doc["folderId"].get_oid() << finalize);
                 if (folderDoc) {
                     folderName = std::string(folderDoc->view()["name"].get_string().value);
                 }
            }
            
            // Path needed for opening, store in hidden column or data
            std::string fullPath = std::string(doc["path"].get_string().value);

            auto* item = new QTreeWidgetItem(resultTree);
            item->setText(0, QString::fromStdString(name));
            item->setText(1, QString::fromStdString(ext));
            item->setText(2, QString::number(size));
            item->setText(3, QString::fromStdString(folderName));
            item->setData(0, Qt::UserRole, QString::fromStdString(fullPath)); // Store path in user data
        }
    }

    void onItemDoubleClicked(QTreeWidgetItem* item, int column) {
        QString path = item->data(0, Qt::UserRole).toString();
        if (!path.isEmpty()) {
            QDesktopServices::openUrl(QUrl::fromLocalFile(path));
        }
    }
};

int main(int argc, char *argv[]) {
    // MongoDB instance must be initialized once
    mongocxx::instance inst{};
    
    QApplication app(argc, argv);
    FileManagerApp window;
    window.show();
    return app.exec();
}
