import sys
import subprocess
import re
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, 
                             QVBoxLayout, QMessageBox, QLineEdit, QInputDialog)
from ldap3 import Server, Connection, ALL

def get_fqdn_user():
    try:
        output = subprocess.check_output("whoami /fqdn", shell=True, universal_newlines=True)
        match = re.search(r'CN=.*', output)
        if match:
            return match.group(0).strip()
    except Exception as e:
        print("Error getting FQDN:", e)
    return None

def determine_role(distinguished_name):
    if "OU=Users" in distinguished_name:
        return "login as User"
    elif "OU=TL/SME" in distinguished_name:
        return "login as TL SME"
    elif "OU=PMO" in distinguished_name:
        return "login as PMO"
    elif "OU=IT" in distinguished_name:
        return "login as Admin"
    else:
        return "login as Unknown"

def check_ldap_login(user, password):
    domain_user = f"rprocess\\{user}"
    server = Server('172.17.1.247', get_info=ALL)
    conn = Connection(server, user=domain_user, password=password, auto_bind=True)
    return conn.bound

class LoginApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Role Based Login Checker")
        self.setGeometry(100, 100, 400, 180)
        self.setup_ui()

    def setup_ui(self):
        self.label = QLabel("Press Login to check your role by AD structure.")
        self.button = QPushButton("Login")
        self.button.clicked.connect(self.handle_login)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def handle_login(self):
        user, ok_user = QInputDialog.getText(self, "Username", "Enter your AD username (e.g. rm014705):")
        if not (ok_user and user):
            QMessageBox.information(self, "Cancelled", "Login cancelled.")
            return

        password, ok_pass = QInputDialog.getText(self, "Password", 
                                                 "Enter your AD password:", 
                                                 QLineEdit.Password)
        if not (ok_pass and password):
            QMessageBox.information(self, "Cancelled", "Login cancelled.")
            return

        dn = get_fqdn_user()
        if dn:
            print(f"Found FQDN: {dn}")
            try:
                if check_ldap_login(user, password):
                    role = determine_role(dn)
                    QMessageBox.information(self, "Login Successful", 
                                            f"✅ Authentication successful!\nRole: {role}")
                else:
                    QMessageBox.warning(self, "Login Failed", 
                                        "⛔ Invalid credentials.")
            except Exception as e:
                QMessageBox.critical(self, "Login Error", f"❌ Could not connect to LDAP:\n{e}")
        else:
            QMessageBox.critical(self, "Login", "❌ Could not determine your FQDN.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginApp()
    window.show()
    sys.exit(app.exec_())
