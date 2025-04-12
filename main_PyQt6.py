# pyqt6_app.py

import sys
import os
import bcrypt

from PyQt6.QtWebEngineWidgets import QWebEngineView  # Add at the top

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QCheckBox, QGridLayout, QVBoxLayout, QHBoxLayout
)
from PyQt6.QtGui import QFont, QDesktopServices
from PyQt6.QtCore import Qt, QUrl

##############################
# Global session variable
##############################
current_user = None

##############################
# MongoDB Setup
##############################
load_dotenv()
username = "test"
password = os.getenv("MONGODB_PASSWORD")
if not password:
    raise ValueError("MONGODB_PASSWORD not set in .env")

uri = f"mongodb+srv://{username}:{password}@cluster0.lygyuzf.mongodb.net/?appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["slughub"]
collection = db["class_schedule"]
user_collection = db["users"]

##############################
# Password security
##############################
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

##############################
# User Authentication
##############################
def create_user(username, email, password):
    if user_collection.find_one({"username": username}):
        return False, "Username already exists."
    if user_collection.find_one({"email": email}):
        return False, "Email already registered."
    hashed_pw = hash_password(password)
    user_collection.insert_one({
        "username": username,
        "email": email,
        "password": hashed_pw
    })
    return True, "Account created successfully!"

def authenticate_user(username, password):
    user = user_collection.find_one({"username": username})
    if not user:
        return False, "User not found."
    if verify_password(password, user["password"]):
        return True, user
    return False, "Invalid password."

##############################
# Class Schedule Helpers
##############################
def get_all_classes(user):
    try:
        return list(collection.find({"user": user}, {"_id": 0}))
    except Exception as e:
        print(f"[MongoDB] Error loading classes: {e}")
        return []

def save_class(data, user):
    try:
        data["user"] = user
        # Insert only if not duplicate
        if not collection.find_one(data):
            collection.insert_one(data)
    except Exception as e:
        print(f"[MongoDB] Error saving class: {e}")

##############################
# Constants / Styles
##############################
APP_BG_COLOR     = "#F5F5F5"     # Soft light gray background
TEXT_COLOR       = "#000000"     # Black text
BUTTON_BG        = "#0077CC"     # Blue buttons
BUTTON_HOVER     = "#3399FF"     # Lighter blue on hover
BACK_BUTTON_BG   = "#DDEEFF"     # Soft blue for secondary/back buttons
BACK_BUTTON_TEXT = "#000000"     # Black text for back buttons
BUTTON_TEXT      = "#000000"     # Black text for buttons

def set_widget_bg(widget, color=APP_BG_COLOR):
    """Helper to apply a background color via style sheet."""
    widget.setStyleSheet(f"background-color: {color};")

##############################
# Individual Pages as Widgets
##############################

