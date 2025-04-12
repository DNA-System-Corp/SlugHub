import sys
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Maps in PyQt6")
        self.setGeometry(100, 100, 800, 600)

        # Load .env
        load_dotenv()
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found in .env file!")

        # Read and patch HTML
        with open("map.html", "r", encoding="utf-8") as file:
            html = file.read().replace("YOUR_API_KEY", api_key)

        browser = QWebEngineView()
        browser.setHtml(html)
        self.setCentralWidget(browser)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
