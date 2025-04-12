import sys
import os
from dotenv import load_dotenv
from PyQt6.QtCore import QTimer, QObject, pyqtSlot, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QGuiApplication

class Bridge(QObject):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @pyqtSlot()
    def mapReady(self):
        print("✅ Map is ready — notifying Python")
        self.callback()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Maps in PyQt6")
        self.setGeometry(100, 100, 800, 600)

        self.map_is_ready = False
        self.pending_route = None  # holds (origin, destination, mode)

        load_dotenv()
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found in .env file!")

        with open("map.html", "r", encoding="utf-8") as file:
            html = file.read().replace("YOUR_API_KEY", api_key)

        # Inject QWebChannel script
        html = html.replace("</head>", """
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>""")

        self.browser = QWebEngineView()
        self.browser.setHtml(html)
        self.setCentralWidget(self.browser)

        # Setup JS↔Python bridge
        self.bridge = Bridge(self.on_map_ready)
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)

    def on_map_ready(self):
        print("🟢 Map is fully initialized.")
        self.map_is_ready = True

        if self.pending_route:
            origin, destination, mode = self.pending_route
            print("↪ Executing pending route...")
            self.update_route(origin, destination, mode)
            self.pending_route = None

    def create_route(self, origin: str, destination: str):
        js_code = f'createRoute("{origin}", "{destination}");'
        self.browser.page().runJavaScript(js_code)

    def set_travel_mode(self, mode: str):
        mode = mode.upper()
        if mode not in ["DRIVING", "WALKING", "BICYCLING", "TRANSIT"]:
            print(f"Invalid travel mode: {mode}")
            return
        js_code = f'setTravelMode("{mode}");'
        self.browser.page().runJavaScript(js_code)

    def update_route(self, origin: str, destination: str, mode: str):
        if not self.map_is_ready:
            print("⏳ Map not ready — storing route request.")
            self.pending_route = (origin, destination, mode)
            return

        print(f"🚗 Updating route: {mode} from {origin} → {destination}")
        self.set_travel_mode(mode)
        self.create_route(origin, destination)

if __name__ == "__main__":
    # Fix high DPI warning before QApplication creation
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
