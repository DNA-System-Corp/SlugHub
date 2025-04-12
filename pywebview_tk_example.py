import threading
import tkinter as tk
import webview

def open_map_window():
    """
    This function runs in a separate thread, creating
    and starting PyWebView with Google Maps in a new window.
    """
    # Option A: Just load Google Maps from the web:
    webview.create_window("Google Maps", "https://www.google.com/maps")
    webview.start()

    # Option B: If you have a local HTML file with a hardcoded API key,
    # you can do something like:
    # webview.create_window("Google Maps", "file:///path/to/your_map.html")
    # webview.start()

def main():
    # Your main Tkinter window
    root = tk.Tk()
    root.title("Main Tkinter App")
    root.geometry("300x150")

    # A button to open the PyWebView map window
    open_btn = tk.Button(root, text="Open Google Maps", 
                         command=lambda: threading.Thread(target=open_map_window).start())
    open_btn.pack(padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
