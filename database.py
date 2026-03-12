import sqlite3
import hashlib
import datetime
import os

DB_FILE = "data/cadet_points.db"


def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    # Enforce foreign key constraints on every connection
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==============================================================================
# DATABASE INITIALISATION
# Creates all tables with primary keys, foreign keys, and constraints.
#
# Relationships implemented:
#   ONE-TO-ONE  : users  ──── staff_profiles
#   ONE-TO-MANY : flights ──< cadets
#   ONE-TO-MANY : cadets  ──< point_history
#   ONE-TO-MANY : users   ──< point_history
#   ONE-TO-MANY : point_categories ──< point_history
#   MANY-TO-MANY: cadets >──< point_categories  (via cadet_awards junction table)
# ==============================================================================

def initialise_database():
    conn = get_connection()
    cursor = conn.cursor()

    # ── flights ────────────────────────────────────────────────────────────────
    # Stores the four flights as entities rather than plain text strings.
    # ONE-TO-MANY: one flight has many cadets.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flights (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT    NOT NULL UNIQUE
        )
    """)

    # Seed the four flights if they don't exist yet
    for flight_name in ("A Flight", "B Flight", "C Flight", "D Flight"):
        cursor.execute(
            "INSERT OR IGNORE INTO flights (name) VALUES (?)",
            (flight_name,)
        )

    # ── cadets ─────────────────────────────────────────────────────────────────
    # Each cadet belongs to exactly one flight (flight_id FK).
    # ONE-TO-MANY: one cadet has many point_history entries.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cadets (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            flight_id INTEGER NOT NULL REFERENCES flights(id),
            points    INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ── users ──────────────────────────────────────────────────────────────────
    # Staff login credentials.
    # ONE-TO-ONE : each user has exactly one staff_profile.
    # ONE-TO-MANY: one user (staff member) appears in many point_history entries.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'staff'
        )
    """)

    # ── staff_profiles ─────────────────────────────────────────────────────────
    # Stores personal details for each staff member separately from login data.
    # ONE-TO-ONE: linked to users by username (same PK = FK pattern).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff_profiles (
            username TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
            full_name TEXT,
            rank      TEXT,
            joined_date TEXT
        )
    """)

    # ── point_categories ───────────────────────────────────────────────────────
    # Each row is a specific award within a category (e.g. Shooting > Gold).
    # ONE-TO-MANY: one category row can appear in many point_history entries.
    # MANY-TO-MANY: linked to cadets via cadet_awards junction table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS point_categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT    NOT NULL,
            subcategory TEXT    NOT NULL,
            points      INTEGER NOT NULL,
            UNIQUE(category, subcategory)
        )
    """)

    # ── point_history ──────────────────────────────────────────────────────────
    # Audit log of every point award event.
    # Foreign keys link to: cadets, users, point_categories.
    # is_custom = 1 means staff entered a manual value (point_category_id is NULL).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS point_history (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            cadet_id           INTEGER NOT NULL REFERENCES cadets(id),
            points             INTEGER NOT NULL,
            category           TEXT,
            reason             TEXT,
            timestamp          TEXT    NOT NULL,
            is_custom          INTEGER NOT NULL DEFAULT 0,
            staff_username     TEXT    REFERENCES users(username),
            point_category_id  INTEGER REFERENCES point_categories(id)
        )
    """)

    # ── cadet_awards ───────────────────────────────────────────────────────────
    # Junction / link table implementing the MANY-TO-MANY relationship between
    # cadets and point_categories.
    # A cadet can earn many different awards; the same award can go to many cadets.
    # date_awarded lets us track when each specific award was first achieved.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cadet_awards (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            cadet_id           INTEGER NOT NULL REFERENCES cadets(id)           ON DELETE CASCADE,
            point_category_id  INTEGER NOT NULL REFERENCES point_categories(id) ON DELETE CASCADE,
            date_awarded       TEXT    NOT NULL,
            awarded_by         TEXT    REFERENCES users(username),
            UNIQUE(cadet_id, point_category_id)
        )
    """)

    # ── MIGRATIONS ─────────────────────────────────────────────────────────────
    # Safely add columns to existing databases without losing data.

    # cadets: add flight_id if upgrading from the old text-based flight column
    cursor.execute("PRAGMA table_info(cadets)")
    cadet_cols = [col[1] for col in cursor.fetchall()]

    if "flight_id" not in cadet_cols and "flight" in cadet_cols:
        # Add the new FK column as nullable first
        cursor.execute("ALTER TABLE cadets ADD COLUMN flight_id INTEGER REFERENCES flights(id)")
        # Populate it by matching the old text value to the flights table
        cursor.execute("""
            UPDATE cadets
            SET flight_id = (
                SELECT flights.id FROM flights
                WHERE flights.name = cadets.flight
            )
        """)
        # Default any unmatched rows to A Flight
        cursor.execute("""
            UPDATE cadets SET flight_id = (SELECT id FROM flights WHERE name = 'A Flight')
            WHERE flight_id IS NULL
        """)

    # point_history: add missing columns for older databases
    cursor.execute("PRAGMA table_info(point_history)")
    history_cols = [col[1] for col in cursor.fetchall()]

    if "is_custom" not in history_cols:
        cursor.execute("ALTER TABLE point_history ADD COLUMN is_custom INTEGER DEFAULT 0")

    if "staff_username" not in history_cols:
        cursor.execute("ALTER TABLE point_history ADD COLUMN staff_username TEXT DEFAULT 'unknown'")

    if "point_category_id" not in history_cols:
        cursor.execute("ALTER TABLE point_history ADD COLUMN point_category_id INTEGER REFERENCES point_categories(id)")

    conn.commit()
    conn.close()


