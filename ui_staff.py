import tkinter as tk
from tkinter import messagebox, ttk
from database import (
    add_cadet,
    get_all_cadets,
    add_points,
    undo_last_action,
    get_point_history,
    get_point_categories,
    get_point_category_id,
    update_point_value,
    update_cadet_flight,
    delete_cadet,
    add_point_category,
    create_user,
    get_all_users,
    delete_user,
    upsert_staff_profile,
)


class StaffFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.categories = get_point_categories()
        self.subcategory_map = {}
        self.edit_subcategory_map = {}

        # ==================== TOP BAR — Back button + Selected Cadet ====================
        top_bar = tk.Frame(self, pady=8)
        top_bar.pack(fill="x")

        tk.Button(
            top_bar, text="← Back", font=("Arial", 10, "bold"),
            command=lambda: controller.show_frame("LeaderboardFrame")
        ).pack(side="left", padx=15)

        self.selected_cadet_label = tk.Label(
            top_bar, text="No cadet selected",
            font=("Arial", 22, "bold"), fg="#1a1a2e"
        )
        self.selected_cadet_label.pack(side="left", padx=30)

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # ==================== THREE COLUMN CONTAINER ====================
        columns = tk.Frame(self)
        columns.pack(fill="both", expand=True)

        # ---- Left column: Audit log ----
        left_col = tk.Frame(columns, padx=10)
        left_col.pack(side="left", fill="both", expand=True, anchor="n")

        # ---- Middle column: Add Points + Staff Accounts ----
        mid_col = tk.Frame(columns, padx=15)
        mid_col.pack(side="left", anchor="n")

        # ---- Right column: Cadet & Category management ----
        right_col = tk.Frame(columns, padx=15)
        right_col.pack(side="left", anchor="n")

        # ==================== LEFT COLUMN — Audit Log ====================
        tk.Label(left_col, text="Point History", font=("Arial", 14, "bold")).pack(pady=5)

        tree_frame = tk.Frame(left_col)
        tree_frame.pack(fill="both", expand=True)

        tree_scroll = tk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")

        self.history_tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=tree_scroll.set,
            columns=("date", "time", "staff", "cadet", "flight", "points", "category", "award"),
            show="headings",
            height=30
        )
        tree_scroll.config(command=self.history_tree.yview)

        self.history_tree.heading("date",     text="Date")
        self.history_tree.heading("time",     text="Time")
        self.history_tree.heading("staff",    text="Staff")
        self.history_tree.heading("cadet",    text="Cadet")
        self.history_tree.heading("flight",   text="Flight")
        self.history_tree.heading("points",   text="Points")
        self.history_tree.heading("category", text="Category")
        self.history_tree.heading("award",    text="Award")

        self.history_tree.column("date",     width=90,  anchor="center")
        self.history_tree.column("time",     width=70,  anchor="center")
        self.history_tree.column("staff",    width=110, anchor="center")
        self.history_tree.column("cadet",    width=130, anchor="w")
        self.history_tree.column("flight",   width=70,  anchor="center")
        self.history_tree.column("points",   width=60,  anchor="center")
        self.history_tree.column("category", width=100, anchor="w")
        self.history_tree.column("award",    width=110, anchor="w")

        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 11), rowheight=30)
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

        self.history_tree.tag_configure("odd",    background="#f0f4ff")
        self.history_tree.tag_configure("even",   background="#ffffff")
        self.history_tree.tag_configure("custom", background="#fff3cd")

        self.history_tree.pack(fill="both", expand=True)

        # ==================== MIDDLE COLUMN — Add Points + Staff Accounts ====================

        # ---------------- Add Points ----------------
        tk.Label(mid_col, text="Add Points", font=("Arial", 14, "bold")).pack(pady=(10, 5))

        self.cadet_var = tk.IntVar()
        tk.Label(mid_col, text="Select Cadet", font=("Arial", 10, "bold")).pack()
        self.cadet_menu = tk.OptionMenu(mid_col, self.cadet_var, "")
        self.cadet_menu.pack()

        tk.Label(mid_col, text="Category", font=("Arial", 10, "bold")).pack(pady=(8, 0))
        self.category_var = tk.StringVar()
        self.category_menu = tk.OptionMenu(
            mid_col, self.category_var, *self.categories.keys(),
            command=self.update_subcategories
        )
        self.category_menu.pack()

        tk.Label(mid_col, text="Award", font=("Arial", 10, "bold")).pack(pady=(8, 0))
        self.subcategory_var = tk.StringVar()
        self.subcategory_menu = tk.OptionMenu(mid_col, self.subcategory_var, "")
        self.subcategory_menu.pack()

        if self.categories:
            first_category = list(self.categories.keys())[0]
            self.category_var.set(first_category)
            self.update_subcategories(first_category)

        tk.Label(mid_col, text="Custom Points (optional)", font=("Arial", 10, "bold")).pack(pady=(10, 0))
        self.custom_points_entry = tk.Entry(mid_col)
        self.custom_points_entry.pack()
        self.custom_points_entry.bind("<KeyRelease>", self.toggle_category_state)

        tk.Button(mid_col, text="Add Points", font=("Arial", 11, "bold"),
                  command=self.add_points).pack(pady=10)
        tk.Button(mid_col, text="Undo Last Action", fg="red",
                  command=self.undo_last).pack(pady=2)

        ttk.Separator(mid_col, orient="horizontal").pack(fill="x", pady=12)

        # ---------------- Staff Accounts ----------------
        tk.Label(mid_col, text="Staff Accounts", font=("Arial", 14, "bold")).pack(pady=(2, 5))

        self.staff_listbox = tk.Listbox(mid_col, width=30, height=6)
        self.staff_listbox.pack(pady=5)

        tk.Label(mid_col, text="Username", font=("Arial", 10, "bold")).pack()
        self.new_staff_username_entry = tk.Entry(mid_col)
        self.new_staff_username_entry.pack()

        tk.Label(mid_col, text="Password", font=("Arial", 10, "bold")).pack(pady=(5, 0))
        self.new_staff_password_entry = tk.Entry(mid_col, show="*")
        self.new_staff_password_entry.pack()

        tk.Label(mid_col, text="Full Name", font=("Arial", 10, "bold")).pack(pady=(5, 0))
        self.new_staff_fullname_entry = tk.Entry(mid_col)
        self.new_staff_fullname_entry.pack()

        tk.Label(mid_col, text="Rank", font=("Arial", 10, "bold")).pack(pady=(5, 0))
        self.new_staff_rank_entry = tk.Entry(mid_col)
        self.new_staff_rank_entry.pack()

        tk.Button(mid_col, text="Add Staff Account",
                  command=self.add_staff_account).pack(pady=5)
        tk.Button(mid_col, text="Delete Selected Account", fg="white", bg="red",
                  command=self.delete_staff_account).pack(pady=2)

        # ==================== RIGHT COLUMN — Cadet & Category Management ====================

        # ---------------- Add Cadet ----------------
        tk.Label(right_col, text="Add New Cadet", font=("Arial", 13, "bold")).pack(pady=(10, 2))

        tk.Label(right_col, text="Cadet Name", font=("Arial", 10, "bold")).pack()
        self.name_entry = tk.Entry(right_col)
        self.name_entry.pack()

        tk.Label(right_col, text="Flight", font=("Arial", 10, "bold")).pack()
        self.flight_var = tk.StringVar(value="A Flight")
        tk.OptionMenu(right_col, self.flight_var,
                      "A Flight", "B Flight", "C Flight", "D Flight").pack()

        tk.Button(right_col, text="Add Cadet", command=self.add_cadet).pack(pady=5)

        ttk.Separator(right_col, orient="horizontal").pack(fill="x", pady=8)

        # ---------------- Change Cadet Flight ----------------
        tk.Label(right_col, text="Change Cadet Flight", font=("Arial", 13, "bold")).pack(pady=(2, 2))

        self.move_flight_var = tk.StringVar(value="A Flight")
        tk.OptionMenu(right_col, self.move_flight_var,
                      "A Flight", "B Flight", "C Flight", "D Flight").pack()

        tk.Button(right_col, text="Move Cadet", command=self.move_cadet).pack(pady=5)
        tk.Button(right_col, text="Delete Cadet", fg="white", bg="red",
                  command=self.delete_cadet).pack(pady=2)

        ttk.Separator(right_col, orient="horizontal").pack(fill="x", pady=8)

        # ---------------- Edit Point Categories ----------------
        tk.Label(right_col, text="Edit Point Categories", font=("Arial", 13, "bold")).pack(pady=(2, 2))

        self.edit_category_var = tk.StringVar()
        self.edit_subcategory_var = tk.StringVar()

        tk.Label(right_col, text="Category", font=("Arial", 10, "bold")).pack()
        self.edit_category_menu = tk.OptionMenu(right_col, self.edit_category_var, "")
        self.edit_category_menu.pack()

        tk.Label(right_col, text="Award", font=("Arial", 10, "bold")).pack()
        self.edit_subcategory_menu = tk.OptionMenu(right_col, self.edit_subcategory_var, "")
        self.edit_subcategory_menu.pack()

        tk.Label(right_col, text="Points Value", font=("Arial", 10, "bold")).pack()
        self.edit_points_entry = tk.Entry(right_col)
        self.edit_points_entry.pack()

        tk.Button(right_col, text="Update Points",
                  command=self.update_category_points).pack(pady=5)

        self.load_edit_categories()

        ttk.Separator(right_col, orient="horizontal").pack(fill="x", pady=8)

        # ---------------- Add New Award ----------------
        tk.Label(right_col, text="Add New Award", font=("Arial", 13, "bold")).pack(pady=(2, 2))

        tk.Label(right_col, text="Category Name", font=("Arial", 10, "bold")).pack()
        self.new_cat_entry = tk.Entry(right_col)
        self.new_cat_entry.pack()

        tk.Label(right_col, text="Award Name", font=("Arial", 10, "bold")).pack()
        self.new_sub_entry = tk.Entry(right_col)
        self.new_sub_entry.pack()

        tk.Label(right_col, text="Points", font=("Arial", 10, "bold")).pack()
        self.new_points_entry = tk.Entry(right_col)
        self.new_points_entry.pack()

        tk.Button(right_col, text="Add Award", command=self.add_new_award).pack(pady=5)

    # ---------------- Disable dropdowns when custom used ----------------
    def toggle_category_state(self, event=None):
        state = "disabled" if self.custom_points_entry.get().strip() else "normal"
        self.category_menu.config(state=state)
        self.subcategory_menu.config(state=state)

    # ---------------- Frame Control ----------------
    def tkraise(self, *args, **kwargs):
        if self.controller.current_user_role != "staff":
            self.controller.show_frame("LeaderboardFrame")
            return
        super().tkraise(*args, **kwargs)
        self.refresh()

    # ---------------- Refresh ----------------
    def refresh(self):
        menu = self.cadet_menu["menu"]
        menu.delete(0, "end")

        self.cadets = get_all_cadets()

        for cadet_id, name, flight, points in self.cadets:
            menu.add_command(
                label=f"{name} ({flight})",
                command=lambda c=cadet_id: self.set_cadet(c)
            )

        if self.cadets:
            self.set_cadet(self.cadets[0][0])

        self.refresh_history()
        self.refresh_staff_list()

    # ---------------- History (Treeview) ----------------
    def refresh_history(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)

        for i, (_, name, flight, points, category, reason, timestamp, is_custom, staff) in enumerate(get_point_history(200)):
            date_part = timestamp[:10]
            time_part = timestamp[11:19]
            points_str = f"{points:+}"
            tag = "custom" if is_custom else ("odd" if i % 2 == 0 else "even")

            self.history_tree.insert("", tk.END, values=(
                date_part, time_part, staff, name, flight, points_str, category, reason
            ), tags=(tag,))

        # Snap to the top so the most recent entry (newest-first order) is always visible
        self.history_tree.yview_moveto(0)
        self.update_idletasks()  # Force the scrollbar thumb to redraw immediately

    # ---------------- Staff Accounts ----------------
    def refresh_staff_list(self):
        self.staff_listbox.delete(0, tk.END)
        for username, role, full_name, rank in get_all_users():
            display = f"{username}  [{role}]"
            if rank or full_name:
                display += f"  — {rank} {full_name}".strip()
            self.staff_listbox.insert(tk.END, display)

    def add_staff_account(self):
        username  = self.new_staff_username_entry.get().strip()
        password  = self.new_staff_password_entry.get().strip()
        full_name = self.new_staff_fullname_entry.get().strip()
        rank      = self.new_staff_rank_entry.get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Username and password cannot be empty")
            return

        # Create the login account in users table
        create_user(username, password, "staff")

        # Create the linked profile in staff_profiles (one-to-one relationship)
        upsert_staff_profile(username, full_name, rank)

        self.new_staff_username_entry.delete(0, tk.END)
        self.new_staff_password_entry.delete(0, tk.END)
        self.new_staff_fullname_entry.delete(0, tk.END)
        self.new_staff_rank_entry.delete(0, tk.END)
        self.refresh_staff_list()
        messagebox.showinfo("Success", f"Account '{username}' created")

    def delete_staff_account(self):
        selection = self.staff_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No account selected")
            return

        entry = self.staff_listbox.get(selection[0])
        username = entry.split("  [")[0]

        if username == self.controller.current_username:
            messagebox.showerror("Error", "You cannot delete your own account")
            return

        if not messagebox.askyesno("Confirm", f"Delete account '{username}'?"):
            return

        delete_user(username)
        self.refresh_staff_list()
        messagebox.showinfo("Deleted", f"Account '{username}' deleted")

    # ---------------- Add Points ----------------
    def add_points(self):
        cadet_id = self.cadet_var.get()
        if not cadet_id:
            messagebox.showerror("Error", "No cadet selected")
            return

        custom_text = self.custom_points_entry.get().strip()

        if custom_text:
            try:
                points = int(custom_text)
            except ValueError:
                messagebox.showerror("Error", "Custom points must be a number")
                return

            if points < 0 and not messagebox.askyesno(
                "Confirm Penalty", f"Deduct {abs(points)} points?"
            ):
                return

            category = "Custom"
            reason = "Manual adjustment"
            is_custom = 1
            point_category_id = None
        else:
            category = self.category_var.get()
            label = self.subcategory_var.get()
            subcategory = self.subcategory_map[label]
            points = self.categories[category][subcategory]
            reason = subcategory
            is_custom = 0
            point_category_id = get_point_category_id(category, subcategory)

        add_points(cadet_id, points, category, reason, is_custom,
                   self.controller.current_username, point_category_id)

        messagebox.showinfo("Success", f"{points:+} points awarded")
        self.custom_points_entry.delete(0, tk.END)
        self.toggle_category_state()
        self.refresh()

    # ---------------- Add Cadet ----------------
    def add_cadet(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Cadet name cannot be empty")
            return

        add_cadet(name, self.flight_var.get())
        self.name_entry.delete(0, tk.END)
        self.refresh()

    # ---------------- Update Subcategories ----------------
    def update_subcategories(self, selected_category):
        menu = self.subcategory_menu["menu"]
        menu.delete(0, "end")
        self.subcategory_map.clear()

        for award, points in self.categories[selected_category].items():
            label = f"{award} (+{points})"
            self.subcategory_map[label] = award
            menu.add_command(
                label=label,
                command=lambda l=label: self.subcategory_var.set(l)
            )

        self.subcategory_var.set(next(iter(self.subcategory_map)))

    # ---------------- Undo ----------------
    def undo_last(self):
        if undo_last_action():
            self.refresh()
        else:
            messagebox.showwarning("Undo", "Nothing to undo")

    # ---------------- Edit Categories ----------------
    def load_edit_categories(self):
        self.edit_categories = get_point_categories()
        menu = self.edit_category_menu["menu"]
        menu.delete(0, "end")

        for cat in self.edit_categories:
            menu.add_command(
                label=cat,
                command=lambda c=cat: self.select_edit_category(c)
            )

        self.select_edit_category(next(iter(self.edit_categories)))

    def select_edit_category(self, category):
        self.edit_category_var.set(category)
        menu = self.edit_subcategory_menu["menu"]
        menu.delete(0, "end")
        self.edit_subcategory_map.clear()

        for award, points in self.edit_categories[category].items():
            label = f"{award} (+{points})"
            self.edit_subcategory_map[label] = award
            menu.add_command(
                label=label,
                command=lambda l=label: self.select_edit_award(l)
            )

        self.select_edit_award(next(iter(self.edit_subcategory_map)))

    def select_edit_award(self, label):
        self.edit_subcategory_var.set(label)
        award = self.edit_subcategory_map[label]
        category = self.edit_category_var.get()
        points = self.edit_categories[category][award]

        self.edit_points_entry.delete(0, tk.END)
        self.edit_points_entry.insert(0, str(points))

    def update_category_points(self):
        category = self.edit_category_var.get()
        label = self.edit_subcategory_var.get()
        award = self.edit_subcategory_map[label]

        try:
            new_points = int(self.edit_points_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Points must be numeric")
            return

        update_point_value(category, award, new_points)
        self.categories = get_point_categories()
        self.load_edit_categories()
        self.update_subcategories(self.category_var.get())

    # ---------------- Set Cadet ----------------
    def set_cadet(self, cadet_id):
        self.cadet_var.set(cadet_id)
        for cid, name, flight, points in self.cadets:
            if cid == cadet_id:
                self.selected_cadet_label.config(
                    text=f"✦  {name}  |  {flight}  |  {points} pts"
                )
                break

    # ---------------- Move Cadet ----------------
    def move_cadet(self):
        cadet_id = self.cadet_var.get()
        new_flight = self.move_flight_var.get()

        if not cadet_id:
            messagebox.showerror("Error", "No cadet selected")
            return

        if not messagebox.askyesno("Confirm", f"Move cadet to {new_flight}?"):
            return

        update_cadet_flight(cadet_id, new_flight)
        messagebox.showinfo("Success", "Cadet moved")
        self.refresh()

    # ---------------- Delete Cadet ----------------
    def delete_cadet(self):
        cadet_id = self.cadet_var.get()

        if not cadet_id:
            messagebox.showerror("Error", "No cadet selected")
            return

        if not messagebox.askyesno(
            "PERMANENT DELETE",
            "This will permanently delete the cadet and ALL history.\n\nContinue?"
        ):
            return

        delete_cadet(cadet_id)
        messagebox.showinfo("Deleted", "Cadet removed")
        self.refresh()

    # ---------------- Add New Award ----------------
    def add_new_award(self):
        cat = self.new_cat_entry.get().strip()
        sub = self.new_sub_entry.get().strip()
        pts = self.new_points_entry.get().strip()

        if not cat or not sub:
            messagebox.showerror("Error", "Please enter a category and award name")
            return

        try:
            pts_int = int(pts)
        except ValueError:
            messagebox.showerror("Error", "Points must be a whole number (can be negative)")
            return

        add_point_category(cat, sub, pts_int)
        messagebox.showinfo("Success", f"{cat} - {sub} added")

        self.new_cat_entry.delete(0, tk.END)
        self.new_sub_entry.delete(0, tk.END)
        self.new_points_entry.delete(0, tk.END)

        self.categories = get_point_categories()
        self.load_edit_categories()
        self.update_subcategories(self.category_var.get())