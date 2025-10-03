#include <iostream>
using namespace std;

int main() {
    int n;
    cout << "Enter a number: ";

    // Check for non-integer input
    if (!(cin >> n)) {
        cout << "Invalid input. Please enter an integer." << endl;
        return 1;
    }

    // Check if number is even or odd
    if (n % 2 == 0) {
        cout << n << " is even." << endl;
    } else {
        cout << n << " is odd." << endl;
    }

    // Handle non-positive input
    if (n > 0) {
        cout << "First " << n << " natural numbers: ";
        for (int i = 1; i <= n; i++) {
            cout << i << " ";
        }
        cout << endl;
    } else {
        cout << "Please enter a positive number to print natural numbers." << endl;
    }

    return 0;
}