class LoginPage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        set_widget_bg(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title_label = QLabel("Welcome to SlugHub")
        title_label.setFont(QFont("Helvetica", 20, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(20)

        # Username
        layout.addWidget(QLabel("Username:"))
        self.username_edit = QLineEdit()
        layout.addWidget(self.username_edit)

        # Password
        layout.addWidget(QLabel("Password:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit)

        # Message label
        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red;")
        layout.addWidget(self.message_label)

        # Buttons
        btn_login = QPushButton("🔓 Login")
        btn_login.clicked.connect(self.login_user)
        btn_login.setStyleSheet("""
            background-color: #28A745;   /* Bootstrap green */
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_login)

        btn_register = QPushButton("📝 Create New Account")
        btn_register.clicked.connect(lambda: self.main_window.show_page("RegisterPage"))
        btn_register.setStyleSheet("""
            background-color: #30D1E4;   /* Bootstrap green */
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_register)

        layout.addStretch()

                                   

    def login_user(self):
        global current_user
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        success, user = authenticate_user(username, password)
        if success:
            current_user = user["username"]
            self.main_window.show_page("HomePage")
        else:
            self.message_label.setText(user)


class RegisterPage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        set_widget_bg(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title_label = QLabel("Create Account")
        title_label.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)

        # Username
        layout.addWidget(QLabel("Username:"))
        self.user_edit = QLineEdit()
        layout.addWidget(self.user_edit)

        # Email
        layout.addWidget(QLabel("Email:"))
        self.email_edit = QLineEdit()
        layout.addWidget(self.email_edit)

        # Password
        layout.addWidget(QLabel("Password:"))
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_edit)

        # Confirm Password
        layout.addWidget(QLabel("Confirm Password:"))
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_edit)

        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red;")
        layout.addWidget(self.message_label)

        btn_register = QPushButton("✅ Register")
        btn_register.clicked.connect(self.register_user)
        btn_register.setStyleSheet("""
            background-color: #5BB2F7;   /* Bootstrap green */
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_register)

        btn_back = QPushButton("⬅ Back to Login")
        
        btn_back.clicked.connect(lambda: self.main_window.show_page("LoginPage"))
        btn_back.setStyleSheet("""
            background-color: #28A745;   /* Bootstrap green */
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_back)

        layout.addStretch()

    def register_user(self):
        username = self.user_edit.text().strip()
        email = self.email_edit.text().strip()
        password = self.pass_edit.text()
        confirm = self.confirm_edit.text()

        if not username or not email or not password or not confirm:
            self.message_label.setText("⚠️ Please fill out all fields.")
            return
        if password != confirm:
            self.message_label.setText("⚠️ Passwords do not match.")
            return

        success, msg = create_user(username, email, password)
        self.message_label.setText(msg)
        if success:
            self.message_label.setStyleSheet("color: green;")
            self.main_window.show_page("LoginPage")
        else:
            self.message_label.setStyleSheet("color: red;")


class HomePage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        set_widget_bg(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title_label = QLabel("Welcome to SlugHub")
        title_label.setFont(QFont("Helvetica", 22, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(20)

        btn_schedule = QPushButton("🗓️ Enter Class Schedule")
        btn_schedule.clicked.connect(lambda: self.main_window.show_page("ScheduleInputPage"))
        btn_schedule.setStyleSheet("""
            background-color: #30D1E4;   /* Bootstrap green */
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_schedule)

        btn_resources = QPushButton("📚 Resources")
        btn_resources.clicked.connect(lambda: self.main_window.show_page("ResourcesPage"))
        btn_resources.setStyleSheet("""
            background-color: #FBE35C;   /* Bootstrap green */
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_resources)

        btn_logout = QPushButton("🔐 Logout")
        btn_logout.clicked.connect(self.logout_user)
        btn_logout.setStyleSheet("""
            background-color: #28A745;   /* Bootstrap green */
            color: white;
            border-radius: 6px;
            padding: 6px 10px;
            min-height: 30px;
            min-width: 30x;
            font-size: 12px;
        """)
        
        btn_map = QPushButton("🗺️ Campus Map")
        btn_map.clicked.connect(lambda: self.main_window.show_page("MapPage"))
        btn_map.setStyleSheet("""
            background-color: #A2D729;
            color: white;
            border-radius: 6px;
            padding: 8px 14px;
        """)
        layout.addWidget(btn_map)
        
        layout.addStretch()
        logout_container = QHBoxLayout()
        logout_container.addStretch()
        logout_container.addWidget(btn_logout)
        logout_container.addStretch()

        layout.addLayout(logout_container)

    def logout_user(self):
        global current_user
        current_user = None
        self.main_window.show_page("LoginPage")


class ResourcesPage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        set_widget_bg(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title_label = QLabel("Resources")
        title_label.setFont(QFont("Helvetica", 20, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)

        sub_label = QLabel("Commonly Used Links:")
        sub_label.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        layout.addWidget(sub_label)

        def open_link(url):
            QDesktopServices.openUrl(QUrl(url))

        btn_textbook = QPushButton("📘 Textbook Website")
        btn_textbook.clicked.connect(lambda: open_link("https://ucsc.textbookx.com/"))
        btn_textbook.setStyleSheet("""
            background-color: #30D1E4;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_textbook)

        btn_canvas = QPushButton("🎓 Canvas Portal")
        btn_canvas.clicked.connect(lambda: open_link("https://canvas.ucsc.edu"))
        btn_canvas.setStyleSheet("""
            background-color: #FBE35C;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_canvas)

        btn_mycusc = QPushButton("🧾 MyUCSC Portal")
        btn_mycusc.clicked.connect(lambda: open_link("https://my.ucsc.edu/psc/csprd/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL?"))
        btn_mycusc.setStyleSheet("""
            background-color: #30D1E4;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_mycusc)

        layout.addSpacing(20)

        sub_label2 = QLabel("Book a Study Room:")
        sub_label2.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        layout.addWidget(sub_label2)

        hbox = QHBoxLayout()
        layout.addLayout(hbox)

        btn_mchenry = QPushButton("📚 McHenry")
        btn_mchenry.clicked.connect(lambda: open_link("https://calendar.library.ucsc.edu/spaces?lid=16577"))
        btn_mchenry.setStyleSheet("""
            background-color: #30D1E4;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        hbox.addWidget(btn_mchenry)

        btn_se = QPushButton("🔬 S&E")
        btn_se.clicked.connect(lambda: open_link("https://calendar.library.ucsc.edu/spaces?lid=16578"))
        btn_se.setStyleSheet("""
            background-color: #FBE35C;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        hbox.addWidget(btn_se)

        layout.addSpacing(20)
        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        btn_se.setStyleSheet("""
            background-color: #28A745;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()


class ScheduleInputPage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        set_widget_bg(self)

        self.schedule_data = []
        self.days_vars = {}

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        title_label = QLabel("Class Schedule Input")
        title_label.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addSpacing(10)

        form_layout = QGridLayout()
        main_layout.addLayout(form_layout)

        # Class Name
        lbl_class = QLabel("Class Name:")
        self.edit_class_name = QLineEdit()
        form_layout.addWidget(lbl_class, 0, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.edit_class_name, 0, 1)

        # Location
        lbl_location = QLabel("Location:")
        self.edit_location = QLineEdit()
        form_layout.addWidget(lbl_location, 1, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.edit_location, 1, 1)

        # Days
        lbl_days = QLabel("Days:")
        form_layout.addWidget(lbl_days, 2, 0, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        days_container = QWidget()
        days_hbox = QHBoxLayout(days_container)
        days_container.setLayout(days_hbox)
        form_layout.addWidget(days_container, 2, 1)

        for day in ["M", "T", "W", "Th", "F"]:
            cb = QCheckBox(day)
            cb.stateChanged.connect(self.update_start_times)
            days_hbox.addWidget(cb)
            self.days_vars[day] = cb

        # Start Time
        lbl_start_time = QLabel("Start Time:")
        self.combo_start_time = QComboBox()
        form_layout.addWidget(lbl_start_time, 3, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.combo_start_time, 3, 1)

        btn_add = QPushButton("➕ Add Class")
        btn_add.clicked.connect(self.add_class)
        btn_add.setStyleSheet("""
            background-color: #FBE35C;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 6px 10px
        """)

        main_layout.addWidget(btn_add, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.class_display = QTextEdit()
        self.class_display.setReadOnly(True)
        main_layout.addWidget(self.class_display)

        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        btn_back.setStyleSheet("""
            background-color: #28A745;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 8px 14px
        """)
        main_layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addStretch()

    def update_start_times(self):
        """Generate start times based on selected days."""
        selected_days = [d for d, cb in self.days_vars.items() if cb.isChecked()]
        mwf = ["8:00 AM", "9:20 AM", "10:40 AM", "12:00 PM", "1:20 PM", "2:40 PM", "4:00 PM"]
        evening = ["5:20 PM", "7:10 PM"]
        tuth = ["8:00 AM", "9:50 AM", "11:40 AM", "1:30 PM", "3:20 PM"]
        valid = []

        if all(day in selected_days for day in ["M", "W", "F"]):
            valid = mwf
        elif set(selected_days) == {"M", "W"} or set(selected_days) == {"T", "Th"}:
            valid = tuth + evening
        elif selected_days:
            valid = sorted(set(mwf + tuth + evening))

        self.combo_start_time.clear()
        if not valid:
            self.combo_start_time.addItem("(select days)")
        else:
            self.combo_start_time.addItems(valid)

    def add_class(self):
        global current_user
        name = self.edit_class_name.text().strip()
        location = self.edit_location.text().strip()
        start_time = self.combo_start_time.currentText()
        days = [d for d, cb in self.days_vars.items() if cb.isChecked()]

        if not name or not location or not days or "(select days)" in start_time:
            self.class_display.append("⚠️ Please complete all fields correctly.\n")
            return

        class_info = {
            "name": name,
            "location": location,
            "start_time": start_time,
            "days": days
        }

        self.schedule_data.append(class_info)
        if current_user:
            save_class(class_info, current_user)
        self.display_schedule()

        # Reset form
        self.edit_class_name.clear()
        self.edit_location.clear()
        for cb in self.days_vars.values():
            cb.setChecked(False)
        self.update_start_times()

    def display_schedule(self):
        self.class_display.clear()
        for cls in self.schedule_data:
            line = f"{cls['name']} @ {cls['location']} on {', '.join(cls['days'])} at {cls['start_time']}\n"
            self.class_display.append(line)

    def refresh(self):
        """Called each time we show this page, to re-fetch the schedule from DB."""
        global current_user
        if current_user:
            self.schedule_data = get_all_classes(current_user)
        else:
            self.schedule_data = []
        self.display_schedule()


class MapPage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Load API key from .env
        load_dotenv()
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found in .env")

        # Read and inject API key into HTML
        with open("map.html", "r", encoding="utf-8") as f:
            html = f.read().replace("YOUR_API_KEY", api_key)

        browser = QWebEngineView()
        browser.setHtml(html)
        layout.addWidget(browser)

        # Back button
        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        btn_back.setStyleSheet("""
            background-color: #28A745;
            color: white;
            border-radius: 6px;
            padding: 8px 14px;
        """)
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)



##############################
# Main Window + StackedWidget
##############################

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SlugHub - Student Assistance")
        self.setFixedSize(500, 600)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Dictionary mapping page names to indexes
        self.page_ids = {}

        # Create and add pages
        pages = [
            ("LoginPage", LoginPage),
            ("RegisterPage", RegisterPage),
            ("HomePage", HomePage),
            ("ResourcesPage", ResourcesPage),
            ("ScheduleInputPage", ScheduleInputPage),
            ("MapPage", MapPage)
        ]

        for name, PageClass in pages:
            page_instance = PageClass(main_window=self)
            index = self.stacked_widget.addWidget(page_instance)
            self.page_ids[name] = index

        # Start on login
        self.show_page("LoginPage")

    def show_page(self, page_name):
        """Switch to the page by name. If it's the ScheduleInputPage, call refresh()."""
        if page_name not in self.page_ids:
            return
        idx = self.page_ids[page_name]
        widget = self.stacked_widget.widget(idx)
        # If the page is the schedule page, refresh
        if page_name == "ScheduleInputPage":
            widget.refresh()

        self.stacked_widget.setCurrentIndex(idx)


def main():
    app = QApplication(sys.argv)

    app.setStyleSheet(f"""
        QWidget {{
            color: {TEXT_COLOR};
            background-color: {APP_BG_COLOR};
            font-family: Helvetica;
        }}
        QLabel {{
            color: {TEXT_COLOR};
            background-color: transparent;
        }}
        QLineEdit, QTextEdit, QComboBox {{
            background-color: transparent;
            color: {TEXT_COLOR};
            border: 1px solid #999;
            padding: 6px;
        }}
        QPushButton {{
            background-color: {BUTTON_BG};
            color: {BUTTON_TEXT};
            border-radius: 8px;
            padding: 12px 16px;
            min-width: 200px;
            min-height: 50px;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {BUTTON_HOVER};
        }}
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
