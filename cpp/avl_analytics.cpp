#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>

using namespace std;

// ---------------- Data Structure ----------------
struct Node {
    string uid;
    string name;
    long long size; // File size in bytes
    int height;
    Node *left;
    Node *right;

    Node(string u, string n, long long s)
        : uid(u), name(n), size(s), height(1), left(nullptr), right(nullptr) {}
};

// ---------------- AVL Tree Class ----------------
class AVLTree {
public:
    Node* root;

    AVLTree() : root(nullptr) {}

    // Utility: Get height of a node
    int height(Node* N) {
        if (N == nullptr) return 0;
        return N->height;
    }

    // Utility: Max of two integers
    int max(int a, int b) {
        return (a > b) ? a : b;
    }

    // Helper: Right Rotate
    Node* rightRotate(Node* y) {
        Node* x = y->left;
        Node* T2 = x->right;

        // Perform rotation
        x->right = y;
        y->left = T2;

        // Update heights
        y->height = max(height(y->left), height(y->right)) + 1;
        x->height = max(height(x->left), height(x->right)) + 1;

        return x; // New root
    }

    // Helper: Left Rotate
    Node* leftRotate(Node* x) {
        Node* y = x->right;
        Node* T2 = y->left;

        // Perform rotation
        y->left = x;
        x->right = T2;

        // Update heights
        x->height = max(height(x->left), height(x->right)) + 1;
        y->height = max(height(y->left), height(y->right)) + 1;

        return y; // New root
    }

    // Get Balance factor of node N
    int getBalance(Node* N) {
        if (N == nullptr) return 0;
        return height(N->left) - height(N->right);
    }

    // Recursive Insert function
    Node* insert(Node* node, string uid, string name, long long size) {
        // 1. Perform the normal BST insertion
        if (node == nullptr)
            return(new Node(uid, name, size));

        // NOTE: We sort by SIZE. 
        if (size < node->size)
            node->left = insert(node->left, uid, name, size);
        else if (size > node->size)
            node->right = insert(node->right, uid, name, size);
        else {
            // Equal sizes are allowed, we'll put them to the right strictly for this project
            // to simplify handling implicit duplicates (though real AVL usually rejects dups).
            // Actually, for file sys, duplicates in size are common. 
            // Let's settle on: if size is EQUAL, we go RIGHT.
             node->right = insert(node->right, uid, name, size);
        }

        // 2. Update height of this ancestor node
        node->height = 1 + max(height(node->left), height(node->right));

        // 3. Get the balance factor of this ancestor node to check whether
        // this node became unbalanced
        int balance = getBalance(node);

        // If this node becomes unbalanced, then there are 4 cases

        // Left Left Case
        if (balance > 1 && size < node->left->size)
            return rightRotate(node);

        // Right Right Case
        if (balance < -1 && size >= node->right->size) // >= because we put equals on right
            return leftRotate(node);

        // Left Right Case
        if (balance > 1 && size > node->left->size) {
            node->left = leftRotate(node->left);
            return rightRotate(node);
        }

        // Right Left Case
        if (balance < -1 && size < node->right->size) {
            node->right = rightRotate(node->right);
            return leftRotate(node);
        }

        /* return the (unchanged) node pointer */
        return node;
    }

    // Wrapper for insert
    void addFile(string uid, string name, long long size) {
        root = insert(root, uid, name, size);
    }

    // Reverse In-Order Traversal to get TOP K largest items
    // (Right -> Root -> Left)
    void getTopK(Node* node, int& count, int k) {
        if (node == nullptr || count >= k)
            return;

        // 1. Visit Right (Larger values)
        getTopK(node->right, count, k);

        // 2. Visit Node
        if (count < k) {
            cout << node->size << "|" << node->name << "|" << node->uid << endl;
            count++;
        }

        // 3. Visit Left (Smaller values)
        getTopK(node->left, count, k);
    }

    void displayTop(int k) {
        int count = 0;
        getTopK(root, count, k);
    }
};

// ---------------- Main Driver ----------------
int main() {
    AVLTree tree;
    string line;
    
    // Format expected from Python: UID|NAME|SIZE
    while (getline(cin, line)) {
        if (line.empty()) continue;
        
        stringstream ss(line);
        string segment;
        vector<string> parts;
        
        while(getline(ss, segment, '|')) {
            parts.push_back(segment);
        }
        
        if (parts.size() >= 3) {
            try {
                // Parse fields
                string uid = parts[0];
                string name = parts[1];
                long long size = stoll(parts[2]);
                tree.addFile(uid, name, size);
            } catch (...) {
                // Ignore malformed lines
                continue;
            }
        }
    }

    // Once input is finished (EOF), we print the report
    // Let's print top 10 for now (could also be an argument)
    tree.displayTop(10);

    return 0;
}
