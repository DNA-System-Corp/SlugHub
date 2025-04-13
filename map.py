import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from PyQt6.QtCore import Qt, QObject, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QGuiApplication

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --no-sandbox"
os.environ["QT_QUICK_BACKEND"] = "software"

# 📅 Mock class schedule
SCHEDULE = [
    {"name": "CSE107", "location": "Thimann Lecture Hall, Santa Cruz, CA", "start_time": "11:40 AM", "days": ["M", "W", "F"]},
    {"name": "CSE20", "location": "Engineering 2, UCSC, Santa Cruz, CA", "start_time": "1:30 PM", "days": ["T", "Th"]}
]

# Map weekday integer to UCSC format
DAY_MAP = {0: "M", 1: "T", 2: "W", 3: "Th", 4: "F"}

class Bridge(QObject):
    def __init__(self, on_ready):
        super().__init__()
        self.on_ready = on_ready

    @pyqtSlot()
    def mapReady(self):
        self.on_ready()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Standalone Smart Campus Map")
        self.setGeometry(100, 100, 1000, 600)
        self.map_is_ready = False
        self.pending_destination = None
        self.current_travel_mode = "DRIVING"

        load_dotenv()
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not set in .env")

        with open("map.html", "r", encoding="utf-8") as f:
            html = f.read().replace("YOUR_API_KEY", api_key)

        html = html.replace("</head>", "<script src='qrc:///qtwebchannel/qwebchannel.js'></script></head>")

        self.browser = QWebEngineView()
        self.browser.setHtml(html)

        self.bridge = Bridge(self.on_map_ready)
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        container = QWidget()
        container.setLayout(layout)

        # Vertical travel mode buttons
        mode_layout = QVBoxLayout()
        for mode in ["DRIVING", "WALKING", "BICYCLING", "TRANSIT"]:
            btn = QPushButton(mode)
            btn.clicked.connect(lambda _, m=mode: self.set_travel_mode(m))
            mode_layout.addWidget(btn)

        layout.addLayout(mode_layout, 1)
        layout.addWidget(self.browser, 4)
        self.setCentralWidget(container)

    def on_map_ready(self):
        self.map_is_ready = True
        self.route_to_next_class()

    def set_travel_mode(self, mode):
        self.current_travel_mode = mode
        self.browser.page().runJavaScript(f'setTravelMode("{mode}");')
        if self.map_is_ready and self.pending_destination:
            self.route_to(self.pending_destination)

    def route_to_next_class(self):
        today = datetime.today()
        now = today.strftime("%I:%M %p")
        weekday_index = today.weekday()  # 0 = Monday ... 6 = Sunday

        upcoming_classes = []

        for offset in range(7):  # look up to a week ahead
            day_to_check = (weekday_index + offset) % 7
            day_letter = DAY_MAP.get(day_to_check)

            if not day_letter:
                continue

            for cls in SCHEDULE:
                if day_letter in cls["days"]:
                    # If it's today, only include classes later than now
                    if offset == 0 and cls["start_time"] <= now:
                        continue
                    upcoming_classes.append((offset, cls))

        if upcoming_classes:
            # sort by earliest day offset, then start_time
            next_class = sorted(upcoming_classes, key=lambda x: (x[0], x[1]["start_time"]))[0][1]
            self.pending_destination = next_class["location"]
            print(f"📍 Next class: {next_class['name']} at {next_class['start_time']} → {next_class['location']}")
            self.route_to(next_class["location"])
        else:
            print("No upcoming classes found.")


    def route_to(self, destination):
        self.browser.page().runJavaScript(f'createRoute("{destination}");')

if __name__ == "__main__":
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
