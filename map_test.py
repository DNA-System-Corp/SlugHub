import sys
import os
import bcrypt

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QCheckBox, QGridLayout, QVBoxLayout, QHBoxLayout
)
# ----- Import for embedding web content -----
from PyQt6.QtWebEngineWidgets import QWebEngineView

##############################
#  Global session variable
##############################
current_user = None

##############################
#  MongoDB Setup
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
#  Password Security
##############################
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

##############################
#  User Authentication
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
#  Class Schedule Helpers
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
        if not collection.find_one(data):
            collection.insert_one(data)
    except Exception as e:
        print(f"[MongoDB] Error saving class: {e}")

##############################
#  Some Constants / Styles
##############################
APP_BG_COLOR = "#E6F0FA"
TEXT_COLOR = "#1A1A1A"

def set_widget_bg(widget, color=APP_BG_COLOR):
    widget.setStyleSheet(f"background-color: {color};")

##############################
#  Pages
##############################
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

class LoginPage(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        set_widget_bg(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title_label = QLabel("Welcome to SlugHub")
        title_label.setFont(QFont("Helvetica", 20, QFont.Weight.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(20)

        layout.addWidget(QLabel("Username:"))
        self.username_edit = QLineEdit()
        layout.addWidget(self.username_edit)

        layout.addWidget(QLabel("Password:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit)

        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red;")
        layout.addWidget(self.message_label)

        btn_login = QPushButton("🔓 Login")
        btn_login.clicked.connect(self.login_user)
        layout.addWidget(btn_login)

        btn_create = QPushButton("📝 Create New Account")
        btn_create.clicked.connect(lambda: self.main_window.show_page("RegisterPage"))
        layout.addWidget(btn_create)

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
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        set_widget_bg(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title_label = QLabel("Create Account")
        title_label.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)

        layout.addWidget(QLabel("Username:"))
        self.user_edit = QLineEdit()
        layout.addWidget(self.user_edit)

        layout.addWidget(QLabel("Email:"))
        self.email_edit = QLineEdit()
        layout.addWidget(self.email_edit)

        layout.addWidget(QLabel("Password:"))
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_edit)

        layout.addWidget(QLabel("Confirm Password:"))
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_edit)

        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red;")
        layout.addWidget(self.message_label)

        btn_reg = QPushButton("✅ Register")
        btn_reg.clicked.connect(self.register_user)
        layout.addWidget(btn_reg)

        btn_back = QPushButton("⬅ Back to Login")
        btn_back.clicked.connect(lambda: self.main_window.show_page("LoginPage"))
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
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        set_widget_bg(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title_label = QLabel("Welcome to SlugHub")
        title_label.setFont(QFont("Helvetica", 22, QFont.Weight.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(20)

        btn_schedule = QPushButton("🗓️ Enter Class Schedule")
        btn_schedule.clicked.connect(lambda: self.main_window.show_page("ScheduleInputPage"))
        layout.addWidget(btn_schedule)

        btn_resources = QPushButton("📚 Resources")
        btn_resources.clicked.connect(lambda: self.main_window.show_page("ResourcesPage"))
        layout.addWidget(btn_resources)

        # BusPlannerPage is where we embed Google Maps
        btn_bus = QPushButton("🚌 Bus Route Planner")
        btn_bus.clicked.connect(lambda: self.main_window.show_page("BusPlannerPage"))
        layout.addWidget(btn_bus)

        btn_logout = QPushButton("🔐 Logout")
        btn_logout.clicked.connect(self.logout)
        layout.addWidget(btn_logout)

        layout.addStretch()

    def logout(self):
        global current_user
        current_user = None
        self.main_window.show_page("LoginPage")


class ResourcesPage(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        set_widget_bg(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title_label = QLabel("Resources")
        title_label.setFont(QFont("Helvetica", 20, QFont.Weight.Bold))
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)

        sub_label = QLabel("Commonly Used Links:")
        sub_label.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        layout.addWidget(sub_label)

        def open_link(url):
            QDesktopServices.openUrl(QUrl(url))

        btn_textbook = QPushButton("📘 Textbook Website")
        btn_textbook.clicked.connect(lambda: open_link("https://ucsc.textbookx.com/"))
        layout.addWidget(btn_textbook)

        btn_canvas = QPushButton("🎓 Canvas Portal")
        btn_canvas.clicked.connect(lambda: open_link("https://canvas.ucsc.edu"))
        layout.addWidget(btn_canvas)

        btn_mycusc = QPushButton("🧾 MyUCSC Portal")
        btn_mycusc.clicked.connect(lambda: open_link("https://my.ucsc.edu/psc/csprd/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL?"))
        layout.addWidget(btn_mycusc)

        layout.addSpacing(20)

        sub_label2 = QLabel("Book a Study Room:")
        sub_label2.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        layout.addWidget(sub_label2)

        link_layout = QHBoxLayout()
        layout.addLayout(link_layout)

        btn_mchenry = QPushButton("📚 McHenry")
        btn_mchenry.clicked.connect(lambda: open_link("https://calendar.library.ucsc.edu/spaces?lid=16577"))
        link_layout.addWidget(btn_mchenry)

        btn_se = QPushButton("🔬 S&E")
        btn_se.clicked.connect(lambda: open_link("https://calendar.library.ucsc.edu/spaces?lid=16578"))
        link_layout.addWidget(btn_se)

        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch()


class ScheduleInputPage(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        set_widget_bg(self)

        self.schedule_data = []
        self.days_vars = {}

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        title_label = QLabel("Class Schedule Input")
        title_label.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addSpacing(10)

        form_layout = QGridLayout()
        main_layout.addLayout(form_layout)

        lbl_class = QLabel("Class Name:")
        self.edit_class_name = QLineEdit()
        form_layout.addWidget(lbl_class, 0, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.edit_class_name, 0, 1)

        lbl_location = QLabel("Location:")
        self.edit_location = QLineEdit()
        form_layout.addWidget(lbl_location, 1, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.edit_location, 1, 1)

        lbl_days = QLabel("Days:")
        form_layout.addWidget(lbl_days, 2, 0, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        days_container = QWidget()
        days_hbox = QHBoxLayout(days_container)
        for day in ["M", "T", "W", "Th", "F"]:
            cb = QCheckBox(day)
            cb.stateChanged.connect(self.update_start_times)
            days_hbox.addWidget(cb)
            self.days_vars[day] = cb
        form_layout.addWidget(days_container, 2, 1)

        lbl_start_time = QLabel("Start Time:")
        self.combo_start_time = QComboBox()
        form_layout.addWidget(lbl_start_time, 3, 0, alignment=Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.combo_start_time, 3, 1)

        btn_add = QPushButton("➕ Add Class")
        btn_add.clicked.connect(self.add_class)
        main_layout.addWidget(btn_add, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.class_display = QTextEdit()
        self.class_display.setReadOnly(True)
        main_layout.addWidget(self.class_display)

        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        main_layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addStretch()

    def update_start_times(self):
        selected_days = [d for d, cb in self.days_vars.items() if cb.isChecked()]
        mwf = ["8:00 AM", "9:20 AM", "10:40 AM", "12:00 PM", "1:20 PM", "2:40 PM", "4:00 PM"]
        evening = ["5:20 PM", "7:10 PM"]
        tuth = ["8:00 AM", "9:50 AM", "11:40 AM", "1:30 PM", "3:20 PM"]
        valid = []

        if all(d in selected_days for d in ["M", "W", "F"]):
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
        global current_user
        if current_user:
            self.schedule_data = get_all_classes(current_user)
        else:
            self.schedule_data = []
        self.display_schedule()


class BusPlannerPage(QWidget):
    """
    Demonstrates embedding Google Maps in a QWebEngineView.
    We'll replace "YOUR_API_KEY" in the local map.html with
    the real key from .env, then load it.
    """
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        set_widget_bg(self)

        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        if not self.api_key:
            print("Warning: GOOGLE_MAPS_API_KEY not set. Map may fail to load.")

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        title_label = QLabel("Bus Route Planner")
        title_label.setFont(QFont("Helvetica", 18, QFont.Weight.Bold))
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addSpacing(10)

        # Top inputs for origin/destination
        input_layout = QHBoxLayout()
        self.edit_origin = QLineEdit()
        self.edit_origin.setPlaceholderText("Enter origin...")
        self.edit_destination = QLineEdit()
        self.edit_destination.setPlaceholderText("Enter destination...")
        btn_route = QPushButton("Calculate Route")
        btn_route.clicked.connect(self.calculate_route)

        input_layout.addWidget(self.edit_origin)
        input_layout.addWidget(self.edit_destination)
        input_layout.addWidget(btn_route)

        main_layout.addLayout(input_layout)

        # The QWebEngineView
        self.webview = QWebEngineView()
        main_layout.addWidget(self.webview, stretch=1)

        btn_back = QPushButton("⬅ Back to Home")
        btn_back.clicked.connect(lambda: self.main_window.show_page("HomePage"))
        main_layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addStretch()

        # Load the local map.html with the real API key
        self.load_map_html()

    def load_map_html(self):
        """Reads map.html, replaces placeholder with real key, loads it into the QWebEngineView."""
        # Make sure map.html is in the same folder as this script
        html_path = os.path.join(os.path.dirname(__file__), "map.html")
        if not os.path.exists(html_path):
            print(f"map.html not found at {html_path}")
            return

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Replace placeholder with real key
        html_content = html_content.replace("YOUR_API_KEY", self.api_key)

        # Load the HTML directly (use setHtml) 
        # We can provide a base URL so relative links work if needed:
        self.webview.setHtml(html_content, baseUrl=QUrl.fromLocalFile(html_path))

    def calculate_route(self):
        """Calls the JS function 'calculateRoute(origin, destination)' inside map.html."""
        origin = self.edit_origin.text().strip()
        destination = self.edit_destination.text().strip()
        if not origin or not destination:
            print("Origin or destination is missing.")
            return

        # Use runJavaScript to call the JS function
        script = f"calculateRoute('{origin}', '{destination}');"
        self.webview.page().runJavaScript(script)


##############################
#  Main Window + StackedWidget
##############################

from PyQt6.QtWidgets import QMainWindow, QStackedWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SlugHub - Student Assistance")
        self.setFixedSize(500, 600)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.page_ids = {}

        pages = [
            ("LoginPage", LoginPage),
            ("RegisterPage", RegisterPage),
            ("HomePage", HomePage),
            ("ResourcesPage", ResourcesPage),
            ("ScheduleInputPage", ScheduleInputPage),
            ("BusPlannerPage", BusPlannerPage)
        ]

        # Instantiate each page & add to QStackedWidget
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
        # If it's the schedule page, refresh before showing
        if page_name == "ScheduleInputPage" and hasattr(widget, "refresh"):
            widget.refresh()
        self.stacked_widget.setCurrentIndex(idx)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
