import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from database import get_leaderboard, get_flight_totals, get_most_popular_events, get_cadets_for_event


class LeaderboardFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Track the currently selected event bar
        self._selected_event = None
        self._event_data = []

        # ===================== NOTEBOOK (TABS) =====================
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.leaderboard_tab = tk.Frame(self.notebook)
        self.notebook.add(self.leaderboard_tab, text="  🏆  Leaderboard  ")

        self.events_tab = tk.Frame(self.notebook)
        self.notebook.add(self.events_tab, text="  📊  Event Popularity  ")

        # Refresh events tab when it becomes active
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_leaderboard_tab()
        self._build_events_tab()

    # ==============================================================================
    # LEADERBOARD TAB
    # ==============================================================================

    def _build_leaderboard_tab(self):
        tab = self.leaderboard_tab

        main = tk.Frame(tab)
        main.pack(fill="both", expand=True)

        left  = tk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        right = tk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)

        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)

        # Flight totals
        tk.Label(left, text="Leaderboard",   font=("Arial", 24)).pack(pady=10)
        tk.Label(left, text="Flight Totals", font=("Arial", 18)).pack()
        self.flight_listbox = tk.Listbox(left, width=40, height=5)
        self.flight_listbox.pack(pady=5)

        # Flight filter
        tk.Label(left, text="Filter by Flight").pack()
        self.flight_filter = tk.StringVar(value="All Flights")
        tk.OptionMenu(
            left, self.flight_filter,
            "All Flights", "A Flight", "B Flight", "C Flight", "D Flight",
            command=lambda _: self._refresh_leaderboard()
        ).pack()

        # Individual leaderboard
        tk.Label(left, text="Individual Cadets", font=("Arial", 18)).pack()
        self.cadet_listbox = tk.Listbox(left, width=55, height=25)
        self.cadet_listbox.pack(pady=5)

        # Buttons
        self.login_button = tk.Button(
            left, text="Staff Login",
            command=lambda: self.controller.show_frame("LoginFrame")
        )
        self.staff_button  = tk.Button(left, text="Staff Panel", command=self.controller.open_staff_panel)
        self.logout_button = tk.Button(left, text="Logout",      command=self.controller.logout)

        # Pie chart
        tk.Label(right, text="Flight Points Distribution", font=("Arial", 18)).pack(pady=10)
        self.chart_frame = tk.Frame(right)
        self.chart_frame.pack(fill="both")

    def _refresh_leaderboard(self):
        self.flight_listbox.delete(0, tk.END)
        self.cadet_listbox.delete(0, tk.END)

        for flight, total in get_flight_totals():
            self.flight_listbox.insert(tk.END, f"{flight} – {total} pts")

        leaderboard = get_leaderboard(self.flight_filter.get())
        if not leaderboard:
            self.cadet_listbox.insert(tk.END, "No cadets to display")
        else:
            for index, (name, flight, points) in enumerate(leaderboard, start=1):
                if   index == 1: prefix = "🥇 "
                elif index == 2: prefix = "🥈 "
                elif index == 3: prefix = "🥉 "
                else:            prefix = f"{index}. "
                self.cadet_listbox.insert(tk.END, f"{prefix}{name} ({flight}) – {points} pts")

        if self.controller.current_user_role == "staff":
            self.staff_button.pack(pady=5)
            self.logout_button.pack(pady=5)
            self.login_button.pack_forget()
        else:
            self.staff_button.pack_forget()
            self.logout_button.pack_forget()
            self.login_button.pack(pady=5)

        self._draw_pie_chart()

    def _draw_pie_chart(self):
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        data = get_flight_totals()
        if not data:
            return

        fig, ax = plt.subplots(figsize=(5, 5))
        ax.pie([r[1] for r in data], labels=[r[0] for r in data], autopct="%1.1f%%")
        ax.set_title("Points per Flight")

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    # ==============================================================================
    # EVENTS TAB
    # ==============================================================================

    def _build_events_tab(self):
        tab = self.events_tab

        tk.Label(tab, text="Most Popular Events", font=("Arial", 18, "bold")).pack(pady=(15, 2))
        tk.Label(
            tab,
            text="Click any bar to see which cadets earned that award",
            font=("Arial", 10), fg="#555555"
        ).pack(pady=(0, 8))

        # Bar chart area
        self.bar_chart_frame = tk.Frame(tab)
        self.bar_chart_frame.pack(fill="both", expand=True, padx=20)

        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=20, pady=8)

        # Selected event label
        self.event_title_label = tk.Label(
            tab,
            text="Select an event above to see attendees",
            font=("Arial", 13, "bold"), fg="#1a1a2e"
        )
        self.event_title_label.pack()

        # Cadet treeview
        list_frame = tk.Frame(tab)
        list_frame.pack(fill="x", padx=20, pady=(5, 15))

        scroll = tk.Scrollbar(list_frame)
        scroll.pack(side="right", fill="y")

        self.event_cadet_tree = ttk.Treeview(
            list_frame,
            yscrollcommand=scroll.set,
            columns=("cadet", "flight", "date", "awarded_by"),
            show="headings",
            height=8
        )
        scroll.config(command=self.event_cadet_tree.yview)

        self.event_cadet_tree.heading("cadet",      text="Cadet")
        self.event_cadet_tree.heading("flight",     text="Flight")
        self.event_cadet_tree.heading("date",       text="Date Awarded")
        self.event_cadet_tree.heading("awarded_by", text="Awarded By")

        self.event_cadet_tree.column("cadet",      width=200, anchor="w")
        self.event_cadet_tree.column("flight",     width=100, anchor="center")
        self.event_cadet_tree.column("date",       width=120, anchor="center")
        self.event_cadet_tree.column("awarded_by", width=150, anchor="center")

        style = ttk.Style()
        style.configure("Treeview",         font=("Arial", 11), rowheight=28)
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        self.event_cadet_tree.tag_configure("odd",  background="#f0f4ff")
        self.event_cadet_tree.tag_configure("even", background="#ffffff")

        self.event_cadet_tree.pack(fill="x")

    def _refresh_events_tab(self):
        for widget in self.bar_chart_frame.winfo_children():
            widget.destroy()

        self._event_data = get_most_popular_events(limit=15)

        if not self._event_data:
            tk.Label(
                self.bar_chart_frame,
                text="No event data yet — award some points first!",
                font=("Arial", 12), fg="#888888"
            ).pack(pady=40)
            return

        labels = [f"{row[0]}\n{row[1]}" for row in self._event_data]
        counts = [row[2] for row in self._event_data]
        colours = []
        for cat, sub, _ in self._event_data:
            if self._selected_event == (cat, sub):
                colours.append("#e8a838")   # gold highlight for selected bar
            else:
                colours.append("#4a6fa5")   # default blue

        fig, ax = plt.subplots(figsize=(12, 4))
        ax.bar(range(len(labels)), counts, color=colours, edgecolor="white", linewidth=0.8)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=8, ha="center")
        ax.set_ylabel("Number of Cadets")
        ax.set_title("Most Popular Events  (by number of cadets awarded)")
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.bar_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

        # Re-connect click handler to the new canvas
        canvas.mpl_connect("button_press_event", self._on_bar_click)

        # Restore cadet list if a bar was already selected
        if self._selected_event:
            self._show_cadets_for_event(*self._selected_event)

    def _on_bar_click(self, event):
        if event.xdata is None:
            return
        index = int(round(event.xdata))
        if 0 <= index < len(self._event_data):
            cat, sub, _ = self._event_data[index]
            self._selected_event = (cat, sub)
            self._refresh_events_tab()  # Redraw with gold highlight + populate list

    def _show_cadets_for_event(self, category, subcategory):
        self.event_title_label.config(
            text=f"Cadets who earned:  {category}  ›  {subcategory}"
        )
        for row in self.event_cadet_tree.get_children():
            self.event_cadet_tree.delete(row)

        cadets = get_cadets_for_event(category, subcategory)
        if not cadets:
            self.event_cadet_tree.insert("", tk.END, values=("No cadets found", "", "", ""))
        else:
            for i, (name, flight, date, awarded_by) in enumerate(cadets):
                tag = "odd" if i % 2 == 0 else "even"
                self.event_cadet_tree.insert("", tk.END, values=(
                    name, flight, date, awarded_by or "—"
                ), tags=(tag,))

    # ==============================================================================
    # FRAME CONTROL
    # ==============================================================================

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        self.refresh()

    def refresh(self):
        self._refresh_leaderboard()
        if self.notebook.index(self.notebook.select()) == 1:
            self._refresh_events_tab()

    def _on_tab_changed(self, event):
        if self.notebook.index(self.notebook.select()) == 1:
            self._refresh_events_tab()