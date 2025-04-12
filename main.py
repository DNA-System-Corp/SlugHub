
# === SlugHub Full App with User Authentication ===

import tkinter as tk
from tkinter import ttk
import webbrowser
import bcrypt
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

# === GLOBAL SESSION VARIABLE ===
current_user = None

# === MongoDB Setup ===
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

# === Password Security ===
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

# === User Authentication ===
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

# === Class Schedule Helpers ===
def get_all_classes(user):
    try:
        return list(collection.find({"user": user}, {"_id": 0}))
    except Exception as e:
        print(f"[MongoDB] Error loading classes: {e}")
        return []

def save_class(data, user):
    try:
        data["user"] = user
        collection.insert_one(data)
    except Exception as e:
        print(f"[MongoDB] Error saving class: {e}")

# === UI Constants ===
APP_BG_COLOR = "#E6F0FA"
TEXT_COLOR = "#1A1A1A"
BUTTON_BG = "#0077CC"
BUTTON_HOVER = "#3399FF"
BACK_BUTTON_BG = "#CCE5FF"
BACK_BUTTON_TEXT = "#003366"
BUTTON_TEXT = "white"

def styled_button(master, text, command):
    return tk.Button(master, text=text, command=command, width=28, height=2,
                     bg=BUTTON_BG, fg=BUTTON_TEXT, activebackground=BUTTON_HOVER,
                     font=("Helvetica", 11, "bold"), relief="raised", bd=3)

def back_button(master, text, command):
    return tk.Button(master, text=text, command=command, width=20, height=1,
                     bg=BACK_BUTTON_BG, fg=BACK_BUTTON_TEXT,
                     font=("Helvetica", 10, "bold"), relief="groove", bd=2)

# === Main App ===
class SlugHub(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SlugHub - Student Assistance")
        self.geometry("500x600")
        self.configure(bg=APP_BG_COLOR)
        self.resizable(False, False)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.TFrame", background=APP_BG_COLOR)
        style.configure("TLabel", background=APP_BG_COLOR)

        container = ttk.Frame(self, style="Custom.TFrame")
        container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (LoginPage, RegisterPage, HomePage, ResourcesPage, ScheduleInputPage, BusPlannerPage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(LoginPage)

    def show_frame(self, page_class):
        self.frames[page_class].tkraise()

# === Pages ===
class LoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="Custom.TFrame")
        self.controller = controller

        tk.Label(self, text="Welcome to SlugHub", font=("Helvetica", 20, "bold"),
                 fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=30)

        self.username_entry = self._entry("Username:")
        self.password_entry = self._entry("Password:", show="*")

        self.message = tk.Label(self, text="", bg=APP_BG_COLOR, fg="red")
        self.message.pack()

        styled_button(self, "🔓 Login", self.login_user).pack(pady=10)
        back_button(self, "📝 Create New Account", lambda: controller.show_frame(RegisterPage)).pack(pady=5)

    def _entry(self, label, show=""):
        tk.Label(self, text=label, bg=APP_BG_COLOR).pack()
        entry = tk.Entry(self, width=30, show=show)
        entry.pack(pady=4)
        return entry

    def login_user(self):
        global current_user
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        success, user = authenticate_user(username, password)
        if success:
            current_user = user["username"]
            self.controller.show_frame(HomePage)
        else:
            self.message.config(text=user)

class RegisterPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="Custom.TFrame")
        self.controller = controller

        tk.Label(self, text="Create Account", font=("Helvetica", 18, "bold"),
                 fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=20)

        self.entries = {}
        for field in ["Username", "Email", "Password", "Confirm Password"]:
            tk.Label(self, text=field + ":", bg=APP_BG_COLOR).pack()
            show = "*" if "Password" in field else ""
            entry = tk.Entry(self, width=30, show=show)
            entry.pack(pady=4)
            self.entries[field.lower().replace(" ", "_")] = entry

        self.message = tk.Label(self, text="", bg=APP_BG_COLOR, fg="red")
        self.message.pack()

        styled_button(self, "✅ Register", self.register_user).pack(pady=10)
        back_button(self, "⬅ Back to Login", lambda: controller.show_frame(LoginPage)).pack(pady=5)

    def register_user(self):
        u = self.entries["username"].get().strip()
        e = self.entries["email"].get().strip()
        p = self.entries["password"].get()
        cp = self.entries["confirm_password"].get()

        if not u or not e or not p or not cp:
            self.message.config(text="⚠️ Please fill out all fields.")
            return
        if p != cp:
            self.message.config(text="⚠️ Passwords do not match.")
            return

        success, msg = create_user(u, e, p)
        self.message.config(text=msg, fg="green" if success else "red")
        if success:
            self.controller.show_frame(LoginPage)


class RegisterPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="Custom.TFrame")
        self.controller = controller

        tk.Label(self, text="Create Account", font=("Helvetica", 18, "bold"), fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=20)

        self.entries = {}
        fields = ["Username", "Email", "Password", "Confirm Password"]
        for i, label in enumerate(fields):
            tk.Label(self, text=label + ":", bg=APP_BG_COLOR).pack()
            show = "*" if "Password" in label else ""
            entry = tk.Entry(self, show=show, width=30)
            entry.pack(pady=3)
            self.entries[label.lower().replace(" ", "_")] = entry

        self.message = tk.Label(self, text="", bg=APP_BG_COLOR, fg="red")
        self.message.pack()

        styled_button(self, "✅ Register", self.register_user).pack(pady=10)
        back_button(self, "⬅ Back to Login", lambda: controller.show_frame(LoginPage)).pack(pady=5)

    def register_user(self):
        username = self.entries["username"].get().strip()
        email = self.entries["email"].get().strip()
        password = self.entries["password"].get()
        confirm = self.entries["confirm_password"].get()

        if not username or not email or not password or not confirm:
            self.message.config(text="⚠️ Please fill out all fields.")
            return
        if password != confirm:
            self.message.config(text="⚠️ Passwords do not match.")
            return

        success, msg = create_user(username, email, password)
        self.message.config(text=msg, fg="green" if success else "red")
        if success:
            self.controller.show_frame(LoginPage)

class LoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="Custom.TFrame")
        self.controller = controller

        tk.Label(self, text="Welcome to SlugHub", font=("Helvetica", 20, "bold"), fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=30)

        self.username_entry = self._labeled_entry("Username:")
        self.password_entry = self._labeled_entry("Password:", show="*")

        self.message = tk.Label(self, text="", bg=APP_BG_COLOR, fg="red")
        self.message.pack()

        styled_button(self, "🔓 Login", self.login_user).pack(pady=10)
        back_button(self, "📝 Create New Account", lambda: controller.show_frame(RegisterPage)).pack(pady=5)

    def _labeled_entry(self, label, show=""):
        tk.Label(self, text=label, bg=APP_BG_COLOR).pack()
        entry = tk.Entry(self, width=30, show=show)
        entry.pack(pady=4)
        return entry

    def login_user(self):
        global current_user
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        success, result = authenticate_user(username, password)
        if success:
            current_user = result["username"]
            self.controller.show_frame(HomePage)
        else:
            self.message.config(text=result)


class HomePage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="Custom.TFrame")

        tk.Label(self, text="Welcome to SlugHub", font=("Helvetica", 22, "bold"),
                 fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=40)

        styled_button(self, "📚 Resources", lambda: controller.show_frame(ResourcesPage)).pack(pady=12)
        styled_button(self, "🗓️ Enter Class Schedule", lambda: controller.show_frame(ScheduleInputPage)).pack(pady=12)
        styled_button(self, "🚌 Bus Route Planner", lambda: controller.show_frame(BusPlannerPage)).pack(pady=12)

class ResourcesPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="Custom.TFrame")

        tk.Label(self, text="Resources", font=("Helvetica", 20, "bold"),
                 fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=(30, 20))

        tk.Label(self, text="Commonly Used Links:", font=("Helvetica", 14, "bold"),
                 fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=(10, 10))

        styled_button(self, "📘 Textbook Website",
                      lambda: webbrowser.open("https://ucsc.textbookx.com/")).pack(pady=8)

        styled_button(self, "🎓 Canvas Portal",
                      lambda: webbrowser.open("https://canvas.ucsc.edu")).pack(pady=8)

        styled_button(self, "🧾 MyUCSC Portal",
                      lambda: webbrowser.open("https://my.ucsc.edu/psc/csprd/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL?")).pack(pady=8)

        tk.Label(self, text="Book a Study Room:", font=("Helvetica", 14, "bold"),
                 fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=(30, 5))

        button_frame = tk.Frame(self, bg=APP_BG_COLOR)
        button_frame.pack(pady=5)

        tk.Button(button_frame, text="📚 McHenry", command=lambda: self.open_library("McHenry"),
                  bg=BUTTON_BG, fg=BUTTON_TEXT, font=("Helvetica", 10, "bold"),
                  relief="raised", bd=3, width=14, height=2,
                  activebackground=BUTTON_HOVER).pack(side="left", padx=10)

        tk.Button(button_frame, text="🔬 S&E", command=lambda: self.open_library("S&E"),
                  bg=BUTTON_BG, fg=BUTTON_TEXT, font=("Helvetica", 10, "bold"),
                  relief="raised", bd=3, width=14, height=2,
                  activebackground=BUTTON_HOVER).pack(side="left", padx=10)

        back_button(self, "⬅ Back to Home", lambda: controller.show_frame(HomePage)).pack(pady=30)

        self.library_urls = {
            "McHenry": "https://calendar.library.ucsc.edu/spaces?lid=16577",
            "S&E": "https://calendar.library.ucsc.edu/spaces?lid=16578"
        }

    def open_library(self, library_name):
        url = self.library_urls.get(library_name)
        if url:
            webbrowser.open(url)

class ScheduleInputPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="Custom.TFrame")

        tk.Label(self, text="Class Schedule Input", font=("Helvetica", 18, "bold"),
                 fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=20)

        form_frame = tk.Frame(self, bg=APP_BG_COLOR)
        form_frame.pack(pady=10)

        tk.Label(form_frame, text="Class Name:", font=("Helvetica", 11), bg=APP_BG_COLOR).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.class_name_entry = tk.Entry(form_frame, width=25)
        self.class_name_entry.grid(row=0, column=1, pady=5)

        tk.Label(form_frame, text="Location:", font=("Helvetica", 11), bg=APP_BG_COLOR).grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.location_entry = tk.Entry(form_frame, width=25)
        self.location_entry.grid(row=1, column=1, pady=5)

        tk.Label(form_frame, text="Days:", font=("Helvetica", 11), bg=APP_BG_COLOR).grid(row=2, column=0, sticky="ne", padx=5, pady=5)
        days_frame = tk.Frame(form_frame, bg=APP_BG_COLOR)
        days_frame.grid(row=2, column=1, sticky="w")
        self.days_vars = {}
        for i, day in enumerate(["M", "T", "W", "Th", "F"]):
            var = tk.BooleanVar()
            self.days_vars[day] = var
            tk.Checkbutton(days_frame, text=day, variable=var, bg=APP_BG_COLOR,
                           command=self.update_start_times).grid(row=0, column=i, padx=5)

        tk.Label(form_frame, text="Start Time:", font=("Helvetica", 11), bg=APP_BG_COLOR).grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.start_time_var = tk.StringVar()
        self.start_time_dropdown = ttk.Combobox(form_frame, textvariable=self.start_time_var, width=22, state="readonly")
        self.start_time_dropdown.grid(row=3, column=1, pady=5)

        self.schedule_data = []
        self.update_start_times()

        styled_button(self, "➕ Add Class", self.add_class).pack(pady=10)
        self.class_display = tk.Text(self, height=8, width=55, bg="white", fg="black")
        self.class_display.pack(pady=10)
        global current_user
        self.schedule_data = get_all_classes(current_user)
        self.display_schedule()

        back_button(self, "⬅ Back to Home", lambda: controller.show_frame(HomePage)).pack(pady=20)

    def update_start_times(self):
        selected_days = [d for d, var in self.days_vars.items() if var.get()]
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

        self.start_time_dropdown['values'] = valid or ["(select days)"]
        self.start_time_dropdown.set(valid[0] if valid else "(select days)")

    def add_class(self):
        global current_user
        name = self.class_name_entry.get().strip()
        location = self.location_entry.get().strip()
        start_time = self.start_time_var.get()
        days = [d for d, var in self.days_vars.items() if var.get()]

        if not name or not location or not days or "(select days)" in start_time:
            self.class_display.insert(tk.END, "⚠️ Please complete all fields correctly.\n")
            return

        class_info = {
            "name": name,
            "location": location,
            "start_time": start_time,
            "days": days
        }

        self.schedule_data.append(class_info)
        save_class(class_info, current_user)
        self.display_schedule()

        self.class_name_entry.delete(0, tk.END)
        self.location_entry.delete(0, tk.END)
        for var in self.days_vars.values():
            var.set(False)
        self.update_start_times()

    def display_schedule(self):
        self.class_display.delete("1.0", tk.END)
        for cls in self.schedule_data:
            line = f"{cls['name']} @ {cls['location']} on {', '.join(cls['days'])} at {cls['start_time']}\n"
            self.class_display.insert(tk.END, line)

class BusPlannerPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="Custom.TFrame")
        tk.Label(self, text="Bus Route Planner", font=("Helvetica", 18, "bold"),
                 fg=TEXT_COLOR, bg=APP_BG_COLOR).pack(pady=40)
        back_button(self, "⬅ Back to Home", lambda: controller.show_frame(HomePage)).pack(pady=30)

# ─── Run ───
if __name__ == "__main__":
    app = SlugHub()
    app.mainloop()
