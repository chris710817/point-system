import os
import base64
import tempfile
import webbrowser
from io import BytesIO
import tkinter as tk
from tkinter import ttk
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
from database import get_leaderboard, get_flight_totals, get_available_years, get_most_popular_events, get_cadets_for_event

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class LeaderboardFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self._images = []  # prevent garbage collection of PhotoImage objects

        # Track the currently selected event bar
        self._selected_event = None
        self._event_data = []

        self.year_var = tk.StringVar()
        self.events_year_var = tk.StringVar()

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

    def _add_logo(self, parent, filename, height=90):
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

    def _build_leaderboard_tab(self):
        tab = self.leaderboard_tab

        # Header strip: RAFAC logo | squadron name | Hutton badge
        header = tk.Frame(tab, pady=8)
        header.pack(fill="x")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=2)
        header.columnconfigure(2, weight=1)

        left_logo = tk.Frame(header)
        left_logo.grid(row=0, column=0, sticky="nsew")
        self._add_logo(left_logo, "rafac_logo.png", height=90)

        tk.Label(
            header,
            text="2476 Hutton Squadron\nAir Training Corps",
            font=("Arial", 17, "bold"), fg="#1a1a2e", justify="center"
        ).grid(row=0, column=1)

        right_logo = tk.Frame(header)
        right_logo.grid(row=0, column=2, sticky="nsew")
        self._add_logo(right_logo, "hutton_atc_logo.png", height=90)

        ttk.Separator(tab, orient="horizontal").pack(fill="x")

        main = tk.Frame(tab)
        main.pack(fill="both", expand=True)

        left  = tk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        right = tk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)

        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)

        # Title + year selector on the same row
        top_row = tk.Frame(left)
        top_row.pack(pady=10)
        tk.Label(top_row, text="Leaderboard", font=("Arial", 24)).pack(side="left", padx=(0, 20))
        tk.Label(top_row, text="Year:", font=("Arial", 12)).pack(side="left")
        self.year_menu = tk.OptionMenu(top_row, self.year_var, "All Time",
                                       command=lambda _: self._refresh_leaderboard())
        self.year_menu.config(font=("Arial", 11))
        self.year_menu.pack(side="left", padx=5)

        # Flight totals
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
        tk.Button(left, text="Export / Print", font=("Arial", 10),
                  command=self._export_leaderboard).pack(pady=(8, 2))

        # Pie chart
        tk.Label(right, text="Flight Points Distribution", font=("Arial", 18)).pack(pady=10)
        self.chart_frame = tk.Frame(right)
        self.chart_frame.pack(fill="both")

    def _export_leaderboard(self):
        selected = self.year_var.get()
        year = None if selected == "All Time" else selected
        year_label = selected

        flight_totals = get_flight_totals(year)
        cadets = get_leaderboard(flight_name=None, year=year)
        generated = datetime.datetime.now().strftime("%d %B %Y, %H:%M")
        medals = ["🥇", "🥈", "🥉"]

        # ── Pie chart → base64 PNG ────────────────────────────────────────────
        pie_data = [(f, t) for f, t in flight_totals if t > 0]
        if pie_data:
            fig, ax = plt.subplots(figsize=(5, 2.2))
            ax.pie([r[1] for r in pie_data], labels=[r[0] for r in pie_data],
                   autopct="%1.1f%%", textprops={"fontsize": 8})
            ax.set_title("Points per Flight", fontsize=9, pad=4)
            fig.tight_layout(pad=0.3)
            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            chart_b64 = base64.b64encode(buf.read()).decode("utf-8")
            pie_html = f'<div class="pie-section"><h3>Flight Distribution</h3><img src="data:image/png;base64,{chart_b64}" style="width:100%;max-height:52mm;object-fit:contain;display:block"></div>'
        else:
            pie_html = ""

        # ── Flight totals table ───────────────────────────────────────────────
        flight_rows = ""
        for i, (flight, total) in enumerate(flight_totals):
            medal = medals[i] if i < 3 else str(i + 1)
            flight_rows += f"<tr><td class='pos'>{medal}</td><td>{flight}</td><td class='pts'>{total}</td></tr>\n"

        # ── Individual cadet table ────────────────────────────────────────────
        cadet_rows = ""
        for i, (name, flight, points) in enumerate(cadets):
            medal = medals[i] if i < 3 else str(i + 1)
            row_class = ["gold", "silver", "bronze"][i] if i < 3 else ("odd" if i % 2 == 0 else "")
            cadet_rows += f"<tr class='{row_class}'><td class='pos'>{medal}</td><td>{name}</td><td>{flight}</td><td class='pts'>{points}</td></tr>\n"

        # ── Per-flight breakdown (one <div> per flight, laid out as a grid) ───
        flights_seen = {}
        for name, flight, points in cadets:
            flights_seen.setdefault(flight, []).append((name, points))

        flight_divs = ""
        for flight, members in sorted(flights_seen.items()):
            rows = ""
            for j, (name, points) in enumerate(members, start=1):
                row_class = "odd" if j % 2 == 1 else ""
                rows += f"<tr class='{row_class}'><td class='pos'>{j}</td><td class='cadet'>{name}</td><td class='pts'>{points}</td></tr>\n"
            flight_divs += f"""
            <div class="block">
              <h3>{flight}</h3>
              <table>
                <thead><tr><th>Pos</th><th>Cadet</th><th>Pts</th></tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>2476 Hutton Squadron – Leaderboard ({year_label})</title>
<style>
  @page {{ size: A4 landscape; margin: 8mm; }}
  * {{ box-sizing: border-box; }}

  body {{
    font-family: Arial, sans-serif;
    font-size: 9pt;
    color: #1a1a2e;
    margin: 0;
    padding: 4mm;
  }}

  /* ── Header ── */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 2px solid #1a1a2e;
    padding-bottom: 3px;
    margin-bottom: 5px;
  }}
  .header h1 {{ font-size: 12pt; margin: 0; }}
  .header span {{ font-size: 8pt; color: #555; white-space: nowrap; }}

  /* ── Section headings ── */
  h3 {{
    font-size: 8.5pt;
    margin: 0 0 3px 0;
    padding-bottom: 2px;
    border-bottom: 1px solid #1a1a2e;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    white-space: nowrap;
  }}

  /* ── Tables ── */
  table {{ border-collapse: collapse; width: auto; }}
  th {{
    background: #1a1a2e;
    color: white;
    padding: 2px 5px;
    text-align: left;
    font-size: 8pt;
    white-space: nowrap;
  }}
  td {{ padding: 1px 5px; border-bottom: 1px solid #e8e8e8; white-space: nowrap; }}
  .pos    {{ width: 24px; text-align: center; }}
  .pts    {{ text-align: right; font-weight: bold; padding-left: 8px; }}
  .cadet  {{ min-width: 90px; }}
  .gold   {{ background: #fff8dc; }}
  .silver {{ background: #f0f0f0; }}
  .bronze {{ background: #fdf0e0; }}
  .odd    {{ background: #f5f7ff; }}

  /* ── Single flex row: all blocks side by side ── */
  .row {{
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    gap: 5mm;
  }}
  .block {{ flex: 0 0 auto; }}
  .divider {{
    width: 1px;
    background: #ccc;
    align-self: stretch;
    flex-shrink: 0;
  }}

  /* ── Flights + pie nested column ── */
  .flights-col {{
    display: flex;
    flex-direction: column;
    gap: 4mm;
    flex: 0 0 auto;
  }}
  .flights-row {{
    display: flex;
    flex-direction: row;
    gap: 5mm;
    align-items: flex-start;
  }}
  .pie-section {{
    width: 100%;
  }}
  .pie-section h3 {{
    margin-bottom: 3px;
  }}
</style>
</head>
<body>

  <div class="header">
    <h1>2476 Hutton Squadron Air Training Corps &mdash; Points Leaderboard &mdash; {year_label}</h1>
    <span>Printed: {generated}</span>
  </div>

  <div class="row">
    <div class="block">
      <h3>Flight Totals</h3>
      <table>
        <thead><tr><th>Pos</th><th>Flight</th><th>Pts</th></tr></thead>
        <tbody>{flight_rows}</tbody>
      </table>
    </div>

    <div class="divider"></div>

    <div class="block">
      <h3>Overall Rankings</h3>
      <table>
        <thead><tr><th>Pos</th><th>Cadet</th><th>Flight</th><th>Pts</th></tr></thead>
        <tbody>{cadet_rows}</tbody>
      </table>
    </div>

    <div class="divider"></div>

    <div class="flights-col">
      <div class="flights-row">
        {flight_divs}
      </div>
      {pie_html}
    </div>
  </div>

</body>
</html>"""

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html",
                                         mode="w", encoding="utf-8")
        tmp.write(html)
        tmp.close()
        webbrowser.open(f"file:///{tmp.name}")

    def _reload_year_selector(self):
        """Rebuild the year dropdown from the database, defaulting to the current year."""
        years = get_available_years()
        current_year = str(datetime.date.today().year)
        menu = self.year_menu["menu"]
        menu.delete(0, "end")
        menu.add_command(label="All Time",
                         command=lambda: (self.year_var.set("All Time"), self._refresh_leaderboard()))
        for y in years:
            menu.add_command(label=y,
                             command=lambda v=y: (self.year_var.set(v), self._refresh_leaderboard()))
        # Set default: current year if it has data, otherwise All Time
        if self.year_var.get() not in (["All Time"] + years):
            self.year_var.set(current_year if current_year in years else "All Time")

    def _refresh_leaderboard(self):
        self.flight_listbox.delete(0, tk.END)
        self.cadet_listbox.delete(0, tk.END)

        selected = self.year_var.get()
        year = None if selected == "All Time" else selected

        for flight, total in get_flight_totals(year):
            self.flight_listbox.insert(tk.END, f"{flight} – {total} pts")

        leaderboard = get_leaderboard(self.flight_filter.get(), year)
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

        selected = self.year_var.get()
        year = None if selected == "All Time" else selected
        data = get_flight_totals(year)
        if not data or all(r[1] == 0 for r in data):
            tk.Label(self.chart_frame, text="No points awarded yet",
                     font=("Arial", 12), fg="#888888").pack(pady=40)
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

        top_row = tk.Frame(tab)
        top_row.pack(pady=(15, 2))
        tk.Label(top_row, text="Most Popular Events", font=("Arial", 18, "bold")).pack(side="left", padx=(0, 20))
        tk.Label(top_row, text="Year:", font=("Arial", 12)).pack(side="left")
        self.events_year_menu = tk.OptionMenu(top_row, self.events_year_var, "All Time",
                                              command=lambda _: self._refresh_events_tab())
        self.events_year_menu.config(font=("Arial", 11))
        self.events_year_menu.pack(side="left", padx=5)

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
            columns=("cadet", "flight", "date", "time", "awarded_by"),
            show="headings",
            height=8
        )
        scroll.config(command=self.event_cadet_tree.yview)

        self.event_cadet_tree.heading("cadet",      text="Cadet")
        self.event_cadet_tree.heading("flight",     text="Flight")
        self.event_cadet_tree.heading("date",       text="Date")
        self.event_cadet_tree.heading("time",       text="Time")
        self.event_cadet_tree.heading("awarded_by", text="Awarded By")

        self.event_cadet_tree.column("cadet",      width=200, anchor="w")
        self.event_cadet_tree.column("flight",     width=100, anchor="center")
        self.event_cadet_tree.column("date",       width=100, anchor="center")
        self.event_cadet_tree.column("time",       width=70,  anchor="center")
        self.event_cadet_tree.column("awarded_by", width=150, anchor="center")

        style = ttk.Style()
        style.configure("Treeview",         font=("Arial", 11), rowheight=28)
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        self.event_cadet_tree.tag_configure("odd",  background="#f0f4ff")
        self.event_cadet_tree.tag_configure("even", background="#ffffff")

        self.event_cadet_tree.pack(fill="x")

    def _reload_events_year_selector(self):
        years = get_available_years()
        current_year = str(datetime.date.today().year)
        menu = self.events_year_menu["menu"]
        menu.delete(0, "end")
        menu.add_command(label="All Time",
                         command=lambda: (self.events_year_var.set("All Time"), self._refresh_events_tab()))
        for y in years:
            menu.add_command(label=y,
                             command=lambda v=y: (self.events_year_var.set(v), self._refresh_events_tab()))
        if self.events_year_var.get() not in (["All Time"] + years):
            self.events_year_var.set(current_year if current_year in years else "All Time")

    def _refresh_events_tab(self):
        for widget in self.bar_chart_frame.winfo_children():
            widget.destroy()

        selected = self.events_year_var.get()
        year = None if selected == "All Time" else selected
        self._event_data = get_most_popular_events(limit=15, year=year)

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
            selected = self.events_year_var.get()
            year = None if selected == "All Time" else selected
            self._show_cadets_for_event(*self._selected_event, year=year)

    def _on_bar_click(self, event):
        if event.xdata is None:
            return
        index = int(round(event.xdata))
        if 0 <= index < len(self._event_data):
            cat, sub, _ = self._event_data[index]
            self._selected_event = (cat, sub)
            self._refresh_events_tab()  # Redraw with gold highlight + populate list

    def _show_cadets_for_event(self, category, subcategory, year=None):
        self.event_title_label.config(
            text=f"Cadets who earned:  {category}  ›  {subcategory}"
        )
        for row in self.event_cadet_tree.get_children():
            self.event_cadet_tree.delete(row)

        cadets = get_cadets_for_event(category, subcategory, year)
        if not cadets:
            self.event_cadet_tree.insert("", tk.END, values=("No cadets found", "", "", "", ""))
        else:
            for i, (name, flight, timestamp, awarded_by) in enumerate(cadets):
                date_part = timestamp[:10]
                time_part = timestamp[11:16]
                tag = "odd" if i % 2 == 0 else "even"
                self.event_cadet_tree.insert("", tk.END, values=(
                    name, flight, date_part, time_part, awarded_by or "—"
                ), tags=(tag,))

    # ==============================================================================
    # FRAME CONTROL
    # ==============================================================================

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        self.refresh()

    def refresh(self):
        self._reload_year_selector()
        self._refresh_leaderboard()
        if self.notebook.index(self.notebook.select()) == 1:
            self._reload_events_year_selector()
            self._refresh_events_tab()

    def _on_tab_changed(self, event):
        if self.notebook.index(self.notebook.select()) == 1:
            self._reload_events_year_selector()
            self._refresh_events_tab()