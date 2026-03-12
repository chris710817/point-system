import tkinter as tk
from tkinter import messagebox
from database import authenticate_user, create_user

class LoginFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Create a default staff account if none exists
        create_user("staff", "admin", "staff")

        tk.Label(self, text="Staff Login", font=("Arial", 22)).pack(pady=30)

        tk.Label(self, text="Username",font=("Arial", 16)).pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()

        tk.Label(self, text="Password",font=("Arial", 16)).pack()
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()

        tk.Button(self, text="Login", width=15, command=self.login).pack(pady=20)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        role = authenticate_user(username, password)
        if role == "staff":
            self.controller.login_success("staff", username)
            self.controller.show_frame("LeaderboardFrame")
        else:
            messagebox.showerror("Error", "Invalid staff login")