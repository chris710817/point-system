import tkinter as tk
from ui_login import LoginFrame
from ui_leaderboard import LeaderboardFrame
from ui_staff import StaffFrame
from database import initialise_database, populate_point_categories
 

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        initialise_database()
        populate_point_categories()


        self.title("Cadet Points Tracker")
        self.geometry("1500x1000")

        self.current_user_role = "viewer"  # "staff" or "viewer"
        self.current_username = None

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames = {}

        for FrameClass in (LoginFrame, LeaderboardFrame, StaffFrame):
            frame = FrameClass(container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LeaderboardFrame")

    def show_frame(self, frame_name):
        frame = self.frames[frame_name]
        frame.tkraise()

    def login_success(self, role, username):
        if role == "staff":
            self.current_user_role = "staff"
            self.current_username = username

    def open_staff_panel(self):
        self.show_frame("StaffFrame")

    def logout(self):
        self.current_user_role = "viewer"
        self.current_username = None
        self.show_frame("LeaderboardFrame")


if __name__ == "__main__":
    app = App()
    app.mainloop()


