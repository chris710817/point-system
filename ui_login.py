import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from database import authenticate_user, create_user

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class LoginFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._images = []  # prevent garbage collection of PhotoImage objects

        create_user("staff", "admin", "staff")

        # Three-column layout: logo | form | logo
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        left = tk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=30, pady=40)
        self._add_logo(left, "rafac_logo.png", height=280)

        centre = tk.Frame(self)
        centre.grid(row=0, column=1, sticky="nsew", padx=20, pady=40)
        self._build_form(centre, controller)

        right = tk.Frame(self)
        right.grid(row=0, column=2, sticky="nsew", padx=30, pady=40)
        self._add_logo(right, "hutton_atc_logo.png", height=280)

    def _add_logo(self, parent, filename, height=280):
        path = os.path.join(BASE_DIR, filename)
        try:
            img = Image.open(path)
            ratio = height / img.height
            img = img.resize((int(img.width * ratio), height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._images.append(photo)
            tk.Label(parent, image=photo).pack(expand=True)
        except Exception:
            pass

    def _build_form(self, parent, controller):
        tk.Label(parent, text="2476 Hutton Squadron", font=("Arial", 16, "italic"), fg="#1a1a2e").pack(pady=(40, 2))
        tk.Label(parent, text="Staff Login", font=("Arial", 26, "bold"), fg="#1a1a2e").pack(pady=(0, 30))

        tk.Label(parent, text="Username", font=("Arial", 13, "bold")).pack()
        self.username_entry = tk.Entry(parent, font=("Arial", 13), width=22)
        self.username_entry.pack(pady=(2, 10))

        tk.Label(parent, text="Password", font=("Arial", 13, "bold")).pack()
        self.password_entry = tk.Entry(parent, font=("Arial", 13), width=22, show="*")
        self.password_entry.pack(pady=(2, 20))
        self.password_entry.bind("<Return>", lambda _: self.login())

        tk.Button(parent, text="Login", font=("Arial", 12, "bold"),
                  width=16, command=self.login).pack(pady=(0, 8))
        tk.Button(parent, text="← Back", font=("Arial", 10),
                  command=lambda: controller.show_frame("LeaderboardFrame")).pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        role = authenticate_user(username, password)
        if role == "staff":
            self.controller.login_success("staff", username)
            self.controller.show_frame("LeaderboardFrame")
        else:
            messagebox.showerror("Error", "Invalid staff login")