# ==============================================================================
# PASSWORD HASHING
# ==============================================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ==============================================================================
# USERS  (ONE-TO-ONE with staff_profiles)
# ==============================================================================

def create_user(username, password, role="staff"):
    """Create a user account. INSERT OR IGNORE means duplicates are silently skipped."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users VALUES (?, ?, ?)",
        (username, hash_password(password), role)
    )
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    # JOIN to staff_profiles so we can show rank/full name alongside username
    cursor.execute("""
        SELECT users.username, users.role,
               COALESCE(staff_profiles.full_name, ''),
               COALESCE(staff_profiles.rank, '')
        FROM users
        LEFT JOIN staff_profiles ON users.username = staff_profiles.username
        ORDER BY users.username
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_user(username):
    conn = get_connection()
    cursor = conn.cursor()
    # ON DELETE CASCADE on staff_profiles means the profile is auto-deleted too
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def authenticate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password_hash, role FROM users WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    conn.close()
    if result and result[0] == hash_password(password):
        return result[1]
    return None


# ==============================================================================
# STAFF PROFILES  (ONE-TO-ONE with users)
# ==============================================================================

def upsert_staff_profile(username, full_name, rank):
    """Insert or update a staff member's profile details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO staff_profiles (username, full_name, rank)
        VALUES (?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            full_name = excluded.full_name,
            rank      = excluded.rank
    """, (username, full_name, rank))
    conn.commit()
    conn.close()


