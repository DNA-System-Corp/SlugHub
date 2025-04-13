# pyqt6_app.py
from functools import partial
import sys
import os
import bcrypt
import uuid

from datetime import datetime

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient    
from pymongo.server_api import ServerApi

from PyQt6.QtCore import Qt, QObject, pyqtSlot, QUrl
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QLabel, QLineEdit,
    QPushButton, QTextEdit, QComboBox, QCheckBox, QGridLayout, QVBoxLayout,
    QHBoxLayout, QSizePolicy
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QGuiApplication, QDesktopServices, QPixmap



# Must do this BEFORE QApplication is created
QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

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
        if not collection.find_one({"user": user, "id": data["id"]}):
            collection.insert_one(data)
    except Exception as e:
        print(f"[MongoDB] Error saving class: {e}")

##############################
# Constants / Styles
##############################
APP_BG_COLOR     = "#8fc1ff"     # Soft light gray background
TEXT_COLOR       = "#000000"     # Black text
BUTTON_BG        = "#161a7d"     # Blue buttons
BUTTON_HOVER     = "#0a0c47"     # Lighter blue on hover
BACK_BUTTON_BG   = "#F7DB3E"     # Soft blue for secondary/back buttons
BACK_HOVER_BG    = "#d1ba34"
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
        self.username_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        layout.addWidget(self.username_edit)

        # Password
        layout.addWidget(QLabel("Password:"))
        self.password_edit = QLineEdit()
        self.password_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit)

        # Message label
        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red;")
        layout.addWidget(self.message_label)

        # Buttons
        btn_login = QPushButton("🔓 Login")
        btn_login.clicked.connect(self.login_user)
        btn_login.setStyleSheet(f"""
            QPushButton {{
                background-color: #28A745;   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000
            }}
            QPushButton:hover {{
                background-color: #0D7024
            }}
        """)
        layout.addWidget(btn_login)

        btn_register = QPushButton("📝 Create New Account")
        btn_register.clicked.connect(lambda: self.main_window.show_page("RegisterPage"))
        btn_register.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        layout.addWidget(btn_register)

        label = QLabel(self)
        pixmap = QPixmap('Sluggy.png')
        scaled_pixmap = pixmap.scaled(500, 300)
        label.setPixmap(scaled_pixmap)
        layout.addWidget(label, alignment= Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)

       # label.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
        self.user_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        layout.addWidget(self.user_edit)

        # Email
        layout.addWidget(QLabel("Email:"))
        self.email_edit = QLineEdit()
        self.email_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        layout.addWidget(self.email_edit)

        # Password
        layout.addWidget(QLabel("Password:"))
        self.pass_edit = QLineEdit()
        self.pass_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_edit)

        # Confirm Password
        layout.addWidget(QLabel("Confirm Password:"))
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_edit)

        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red;")
        layout.addWidget(self.message_label)

        btn_register = QPushButton("✅ Register")
        btn_register.clicked.connect(self.register_user)
        btn_register.setStyleSheet(f"""
            QPushButton: {{
                background-color: {BUTTON_BG};   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;              
            }}                     
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        layout.addWidget(btn_register)

        btn_back = QPushButton("⬅ Back to Login")
        btn_back.clicked.connect(lambda: self.main_window.show_page("LoginPage"))
        btn_back.setStyleSheet( """
            QPushButton: {{
                background-color: #28A745;   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }}
            QPushButton:hover {{
                background-color: #0D7024
            }}
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

        btn_schedule = QPushButton("🗓️ Class Schedule")
        btn_schedule.clicked.connect(lambda: self.main_window.show_page("ScheduleInputPage"))
        btn_schedule.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        layout.addWidget(btn_schedule)

        btn_resources = QPushButton("📚 Resources")
        btn_resources.clicked.connect(lambda: self.main_window.show_page("ResourcesPage"))
        btn_resources.setStyleSheet(f"""
            QPushButton {{
                background-color: {BACK_BUTTON_BG};   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000
            }}
            QPushButton:hover {{
                background-color: {BACK_HOVER_BG}
            }}
        """)
        layout.addWidget(btn_resources)

        btn_logout = QPushButton("🔐 Logout")
        btn_logout.clicked.connect(self.logout_user)
        btn_logout.setStyleSheet("""
            QPushButton{
            background-color: #28A745;   /* Bootstrap green */
            color: white;
            border-radius: 6px;
            padding: 6px 10px;
            min-height: 30px;
            min-width: 30x;
            font-size: 12px;
            border: 2px solid #000000
            }
            QPushButton:hover{
                background-color: #0D7024
            }
        """)
        
        btn_map = QPushButton("🗺️ Campus Map")
        btn_map.clicked.connect(lambda: self.main_window.show_page("MapPage"))
        btn_map.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
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
        btn_textbook.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};   /* Bootstrap green fbe35c*/
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        layout.addWidget(btn_textbook)

        btn_canvas = QPushButton("🎓 Canvas Portal")
        btn_canvas.clicked.connect(lambda: open_link("https://canvas.ucsc.edu"))
        btn_canvas.setStyleSheet(f"""
            QPushButton {{
                background-color: {BACK_BUTTON_BG};   /* Bootstrap green fbe35c*/
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }}
            QPushButton:hover {{
                background-color: {BACK_HOVER_BG}
            }}
        """)
        layout.addWidget(btn_canvas)

        btn_mycusc = QPushButton("🧾 MyUCSC Portal")
        btn_mycusc.clicked.connect(lambda: open_link("https://my.ucsc.edu/psc/csprd/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL?"))
        btn_mycusc.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};   /* BLUE*/
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
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
        btn_mchenry.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};   /* YELLOW*/
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        hbox.addWidget(btn_mchenry)

        btn_se = QPushButton("🔬 S&E")
        btn_se.clicked.connect(lambda: open_link("https://calendar.library.ucsc.edu/spaces?lid=16578"))
        btn_se.setStyleSheet(f"""
            QPushButton {{
                background-color: {BACK_BUTTON_BG};   /* Bootstrap green fbe35c*/
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }}
            QPushButton:hover {{
                background-color: {BACK_HOVER_BG}
            }}
        """)
        hbox.addWidget(btn_se)

        layout.addSpacing(20)
        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        btn_back.setStyleSheet("""
            QPushButton{
            background-color: #28A745;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 8px 14px;
            border: 2px solid #000000;
            }
            QPushButton:hover{
                background-color: #0D7024
            }
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

        # Title
        title_label = QLabel("Class Schedule Input")
        title_label.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addSpacing(10)

        # Form layout
        form_layout = QGridLayout()
        main_layout.addLayout(form_layout)

        # Class Name
        lbl_class = QLabel("Class Name:")
        self.edit_class_name = QLineEdit()
        self.edit_class_name.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        form_layout.addWidget(lbl_class, 0, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.edit_class_name, 0, 1)

        # Location
        lbl_location = QLabel("Location:")
        self.edit_location = QLineEdit()
        self.edit_location.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
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
        self.combo_start_time.setStyleSheet('''
            QComboBox { background-color: #FFFFFF}
            QComboBox QAbstractItemView { background-color: #FFFFFF }
            ''')
        form_layout.addWidget(lbl_start_time, 3, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.combo_start_time, 3, 1)

        # Add Class Button
        btn_add = QPushButton("➕ Add Class")
        btn_add.clicked.connect(self.add_class)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};
                color: white;
                border-radius: 6px;
                padding: 6px 10px;
                border: 2px solid #000000;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        main_layout.addWidget(btn_add, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Warning Label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red;")
        main_layout.addWidget(self.warning_label)

        # Class Display Area
        self.class_display_container = QWidget()
        self.class_display_layout = QVBoxLayout()
        self.class_display_container.setLayout(self.class_display_layout)
        main_layout.addWidget(self.class_display_container)

        # Back to Home Button
        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: #28A745;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }}
            QPushButton:hover {{
                background-color: #0D7024
            }}
        """)
        main_layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addStretch()

    def update_start_times(self):
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
            self.warning_label.setText("⚠️ Please complete all fields correctly.")
            return

        self.warning_label.setText("")

        class_info = {
            "id": str(uuid.uuid4()),
            "name": name,
            "location": location,
            "start_time": start_time,
            "days": days
        }

        if current_user:
            save_class(class_info, current_user)

        self.refresh()  # Reload data

        # Reset form
        self.edit_class_name.clear()
        self.edit_location.clear()
        for cb in self.days_vars.values():
            cb.setChecked(False)
        self.update_start_times()

    def delete_class(self, class_info):
        global current_user
        class_id = class_info.get("id")
        if current_user:
            try:
                collection.delete_one({"user": current_user, "id": class_id})
            except Exception as e:
                print(f"[MongoDB] Error deleting class: {e}")
        self.refresh()

    def display_schedule(self):
        # Clear previous widgets
        for i in reversed(range(self.class_display_layout.count())):
            widget_to_remove = self.class_display_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)

        for cls in self.schedule_data:
            days = cls["days"]
            day_str = ''.join(days)
            if days == ["T", "Th"]:
                day_str = "TuTh"
            elif set(days) == {"M", "W"}:
                day_str = "MW"
            elif set(days) == {"M", "W", "F"}:
                day_str = "MWF"

            # Info Label
            label = QLabel(f"{cls['name']}\n{day_str} @ {cls['start_time']}\n{cls['location']}")
            label.setStyleSheet("""
                QLabel {
                    background-color: #DDEEFF;
                    color: #000000;
                    border: 1px solid #999;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 14px;
                }
                QLabel:hover {
                    background-color: #c9def2;
                }
            """)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedWidth(250)

            # Trash Button
            btn_delete = QPushButton("🗑️")
            btn_delete.setFixedSize(12, 12)
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #FF6666;
                    color: white;
                    border-radius: 6px;
                    font-size: 10px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #FF4444;
                }
            """)
            btn_delete.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn_delete.clicked.connect(partial(self.delete_class, cls))

            # Class Block Layout
            block_layout = QHBoxLayout()
            block_layout.setSpacing(10)
            block_layout.addWidget(label)
            block_layout.addWidget(btn_delete)

            class_block_widget = QWidget()
            outer_layout = QHBoxLayout()
            outer_layout.addStretch()
            outer_layout.addLayout(block_layout)
            outer_layout.addStretch()
            class_block_widget.setLayout(outer_layout)

            self.class_display_layout.addWidget(class_block_widget)

    def refresh(self):
        global current_user
        self.schedule_data = []
        if current_user:
            self.schedule_data = get_all_classes(current_user)
        self.display_schedule()

##############################
# MapPage with route-to-next-class
##############################
DAY_MAP = {
    0: "M",   # Monday
    1: "T",
    2: "W",
    3: "Th",
    4: "F",
    # ignoring Sat(5)/Sun(6)
}

class MapBridge(QObject):
    """
    Bridge for the web channel. JavaScript calls window.bridge.mapReady()
    when google maps has initialized.
    """
    def __init__(self, map_page):
        super().__init__()
        self.map_page = map_page

    @pyqtSlot()
    def mapReady(self):
        self.map_page.on_map_ready()

class MapPage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.map_is_ready = False
        self.pending_destination = None
        self.current_travel_mode = "DRIVING"

        # Track if we've loaded the map yet
        self._map_loaded = False

        # Main layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        #
        # 1) Top row: Travel Mode Buttons
        #
        mode_layout = QHBoxLayout()

        btn_drive = QPushButton("Drive")
        btn_drive.clicked.connect(lambda: self.set_travel_mode("DRIVING"))
        mode_layout.addWidget(btn_drive)

        btn_walk = QPushButton("Walk")
        btn_walk.clicked.connect(lambda: self.set_travel_mode("WALKING"))
        mode_layout.addWidget(btn_walk)

        btn_bike = QPushButton("Bike")
        btn_bike.clicked.connect(lambda: self.set_travel_mode("BICYCLING"))
        mode_layout.addWidget(btn_bike)

        btn_transit = QPushButton("Transit")
        btn_transit.clicked.connect(lambda: self.set_travel_mode("TRANSIT"))
        mode_layout.addWidget(btn_transit)

        self.layout.addLayout(mode_layout)

        #
        # 2) "Back to Home" Button
        #
        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        btn_back.setStyleSheet("""
            QPushButton{
            background-color: #28A745;   /* Bootstrap green fbe35c*/
            color: white;
            border-radius: 6px;
            padding: 8px 14px;
            }
            QPushButton:hover{
                background-color: #0D7024
            }
        """)
        self.layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)

    def load_map(self):
        """ Actually load the QWebEngine map only once. """
        if self._map_loaded:
            return  # Already loaded

        self._map_loaded = True

        load_dotenv()
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found in .env")

        # Read map.html and inject QWebChannel + API key
        with open("map.html", "r", encoding="utf-8") as f:
            html = f.read().replace("YOUR_API_KEY", api_key)
        # Insert the qwebchannel script
        html = html.replace("</head>", "<script src='qrc:///qtwebchannel/qwebchannel.js'></script></head>")

        # Now create the browser and bridge
        self.browser = QWebEngineView()
        self.channel = QWebChannel()
        self.bridge = MapBridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        # Load the HTML
        self.browser.setHtml(html)

        # Insert the browser at the *top* of the layout, or wherever you like
        self.layout.insertWidget(0, self.browser)

    def set_travel_mode(self, mode):
        """Change travel mode and tell the JS side (setTravelMode)."""
        self.current_travel_mode = mode
        # If the map is already ready, update the JS travel mode
        if self.map_is_ready:
            script = f'setTravelMode("{mode}");'
            self.browser.page().runJavaScript(script)
            # Optionally reroute if there's already a destination
            if self.pending_destination:
                self.route_to(self.pending_destination)

    def on_map_ready(self):
        """
        Called once JS side map initialization is finished.
        """
        self.map_is_ready = True

        # Make sure the map starts with the current travel mode
        self.set_travel_mode(self.current_travel_mode)

        # Attempt routing to next class
        self.route_to_next_class()

    def route_to(self, destination):
        """
        Sends the createRoute() call to JavaScript.
        """
        if not self.map_is_ready:
            self.pending_destination = destination
            return

        self.pending_destination = destination  # store it so we can re-route after changing modes
        script = f'createRoute("{destination}");'
        self.browser.page().runJavaScript(script)

    def route_to_next_class(self):
        """
        Looks up the user's next upcoming class from the DB and calls route_to().
        """
        global current_user
        if not current_user:
            print("No user logged in; can't load schedule.")
            return

        schedule = get_all_classes(current_user)
        if not schedule:
            print("User has no classes saved.")
            return

        today = datetime.today()
        now_str = today.strftime("%I:%M %p")  # e.g. "02:40 PM"
        weekday_index = today.weekday()       # 0=Mon, 6=Sun

        upcoming_classes = []

        # Look up to 7 days ahead
        for offset in range(7):
            check_day = (weekday_index + offset) % 7
            day_letter = DAY_MAP.get(check_day)
            if not day_letter:
                # skip Sat/Sun or anything out of DAY_MAP
                continue

            for cls in schedule:
                if day_letter in cls["days"]:
                    # If it's the same day, skip classes that already started
                    if offset == 0 and cls["start_time"] <= now_str:
                        continue
                    upcoming_classes.append((offset, cls))

            # If we found any classes for this day, no need to keep looking further days
            if upcoming_classes:
                break

        if not upcoming_classes:
            print("No upcoming classes found in the next week.")
            return

        # Sort by day-offset first, then start time
        next_class = sorted(upcoming_classes, key=lambda x: (x[0], x[1]["start_time"]))[0][1]
        print(f"Next class: {next_class['name']} at {next_class['start_time']} → {next_class['location']}")
        self.route_to(next_class["location"])


##############################
# Main Window + StackedWidget
##############################

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SlugHub - Student Assistance")
        self.setFixedSize(800, 700)

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
        if page_name not in self.page_ids:
            return
        idx = self.page_ids[page_name]
        widget = self.stacked_widget.widget(idx)

        # Refresh if it's the schedule input page
        if page_name == "ScheduleInputPage":
            widget.refresh()

        # If the page is the map page, load the map
        if page_name == "MapPage":
            widget.load_map()

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
