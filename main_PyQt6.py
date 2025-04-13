# pyqt6_app.py
from functools import partial
import sys
import os
import bcrypt
import uuid
from PyQt6.QtWidgets import QScrollArea, QMessageBox
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient    
from pymongo.server_api import ServerApi
from class_forum_scraper import fetch_all_ucsc_classes
from PyQt6.QtCore import Qt, QObject, pyqtSlot, QUrl, QVariant
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QLabel, QLineEdit,
    QPushButton, QTextEdit, QComboBox, QCheckBox, QGridLayout, QVBoxLayout,
    QHBoxLayout, QSizePolicy
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QGuiApplication, QDesktopServices, QPixmap
from eventscraper import scrape_ucsc_events

from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtCore import QTimer
import geocoder



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
class_collection = db["all_ucsc_classes"]
forum_collection = db["forum_posts"]
collection = db["class_schedule"]
user_collection = db["users"]

def store_classes_in_db():
    """Scrape the catalog, then store the entire list of courses in a single MongoDB document."""
    classes = fetch_all_ucsc_classes()
    if not classes:
        #print("No classes found or scraping failed.")
        return

    # We'll store them all in one doc with a known _id, e.g. "ucsc_course_list"
    # so we can easily upsert or retrieve them.
    doc = {
        "_id": "ucsc_course_list",
        "courses": classes
    }
    class_collection.replace_one({"_id": "ucsc_course_list"}, doc, upsert=True)
    print(f"Stored {len(classes)} classes in the DB under _id='ucsc_course_list'.")

def get_saved_ucsc_classes():
    """Retrieve our stored course codes from the MongoDB collection."""
    doc = class_collection.find_one({"_id": "ucsc_course_list"})
    if doc:
        return doc["courses"]  # e.g. ["CSE 107", "MATH 19A", ...]
    return []
VALID_UCSC_CLASSES = get_saved_ucsc_classes()
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

        title_image = QLabel(self)
        pixmap = QPixmap('logo.png').scaled(500, 325)
        title_image.setPixmap(pixmap)
        title_image.setStyleSheet("background: transparent;")
        layout.addWidget(title_image, alignment= Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        # Username
        user_label_text = QLabel("Username:")
        user_label_text.setStyleSheet("background: transparent;")
        layout.addWidget(user_label_text, alignment=Qt.AlignmentFlag.AlignCenter)
        self.username_edit = QLineEdit()
        self.username_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        self.username_edit.setFixedWidth(400)
        layout.addWidget(self.username_edit, alignment=Qt.AlignmentFlag.AlignCenter)

        # Password
        pass_label_text = QLabel("Password:")
        pass_label_text.setStyleSheet("background: transparent;")
        layout.addWidget(pass_label_text, alignment=Qt.AlignmentFlag.AlignCenter)
        self.password_edit = QLineEdit()
        self.password_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setFixedWidth(400)
        self.password_edit.returnPressed.connect(self.login_user)
        layout.addWidget(self.password_edit, alignment=Qt.AlignmentFlag.AlignCenter)

        # Message label
        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red; background: transparent")
        layout.addWidget(self.message_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Buttons
        btn_login = QPushButton("🔓 Login")
        btn_login.clicked.connect(self.login_user)
        btn_login.setStyleSheet(f"""
            QPushButton {{
                background-color: #28A745;   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 30px;
            }}
            QPushButton:hover {{
                background-color: #0D7024
            }}
        """)
        btn_login.setFixedWidth(100)
        layout.addWidget(btn_login, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_register = QPushButton("📝 Create New Account")
        btn_register.clicked.connect(lambda: self.main_window.show_page("RegisterPage"))
        btn_register.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 19px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        btn_register.setFixedWidth(100)
        layout.addWidget(btn_register, alignment=Qt.AlignmentFlag.AlignCenter)

        label = QLabel(self)
        label.setStyleSheet("background: transparent")
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
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)

        # Username
        user_label = QLabel("Username:")
        user_label.setStyleSheet("background: transparent;")
        layout.addWidget(user_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.user_edit = QLineEdit()
        self.user_edit.setFixedWidth(400)
        self.user_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        layout.addWidget(self.user_edit, alignment=Qt.AlignmentFlag.AlignCenter)

        # Email
        email_label = QLabel("Email:")
        email_label.setStyleSheet("background: transparent;")
        layout.addWidget(email_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.email_edit = QLineEdit()
        self.email_edit.setFixedWidth(400)
        self.email_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        layout.addWidget(self.email_edit, alignment=Qt.AlignmentFlag.AlignCenter)

        # Password
        pass_label = QLabel("Password:")
        pass_label.setStyleSheet("background: transparent;")
        layout.addWidget(pass_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.pass_edit = QLineEdit()
        self.pass_edit.setFixedWidth(400)
        self.pass_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_edit, alignment=Qt.AlignmentFlag.AlignCenter)

        # Confirm Password
        confirm_pass_label = QLabel("Confirm Password:")
        confirm_pass_label.setStyleSheet("background: transparent;")
        layout.addWidget(confirm_pass_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setFixedWidth(400)
        self.confirm_edit.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_edit, alignment=Qt.AlignmentFlag.AlignCenter)

        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red; background: transparent")
        layout.addWidget(self.message_label, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_register = QPushButton("✅ Register")
        btn_register.clicked.connect(self.register_user)
        btn_register.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;   
                font-family: 'Times New Roman';
                font-size: 18px;           
            }}                     
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        btn_register.setFixedWidth(250)
        layout.addWidget(btn_register, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_back = QPushButton("⬅ Back to Login")
        btn_back.clicked.connect(lambda: self.main_window.show_page("LoginPage"))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: #28A745;   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: #0D7024
            }}
        """)
        btn_back.setFixedWidth(250)
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        label = QLabel(self)
        pixmap = QPixmap('Sluggy.png')
        scaled_pixmap = pixmap.scaled(500, 300)
        label.setPixmap(scaled_pixmap)
        label.setStyleSheet("background: transparent;")
        layout.addWidget(label, alignment= Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)

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

        title_image = QLabel(self)
        title_image.setStyleSheet("background: transparent;")
        pixmap = QPixmap('logo.png').scaled(500, 325)
        title_image.setPixmap(pixmap)
        layout.addWidget(title_image, alignment= Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        btn_schedule = QPushButton("🗓️ Class Schedule")
        btn_schedule.clicked.connect(lambda: self.main_window.show_page("ScheduleInputPage"))
        btn_schedule.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};   /* Bootstrap green */
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        btn_schedule.setFixedHeight(350)
        layout.addWidget(btn_schedule, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_resources = QPushButton("📚 Resources")
        btn_resources.clicked.connect(lambda: self.main_window.show_page("ResourcesPage"))
        btn_resources.setStyleSheet(f"""
            QPushButton {{
                background-color: {BACK_BUTTON_BG};   /* Bootstrap green */
                color: black;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {BACK_HOVER_BG}
            }}
        """)
        btn_resources.setFixedWidth(350)
        layout.addWidget(btn_resources, alignment=Qt.AlignmentFlag.AlignCenter)

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
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        btn_map.setMinimumWidth(550)
        layout.addWidget(btn_map, alignment=Qt.AlignmentFlag.AlignCenter)
        
        btn_events = QPushButton("📅Slug Events")
        btn_events.clicked.connect(lambda: self.main_window.show_page("UCSCEventsPage"))
        btn_events.setStyleSheet(f"""
            QPushButton {{
                background-color: {BACK_BUTTON_BG};   /* Bootstrap green */
                color: black;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {BACK_HOVER_BG}
            }}
        """)
        btn_events.setFixedWidth(350)
        layout.addWidget(btn_events, alignment=Qt.AlignmentFlag.AlignCenter)


        btn_forum = QPushButton("🗣️Class Forums")
        btn_forum.clicked.connect(lambda: self.main_window.show_page("ForumPage"))
        btn_forum.setStyleSheet(f"""
            QPushButton {{
                background-color: {BUTTON_BG};
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        btn_forum.setMinimumWidth(550)
        layout.addWidget(btn_forum, alignment=Qt.AlignmentFlag.AlignCenter)
        


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
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)

        sub_label = QLabel("Commonly Used Links:")
        sub_label.setStyleSheet("background: transparent;")
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
                font-family: 'Times New Roman';
                font-size: 18px;
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
                color: black;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
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
                font-family: 'Times New Roman';
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        layout.addWidget(btn_mycusc)

        layout.addSpacing(20)

        sub_label2 = QLabel("Book a Study Room:")
        sub_label2.setStyleSheet("background: transparent;")
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
                font-family: 'Times New Roman';
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        hbox.addWidget(btn_mchenry)

        btn_se = QPushButton("🔬 S&&E")
        btn_se.clicked.connect(lambda: open_link("https://calendar.library.ucsc.edu/spaces?lid=16578"))
        btn_se.setStyleSheet(f"""
            QPushButton {{
                background-color: {BACK_BUTTON_BG};   /* Bootstrap green fbe35c*/
                color: black;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
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
            font-family: 'Times New Roman';
            font-size: 18px;
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
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent")
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addSpacing(10)

        # Form layout
        form_layout = QGridLayout()
        main_layout.addLayout(form_layout)

        # Class Name
        lbl_class = QLabel("Class Name:")
        lbl_class.setStyleSheet("background: transparent;")
        self.edit_class_name = QLineEdit()
        self.edit_class_name.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        form_layout.addWidget(lbl_class, 0, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.edit_class_name, 0, 1)

        # Location
        lbl_location = QLabel("Location:")
        lbl_location.setStyleSheet("background: transparent;")
        self.edit_location = QLineEdit()
        self.edit_location.setStyleSheet("QLineEdit { background-color: #FFFFFF}")
        form_layout.addWidget(lbl_location, 1, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.edit_location, 1, 1)

        # Days
        lbl_days = QLabel("Days:")
        lbl_days.setStyleSheet("background: transparent;")
        form_layout.addWidget(lbl_days, 2, 0, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        days_container = QWidget()
        days_container.setStyleSheet("background: transparent;")
        days_hbox = QHBoxLayout(days_container)
        days_container.setLayout(days_hbox)
        form_layout.addWidget(days_container, 2, 1)

        for day in ["M", "T", "W", "Th", "F"]:
            cb = QCheckBox(day)
            cb.setStyleSheet("background: transparent;")
            cb.stateChanged.connect(self.update_start_times)
            days_hbox.addWidget(cb)
            self.days_vars[day] = cb

        # Start Time
        lbl_start_time = QLabel("Start Time:")
        lbl_start_time.setStyleSheet("background: transparent;")
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
                font-family: 'Times New Roman';
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {BUTTON_HOVER}
            }}
        """)
        main_layout.addWidget(btn_add, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Warning Label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red; background: transparent")
        main_layout.addWidget(self.warning_label)

        # Class Display Area
        self.class_display_container = QWidget()
        self.class_display_container.setStyleSheet("background: transparent;")
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
                font-family: 'Times New Roman';
                font-size: 18px;
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
            if cls.get("is_event"):
                label.setStyleSheet("""
                    QLabel {
                        background-color: #FFF3CD;  /* light yellow */
                        color: #000000;
                        border: 2px dashed #FFB000;
                        border-radius: 6px;
                        padding: 6px;
                        font-size: 11px;
                    }
                    QLabel:hover {
                        background-color: #FFE8A1;
                    }
                """)
                label.setWordWrap(True)  # Enable wrapping
                label.setFixedWidth(200)  # Smaller width
                label.setMaximumHeight(80)  # Height constraint
                label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            else:
                label.setStyleSheet("""
                    QLabel {
                        background-color: #DDEEFF;
                        color: #000000;
                        border: 2px solid #999;
                        border-radius: 6px;
                        padding: 6px;
                        font-size: 11px;
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

api_key = os.getenv("GOOGLE_MAPS_API_KEY")

DAY_MAP = {
    0: "M",   # Monday
    1: "T",
    2: "W",
    3: "Th",
    4: "F",
    # ignoring Sat(5)/Sun(6)
}




class UCSCEventsPage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        set_widget_bg(self)

        self.pinned_events = []
        self.hidden_event_ids = set()
        self.remaining_events = []

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("📅 Upcoming UCSC Events")
        title.setFont(QFont("Helvetica", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: black; background: transparent")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.scroll = QScrollArea()
        self.scroll.setMinimumHeight(900)  # Or adjust height to fit more
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        self.content = QWidget()
        self.scroll_layout = QVBoxLayout(self.content)
        self.scroll.setWidget(self.content)

        
        # Back button
        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                font-family: 'Times New Roman';
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #0D7024
            }
        """)
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()

        self.refresh_events()

    def refresh_events(self):
        self.clear_event_layout()

        # Scrape new events, filter out pinned and hidden
        all_events = scrape_ucsc_events()
        self.remaining_events = [
            e for e in all_events
            if e["title"] not in self.hidden_event_ids and
            not any(p["title"] == e["title"] for p in self.pinned_events)
        ]

        # Show pinned first, then top 15 minus pinned
        events_to_show = self.pinned_events + self.get_next_events(15 - len(self.pinned_events))

        for event in events_to_show:
            self.display_event_card(event)

        self.scroll_layout.addStretch()

    def get_next_events(self, count):
        shown = []
        while self.remaining_events and len(shown) < count:
            next_event = self.remaining_events.pop(0)
            if next_event["title"] not in self.hidden_event_ids:
                shown.append(next_event)
        return shown

    def display_event_card(self, event):
        is_pinned = any(event["title"] == e["title"] for e in self.pinned_events)
        prefix = "📌🟡 " if is_pinned else "🟡 "
        title = QLabel(f"{prefix}{event['title']}")
        title.setWordWrap(True)
        date = QLabel(f"📆 {event['date']}")
        location_text = event.get("location", "").strip()
        location_display = location_text if location_text and location_text != "--" else "TBD"
        location = QLabel(f"📍 {location_display}")
        event_price = event.get("price", "").strip()
        price_display = "FREE" if not event_price or event_price == "--" else event_price
        price = QLabel(f"💵 {price_display}")
        for label in [title, date, location, price]:
            label.setStyleSheet("color: #FFFFFF; font-size: 14px;")

        # Pin button (smaller with hover)
        btn_pin = QPushButton("Pin📌")
        btn_pin.setFixedSize(26, 26)
        btn_pin.setStyleSheet("""
            QPushButton {
                background-color: #f0d954;
                color: black;
                border-radius: 3px;
                font-family: 'Times New Roman';
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #d4be3f;
            }
        """)
        btn_pin.clicked.connect(lambda _, e=event: self.pin_event(e))

        # Hide button (smaller with hover + fast remove)
        btn_hide = QPushButton("Hide❌")
        btn_hide.setFixedSize(26, 26)
        btn_hide.setStyleSheet("""
            QPushButton {
                background-color: #2d32ad;
                color: white;
                border-radius: 3px;
                font-family: 'Times New Roman';
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #1d218f;
            }
        """)
        btn_hide.clicked.connect(lambda _, e=event: self.quick_hide_event(e))

        # Add to calendar button (one-time class)
        btn_calendar = QPushButton("Add to 📆")
        btn_calendar.setFixedSize(26, 26)
        btn_calendar.setStyleSheet("""
            QPushButton {
                background-color: #f0d954;
                color: black;
                border-radius: 3px;
                font-family: 'Times New Roman';
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #d4be3f;
            }
        """)
        btn_calendar.setObjectName("calendarBtn")
        btn_calendar.clicked.connect(lambda _, e=event: self.add_event_to_schedule(e))


        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_pin)
        btn_layout.addWidget(btn_hide)
        btn_layout.addWidget(btn_calendar)
        btn_layout.setSpacing(6)

        card_layout = QVBoxLayout()
        card_layout.addWidget(title)
        card_layout.addWidget(date)
        card_layout.addWidget(location)
        card_layout.addWidget(price)
        card_layout.addLayout(btn_layout)
        card_layout.setContentsMargins(12, 12, 12, 12)

        frame = QWidget()
        frame.setLayout(card_layout)

        is_pinned = any(event["title"] == e["title"] for e in self.pinned_events)
        bg_color = "#3A4F7A" if not is_pinned else "#226622"  # Blue or Green when pinned

        frame.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 10px;
                border: 1px solid #cccccc;
            }}
        """)

# Prevent layout jumps
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed) # Tweak as needed for visual balance
        frame.setContentsMargins(8, 8, 8, 8)
        frame.setFixedHeight(260)  # Bump up slightly for padding room
        # Track event data for quick lookup
        frame.event_data = event
        self.scroll_layout.addWidget(frame)

        # Store the frame so we can remove it instantly
        frame.event_data = event
        self.scroll_layout.addWidget(frame)

    def clear_event_layout(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def pin_event(self, event):
        if any(e["title"] == event["title"] for e in self.pinned_events):
            return

        self.pinned_events.append(event)

        # Remove widget from current spot
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if hasattr(widget, 'event_data') and widget.event_data["title"] == event["title"]:
                widget.setParent(None)
                break

        # Redraw pinned event at the top
        self.clear_event_layout()
        events_to_show = self.pinned_events + self.get_next_events(15 - len(self.pinned_events))
        for ev in events_to_show:
            self.display_event_card(ev)
        self.scroll_layout.addStretch()

    def quick_hide_event(self, event):
        self.hidden_event_ids.add(event["title"])

        # Remove widget instantly from layout
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            widget = item.widget()
            if hasattr(widget, 'event_data') and widget.event_data["title"] == event["title"]:
                widget.setParent(None)
                break

        # Replace with next event, if available
        next_events = self.get_next_events(1)
        if next_events:
            self.display_event_card(next_events[0])

    def add_event_to_schedule(self, event):
        global current_user
        if not current_user:
            return

        # Attempt to parse start time from the event date string
        date_str = event["date"]
        start_time = "10:00 AM"  # default fallback
        event_day = []

        # Try extracting time info from event['date']
        if "am" in date_str.lower() or "pm" in date_str.lower():
            try:
                parts = date_str.split(',')
                if len(parts) > 2:
                    date_part = parts[1].strip()
                    time_part = parts[2].strip().split()[0]
                    start_time = time_part
                day_abbr = parts[0].strip()[:3]
                day_map = {"Mon": "M", "Tue": "T", "Wed": "W", "Thu": "Th", "Fri": "F"}
                if day_abbr in day_map:
                    event_day = [day_map[day_abbr]]
            except Exception as e:
                print(f"🧠 Couldn't parse date from: {event['date']}")

        class_info = {
            "id": str(uuid.uuid4()),
            "name": event["title"],
            "location": event["location"] or "TBD",
            "start_time": start_time,
            "days": event_day or ["M"],  # default to Monday
            "is_event": True
        }

        save_class(class_info, current_user)
        QMessageBox.information(self, "✅ Added!", f"'{event['title']}' was added to your schedule.")



class SelectClassPage(QWidget):
    def __init__(self, parent=None, main_window=None, valid_codes=None):
        super().__init__(parent)
        self.main_window = main_window
        self.valid_codes = valid_codes or []  # big list of all "CSE 107", "MATH 19A", etc.

        # Build UI
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Find Your Class Forum")
        title.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Department line edit
        dept_label = QLabel("Department (e.g. CSE):")
        layout.addWidget(dept_label)
        self.dept_input = QLineEdit()
        layout.addWidget(self.dept_input)

        # Number line edit
        num_label = QLabel("Course Number (e.g. 107):")
        layout.addWidget(num_label)
        self.num_input = QLineEdit()
        layout.addWidget(self.num_input)

        # "Go" button
        go_button = QPushButton("Go")
        go_button.setStyleSheet("""
            QPushButton{
                background-color: #161a7d;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }
            QPushButton:hover{
                background-color: #0a0c47;
            }
        """)
        go_button.clicked.connect(self.handle_go)
        layout.addWidget(go_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        # "Back to Home"
        back_button = QPushButton("⬅ Back to Home")
        back_button.setStyleSheet("""
            QPushButton{
                background-color: #28A745;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }
            QPushButton:hover{
                background-color: #0D7024;
            }
        """)
        back_button.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()

    def handle_go(self):
        dept = self.dept_input.text().strip().upper()       # e.g. "CSE"
        number = self.num_input.text().strip().upper()      # e.g. "107" or "19A"
        full_code = f"{dept} {number}"                      # "CSE 107"

        if full_code not in self.valid_codes:
            QMessageBox.warning(self, "Invalid Class", f"'{full_code}' not found in the official UCSC class list!")
            return

        # If it's valid, let's go to the ForumPage
        # We want the ForumPage to load that class's posts automatically
        # One approach: add a method on ForumPage called load_specific_class(code).
        
        self.main_window.show_page("ForumPage")
        forum_page = self.main_window.get_page("ForumPage")
        forum_page.load_specific_class(full_code)


class ForumPage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        set_widget_bg(self)

        self.current_forum_name = None
        self.forum_selector_items = []

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        title_label = QLabel("Class Forums")
        title_label.setStyleSheet("background: transparent;")
        title_label.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        forum_label = QLabel("Select a Forum:")
        forum_label.setStyleSheet("background: transparent;")
        main_layout.addWidget(forum_label)

        self.forum_selector = QComboBox()
        self.forum_selector.setStyleSheet("QComboBox { background-color: #FFFFFF }")
        self.forum_selector.currentTextChanged.connect(self.on_forum_changed)
        main_layout.addWidget(self.forum_selector)

        # Create new forum UI
        new_forum_layout = QHBoxLayout()
        self.new_forum_input = QLineEdit()
        self.new_forum_input.setPlaceholderText("Enter new forum name")
        self.new_forum_input.setStyleSheet("QLineEdit { background-color: #FFFFFF }")
        new_forum_layout.addWidget(self.new_forum_input)

        create_button = QPushButton("➕ Create Forum")
        create_button.clicked.connect(self.create_new_forum)
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #161a7d;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;   
            }
            QPushButton:hover { background-color: #0a0c47; }
        """)
        new_forum_layout.addWidget(create_button)
        main_layout.addLayout(new_forum_layout)

        # Scroll area for posts
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, stretch=1)

        msg = QLabel("Write a message:")
        msg.setStyleSheet("background: transparent;")
        main_layout.addWidget(msg)

        self.post_text = QTextEdit()
        self.post_text.setFixedHeight(100)
        self.post_text.setStyleSheet("QTextEdit { background-color: #FFFFFF }")
        main_layout.addWidget(self.post_text)

        post_btn = QPushButton("Post")
        post_btn.clicked.connect(self.handle_post)
        post_btn.setStyleSheet("""
            QPushButton {
                background-color: #161a7d;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
            }
            QPushButton:hover { background-color: #0a0c47; }
        """)
        main_layout.addWidget(post_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        back_btn = QPushButton("⬅ Back to Home")
        back_btn.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
                font-family: 'Times New Roman';
                font-size: 18px;
            }
            QPushButton:hover { background-color: #0D7024; }
        """)
        main_layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addStretch()

        # Setup polling timer for real-time updates
        self.latest_timestamp = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_for_new_posts)
        self.timer.start(5000)  # every 5 seconds

        self.load_forum_list()

    def load_forum_list(self):
        self.forum_selector.clear()
        self.forum_selector_items = forum_collection.distinct("forum_name")
        self.forum_selector.addItems(self.forum_selector_items)
        if self.forum_selector_items:
            self.current_forum_name = self.forum_selector_items[0]
            self.load_forum_posts()

    def on_forum_changed(self, forum):
        self.current_forum_name = forum
        self.load_forum_posts()

    def create_new_forum(self):
        new_name = self.new_forum_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Error", "Forum name cannot be empty.")
            return
        if new_name in self.forum_selector_items:
            QMessageBox.information(self, "Info", "Forum already exists.")
            return
        self.forum_selector.addItem(new_name)
        self.forum_selector.setCurrentText(new_name)
        self.forum_selector_items.append(new_name)
        self.new_forum_input.clear()

    def load_forum_posts(self):
        self.clear_posts()
        posts = forum_collection.find({"forum_name": self.current_forum_name}).sort("timestamp", 1)
        for doc in posts:
            self.add_post_widget(doc)
            self.latest_timestamp = doc.get("timestamp", self.latest_timestamp)
        QApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def poll_for_new_posts(self):
        if not self.current_forum_name or not self.latest_timestamp:
            return
        new_posts = forum_collection.find({
            "forum_name": self.current_forum_name,
            "timestamp": {"$gt": self.latest_timestamp}
        }).sort("timestamp", 1)
        new_found = False
        for doc in new_posts:
            self.add_post_widget(doc)
            self.latest_timestamp = doc["timestamp"]
            new_found = True
        if new_found:
            QApplication.processEvents()
            self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def handle_post(self):
        global current_user
        if not current_user:
            QMessageBox.warning(self, "Not logged in", "Please log in to post.")
            return
        msg = self.post_text.toPlainText().strip()
        if not msg:
            return
        post = {
            "forum_name": self.current_forum_name,
            "user": current_user,
            "message": msg,
            "timestamp": datetime.now()
        }
        forum_collection.insert_one(post)
        self.post_text.clear()
        self.load_forum_posts()

    def add_post_widget(self, doc):
        user = doc.get("user", "Unknown")
        msg = doc.get("message", "")
        ts = doc.get("timestamp")
        time_str = ts.strftime("%b %d %Y, %I:%M %p") if ts else ""
        label = QLabel(f"<b>{user}</b> @ {time_str}<br/><br/>{msg}")
        label.setStyleSheet("""
            QLabel {
                background-color: #DDEEFF;
                border: 1px solid #999;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        label.setWordWrap(True)
        self.scroll_layout.addWidget(label)

    def clear_posts(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)








class MapBridge(QObject):
    def __init__(self, map_page):
        super().__init__()
        self.map_page = map_page

    @pyqtSlot()
    def mapReady(self):
        self.map_page.on_map_ready()

    @pyqtSlot(result=QVariant)
    def getUserLocation(self):
        g = geocoder.ip('me')
        if g.ok:
            print("🛰️ Python location:", g.latlng)
            return {"lat": g.latlng[0], "lng": g.latlng[1]}
        else:
            print("⚠️ Could not get location")
            return {"lat": 36.9914, "lng": -122.0609}  # UCSC fallback

class MapPage(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.map_is_ready = False
        self.pending_destination = None
        self.current_travel_mode = "DRIVING"
        self.upcoming_classes = []         # Holds all upcoming classes
        self.current_class_index = 0       # Tracks which class we're currently showing


        # Main layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        #
        # 1) Top row: Travel Mode Buttons
        #
        mode_layout = QHBoxLayout()

#
# 1) Travel Mode Buttons (2x2 Grid)
#
        mode_grid = QGridLayout()

        button_style = """
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border-radius: 4px;
                padding: 4px;
                font-size: 10px;
                border: 2px solid #000000;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0a0c47;
            }
        """

        btn_drive = QPushButton("🚗 Drive")
        btn_drive.clicked.connect(lambda: self.set_travel_mode("DRIVING"))
        btn_drive.setStyleSheet(button_style)
        mode_grid.addWidget(btn_drive, 0, 0)

        btn_walk = QPushButton("🚶 Walk")
        btn_walk.clicked.connect(lambda: self.set_travel_mode("WALKING"))
        btn_walk.setStyleSheet(button_style)
        mode_grid.addWidget(btn_walk, 0, 1)

        btn_bike = QPushButton("🚴 Bike")
        btn_bike.clicked.connect(lambda: self.set_travel_mode("BICYCLING"))
        btn_bike.setStyleSheet(button_style)
        mode_grid.addWidget(btn_bike, 1, 0)

        btn_transit = QPushButton("🚌 Transit")
        btn_transit.clicked.connect(lambda: self.set_travel_mode("TRANSIT"))
        btn_transit.setStyleSheet(button_style)
        mode_grid.addWidget(btn_transit, 1, 1)

        self.layout.addLayout(mode_grid)
        self.layout.addLayout(mode_layout)

        #
        # 2) Navigation Buttons: Route to Next/Previous Class
        #
        nav_layout = QHBoxLayout()

        btn_prev = QPushButton("🕘 Previous Class")
        btn_prev.clicked.connect(self.route_to_previous_class)
        btn_prev.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        nav_layout.addWidget(btn_prev)

        btn_next = QPushButton("🔃")
        btn_next.clicked.connect(self.route_to_next_class)
        btn_next.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;   /* Amber */
                color: black;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        nav_layout.addWidget(btn_next)


        self.layout.addLayout(nav_layout)

        btn_later = QPushButton("Next Class ➡")
        btn_later.clicked.connect(self.route_to_later_class)
        btn_later.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                border: 2px solid #000000;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        nav_layout.addWidget(btn_later)

        #
        # 3) "Back to Home" Button
        #
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
        self.layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)

    def load_map(self):
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found in .env")

        with open("map.html", "r", encoding="utf-8") as f:
            html = f.read().replace("YOUR_API_KEY", api_key)

        if hasattr(self, 'browser'):
            self.layout.removeWidget(self.browser)
            self.browser.deleteLater()

        self.browser = QWebEngineView()
        self.channel = QWebChannel()
        self.bridge = MapBridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        self.browser.setHtml(html)

        self.layout.insertWidget(0, self.browser)

        self.map_is_ready = False
        self.pending_destination = None

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
        Stores all upcoming classes in order for later navigation.
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
                continue  # skip weekends

            for cls in schedule:
                if day_letter in cls["days"]:
                    # If it's today, only include classes that haven't started yet
                    if offset == 0 and cls["start_time"] <= now_str:
                        continue
                    upcoming_classes.append((offset, cls))

        if not upcoming_classes:
            print("No upcoming classes found in the next week.")
            QMessageBox.information(self, "No Classes", "You have no upcoming classes.")
            return

        # Store sorted list and start at index 0
        self.upcoming_classes = sorted(upcoming_classes, key=lambda x: (x[0], x[1]["start_time"]))
        self.current_class_index = 0

        next_class = self.upcoming_classes[self.current_class_index][1]
        print(f"Next class: {next_class['name']} at {next_class['start_time']} → {next_class['location']}")
        self.route_to(next_class["location"])

    def route_to_later_class(self):
        if not self.upcoming_classes or self.current_class_index >= len(self.upcoming_classes) - 1:
            print("No further classes to show.")
            QMessageBox.information(self, "Done", "No more classes scheduled after this.")
            return

        self.current_class_index += 1
        later_class = self.upcoming_classes[self.current_class_index][1]
        print(f"Later class: {later_class['name']} at {later_class['start_time']} → {later_class['location']}")
        self.route_to(later_class["location"])

    def route_to_previous_class(self):
        if not self.upcoming_classes or self.current_class_index <= 0:
            print("No earlier class to go back to.")
            QMessageBox.information(self, "Start", "You're already at the first upcoming class.")
            return

        self.current_class_index -= 1
        previous_class = self.upcoming_classes[self.current_class_index][1]
        print(f"Previous class: {previous_class['name']} at {previous_class['start_time']} → {previous_class['location']}")
        self.route_to(previous_class["location"])


class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)

    def featurePermissionRequested(self, securityOrigin, feature):
        if feature == QWebEnginePage.Feature.Geolocation:
            print("🔐 Granting geolocation permission.")
            self.setFeaturePermission(
                securityOrigin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )


##############################
# Main Window + StackedWidget
##############################

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SlugHub - Student Assistance")
        self.setFixedSize(850, 900)

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
            ("MapPage", MapPage),
            ("UCSCEventsPage",UCSCEventsPage),
            ("ForumPage",ForumPage),
            ("SelectClassPage", SelectClassPage)
        ]

        for name, PageClass in pages:
            if name == "SelectClassPage":
                page_instance = PageClass(main_window=self, valid_codes=VALID_UCSC_CLASSES)
            else:
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
    store_classes_in_db()
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
    window.setStyleSheet('''
        QWidget {
            background: qlineargradient(
                x1: 0, y1: 0,
                x2: 1, y2: 1,
                stop: 0 #8fc1ff,
                stop: 1 #163f73
            );           
        }
    ''')

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