def get_staff_profile(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT users.username, users.role, staff_profiles.full_name, staff_profiles.rank
        FROM users
        LEFT JOIN staff_profiles ON users.username = staff_profiles.username
        WHERE users.username = ?
    """, (username,))
    row = cursor.fetchone()
    conn.close()
    return row


# ==============================================================================
# FLIGHTS  (ONE-TO-MANY: one flight → many cadets)
# ==============================================================================

def get_all_flights():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM flights ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_flight_totals():
    """Returns total points per flight by JOINing cadets to flights."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT flights.name, COALESCE(SUM(cadets.points), 0)
        FROM flights
        LEFT JOIN cadets ON cadets.flight_id = flights.id
        GROUP BY flights.id
        ORDER BY SUM(cadets.points) DESC
    """)
    results = cursor.fetchall()
    conn.close()
    return results


# ==============================================================================
# CADETS  (MANY-TO-ONE: many cadets → one flight)
# ==============================================================================

def add_cadet(name, flight_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM flights WHERE name = ?", (flight_name,))
    flight_row = cursor.fetchone()
    if not flight_row:
        conn.close()
        raise ValueError(f"Flight '{flight_name}' not found")

    # Write both flight_id (new FK) and flight (legacy text column) so existing
    # databases with a NOT NULL constraint on flight are still satisfied.
    cursor.execute("""
        INSERT INTO cadets (name, flight, flight_id) VALUES (?, ?, ?)
    """, (name, flight_name, flight_row[0]))
    conn.commit()
    conn.close()


def get_all_cadets():
    """Returns cadets with their flight name via JOIN to flights table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cadets.id, cadets.name, flights.name, cadets.points
        FROM cadets
        JOIN flights ON cadets.flight_id = flights.id
        ORDER BY cadets.name
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_cadet(cadet_id):
    conn = get_connection()
    cursor = conn.cursor()
    # Delete history and awards first (cadet_awards has CASCADE but point_history does not)
    cursor.execute("DELETE FROM point_history WHERE cadet_id = ?", (cadet_id,))
    cursor.execute("DELETE FROM cadet_awards  WHERE cadet_id = ?", (cadet_id,))
    cursor.execute("DELETE FROM cadets        WHERE id = ?",       (cadet_id,))
    conn.commit()
    conn.close()


def update_cadet_flight(cadet_id, new_flight_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM flights WHERE name = ?", (new_flight_name,))
    flight_row = cursor.fetchone()
    if not flight_row:
        conn.close()
        raise ValueError(f"Flight '{new_flight_name}' not found")
    # Update both columns to keep legacy and new schema in sync
    cursor.execute(
        "UPDATE cadets SET flight = ?, flight_id = ? WHERE id = ?",
        (new_flight_name, flight_row[0], cadet_id)
    )
    conn.commit()
    conn.close()


def get_leaderboard(flight_name=None):
    conn = get_connection()
    cursor = conn.cursor()
    if flight_name is None or flight_name == "All Flights":
        cursor.execute("""
            SELECT cadets.name, flights.name, cadets.points
            FROM cadets
            JOIN flights ON cadets.flight_id = flights.id
            ORDER BY cadets.points DESC
        """)
    else:
        cursor.execute("""
            SELECT cadets.name, flights.name, cadets.points
            FROM cadets
            JOIN flights ON cadets.flight_id = flights.id
            WHERE flights.name = ?
            ORDER BY cadets.points DESC
        """, (flight_name,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ==============================================================================
# POINTS  (point_history links cadets, users, and point_categories)
# ==============================================================================

def add_points(cadet_id, points, category, reason, is_custom,
               staff_username="unknown", point_category_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    # Update the cadet's running total
    cursor.execute(
        "UPDATE cadets SET points = points + ? WHERE id = ?",
        (points, cadet_id)
    )

    # Insert a full audit record into point_history
    cursor.execute("""
        INSERT INTO point_history
            (cadet_id, points, category, reason, timestamp, is_custom,
             staff_username, point_category_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cadet_id, points, category, reason,
        datetime.datetime.now().isoformat(),
        int(is_custom), staff_username, point_category_id
    ))

    # If this is a standard award (not custom), record it in cadet_awards too.
    # UNIQUE constraint means each cadet/award pair is only stored once — this
    # shows the many-to-many relationship between cadets and point_categories.
    if point_category_id and not is_custom:
        cursor.execute("""
            INSERT OR IGNORE INTO cadet_awards
                (cadet_id, point_category_id, date_awarded, awarded_by)
            VALUES (?, ?, ?, ?)
        """, (
            cadet_id, point_category_id,
            datetime.datetime.now().isoformat()[:10],
            staff_username
        ))

    conn.commit()
    conn.close()


def undo_last_action():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, cadet_id, points, point_category_id
        FROM point_history
        ORDER BY id DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    history_id, cadet_id, points, point_category_id = row

    cursor.execute(
        "UPDATE cadets SET points = points - ? WHERE id = ?",
        (points, cadet_id)
    )
    cursor.execute(
        "DELETE FROM point_history WHERE id = ?",
        (history_id,)
    )

    # Also remove from cadet_awards if this was the only award of that type
    if point_category_id:
        cursor.execute("""
            SELECT COUNT(*) FROM point_history
            WHERE cadet_id = ? AND point_category_id = ?
        """, (cadet_id, point_category_id))
        remaining = cursor.fetchone()[0]
        if remaining == 0:
            cursor.execute("""
                DELETE FROM cadet_awards
                WHERE cadet_id = ? AND point_category_id = ?
            """, (cadet_id, point_category_id))

    conn.commit()
    conn.close()
    return True


def get_point_history(limit=50):
    """
    Returns point history with full relational data:
    - Cadet name and flight pulled from cadets JOIN flights
    - Category and subcategory pulled from point_categories (COALESCE falls back
      to stored text for custom/legacy entries)
    - Staff username from point_history
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            point_history.id,
            cadets.name,
            flights.name,
            point_history.points,
            COALESCE(point_categories.category,    point_history.category) AS category,
            COALESCE(point_categories.subcategory, point_history.reason)   AS reason,
            point_history.timestamp,
            point_history.is_custom,
            point_history.staff_username
        FROM point_history
        JOIN cadets          ON point_history.cadet_id          = cadets.id
        JOIN flights         ON cadets.flight_id                = flights.id
        LEFT JOIN point_categories ON point_history.point_category_id = point_categories.id
        ORDER BY point_history.timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ==============================================================================
# POINT CATEGORIES  (ONE-TO-MANY with point_history; MANY-TO-MANY with cadets)
# ==============================================================================

from point_system import POINT_CATEGORIES


def populate_point_categories():
    """Seeds point_categories from point_system.py on first run."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM point_categories")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    for category, awards in POINT_CATEGORIES.items():
        for subcategory, points in awards.items():
            cursor.execute("""
                INSERT INTO point_categories (category, subcategory, points)
                VALUES (?, ?, ?)
            """, (category, subcategory, points))
    conn.commit()
    conn.close()


def get_point_categories():
    """Returns {category: {subcategory: points}} dict."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, subcategory, points
        FROM point_categories
        ORDER BY category, points
    """)
    rows = cursor.fetchall()
    conn.close()
    categories = {}
    for category, subcategory, points in rows:
        categories.setdefault(category, {})[subcategory] = points
    return categories


def get_point_category_id(category, subcategory):
    """Looks up the primary key id for a given category + subcategory pair."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM point_categories
        WHERE category = ? AND subcategory = ?
    """, (category, subcategory))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def update_point_value(category, subcategory, new_points):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE point_categories SET points = ?
        WHERE category = ? AND subcategory = ?
    """, (new_points, category, subcategory))
    conn.commit()
    conn.close()


def add_point_category(category, subcategory, points):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO point_categories (category, subcategory, points)
        VALUES (?, ?, ?)
    """, (category, subcategory, points))
    conn.commit()
    conn.close()


# ==============================================================================
# CADET AWARDS  (MANY-TO-MANY junction table: cadets <-> point_categories)
# ==============================================================================

def get_cadet_awards(cadet_id):
    """
    Returns all awards a specific cadet has achieved.
    Demonstrates a cross-table JOIN across the many-to-many junction table.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            point_categories.category,
            point_categories.subcategory,
            point_categories.points,
            cadet_awards.date_awarded,
            cadet_awards.awarded_by
        FROM cadet_awards
        JOIN point_categories ON cadet_awards.point_category_id = point_categories.id
        WHERE cadet_awards.cadet_id = ?
        ORDER BY point_categories.category, point_categories.subcategory
    """, (cadet_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_award_holders(point_category_id):
    """
    Returns all cadets who have achieved a specific award.
    The reverse traversal of the many-to-many relationship.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            cadets.name,
            flights.name,
            cadet_awards.date_awarded,
            cadet_awards.awarded_by
        FROM cadet_awards
        JOIN cadets  ON cadet_awards.cadet_id  = cadets.id
        JOIN flights ON cadets.flight_id       = flights.id
        WHERE cadet_awards.point_category_id = ?
        ORDER BY cadet_awards.date_awarded DESC
    """, (point_category_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows