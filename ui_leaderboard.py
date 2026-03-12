import tkinter as tk
from database import get_all_cadets, get_leaderboard, get_flight_totals
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class LeaderboardFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # ===================== MAIN TWO-COLUMN LAYOUT =====================
        self.main_container = tk.Frame(self)
        self.main_container.pack(fill="both", expand=True)

        # Left side (Leaderboard content)
        self.left_frame = tk.Frame(self.main_container)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)

        # Right side (Pie chart)
        self.right_frame = tk.Frame(self.main_container)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)

        self.main_container.columnconfigure(0, weight=3)
        self.main_container.columnconfigure(1, weight=2)

        # ===================== LEFT SIDE CONTENT =====================

        tk.Label(self.left_frame, text="Leaderboard", font=("Arial", 24)).pack(pady=10)

        # ---------------- Flight Totals ----------------
        tk.Label(self.left_frame, text="Flight Totals", font=("Arial", 18)).pack()
        self.flight_listbox = tk.Listbox(self.left_frame, width=40, height=5)
        self.flight_listbox.pack(pady=5)

        # ---------------- Flight Filter ----------------
        tk.Label(self.left_frame, text="Filter by Flight").pack()

        self.flight_filter = tk.StringVar(value="All Flights")

        tk.OptionMenu(
            self.left_frame,
            self.flight_filter,
            "All Flights",
            "A Flight",
            "B Flight",
            "C Flight",
            "D Flight",
            command=lambda _: self.refresh()
        ).pack()

        # ---------------- Individual Leaderboard ----------------
        tk.Label(self.left_frame, text="Individual Cadets", font=("Arial", 18)).pack()
        self.cadet_listbox = tk.Listbox(self.left_frame, width=55, height=25)
        self.cadet_listbox.pack(pady=5)

        # ---------------- Buttons ----------------
        self.login_button = tk.Button(
            self.left_frame,
            text="Staff Login",
            command=lambda: controller.show_frame("LoginFrame")
        )

        self.staff_button = tk.Button(
            self.left_frame,
            text="Staff Panel",
            command=controller.open_staff_panel
        )

        tk.Button(self.left_frame, text="Logout", command=controller.logout).pack(pady=5)

        # ===================== RIGHT SIDE (PIE CHART) =====================

        tk.Label(
            self.right_frame,
            text="Flight Points Distribution",
            font=("Arial", 18)
        ).pack(pady=10)

        self.chart_frame = tk.Frame(self.right_frame)
        self.chart_frame.pack(fill="both")

    # ===================== Frame Control =====================
    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        self.refresh()

    # ===================== Refresh Leaderboard =====================
    def refresh(self):
        self.flight_listbox.delete(0, tk.END)
        self.cadet_listbox.delete(0, tk.END)

        # ---- Flight totals via relational JOIN in get_flight_totals ----
        for flight, total in get_flight_totals():
            self.flight_listbox.insert(tk.END, f"{flight} – {total} pts")

        # ---- Individual leaderboard (filtered) ----
        selected_flight = self.flight_filter.get()
        leaderboard = get_leaderboard(selected_flight)

        if not leaderboard:
            self.cadet_listbox.insert(tk.END, "No cadets to display")
        else:
            for index, (name, flight, points) in enumerate(leaderboard, start=1):

                if index == 1:
                    prefix = "🥇 "
                elif index == 2:
                    prefix = "🥈 "
                elif index == 3:
                    prefix = "🥉 "
                else:
                    prefix = f"{index}. "

                line = f"{prefix}{name} ({flight}) – {points} pts"
                self.cadet_listbox.insert(tk.END, line)

        # ---- Permission-based buttons ----
        if self.controller.current_user_role == "staff":
            self.staff_button.pack(pady=5)
            self.login_button.pack_forget()
        else:
            self.staff_button.pack_forget()
            self.login_button.pack(pady=5)

        self.draw_pie_chart()

    # ===================== Pie Chart =====================
    def draw_pie_chart(self):
        data = get_flight_totals()

        # Clear old chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        if not data:
            return

        flights = [row[0] for row in data]
        totals = [row[1] for row in data]

        fig, ax = plt.subplots(figsize=(5, 5))
        ax.pie(
            totals,
            labels=flights,
            autopct='%1.1f%%'
        )
        ax.set_title("Points per Flight")

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)