from flask import Flask, render_template, redirect, request, session
from flask_session import Session
import mysql.connector
from datetime import timedelta, datetime, date, time
import string
import re
import random
import os
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from decimal import Decimal, InvalidOperation

from utilities import (
  fetch_route_duration_hours, can_use_plane, can_assign_staff,fetch_flight,lock_total_price_at_booking_time,
  fetch_plane_size, required_crew_by_plane_size, validate_long_flight_plane_size,fetch_airports_from_flight_duration,
_fetch_available_resources,_build_flight_row_for_checks, _compute_landing_time,_normalize_time,_normalize_date,_flight_capacity_for_plane)






app = Flask(__name__)
app.config["SECRET_KEY"] = "flytau-dev-secret"



app.config.update(
    SESSION_TYPE="filesystem",
    # SESSION_FILE_DIR="flask_session_data",   # if using local
    SESSION_FILE_DIR="/home/segev/information_systems_project/flask_session_data",   # if using pythonanywhere
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=10),
    SESSION_REFRESH_EACH_REQUEST=True,
    SESSION_COOKIE_SECURE=False              # אם אתה עובד על localhost (לא https)
)

Session(app)

mydb = mysql.connector.connect(

    # # #### if using local ####
    # host="localhost",
    # user="root",
    # password="root",
    # database="flytau",

    ### if using pythonanywhere ####
    host= "segev.mysql.pythonanywhere-services.com",
    user="segev",
    password="Amit1111",
    database="segev$flytau_DB",

    #### General ####
    autocommit=True
)

def ensure_mydb_is_connected():
    global mydb
    if not mydb.is_connected():
        mydb.reconnect(attempts=3, delay=2)

@app.route("/")
def homepage():
        return render_template("Homepage.html")

@app.route("/session/clear")
def session_clear():
    session.clear()
    return redirect("/")


@app.route("/login", methods=["POST", "GET"])
def login():

    if request.method == "POST":
        email = request.form.get("email")
        pw = request.form.get("password")

        ensure_mydb_is_connected()
        cur = mydb.cursor()
        cur.execute("SELECT `password` FROM `registered_customers` WHERE `email` = %s",(email,))
        row = cur.fetchone()
        cur.close()

        if row is None:
            return render_template("login.html", message="Email not found")

        db_password = row[0]

        if db_password == pw:
            session.clear()
            session["role"] = "user"
            session["username"] = email
            return redirect("/user_home")
        else:
            return render_template("login.html", message="Incorrect password")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()      # מוחק את כל הסשן (user / admin / role)
    return render_template("homepage.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        first_name = request.form.get("fname")
        last_name = request.form.get("lname")
        date_of_birth = request.form.get("date_of_birth")
        passport_number = request.form.get("passport")
        password = request.form.get("password")
        now = datetime.now()

        phones = request.form.getlist("phone")

        clean_phones = []
        seen = set()
        for p in phones:
            p = (p or "").strip()
            if not p:
                continue
            if p in seen:
                continue
            seen.add(p)
            clean_phones.append(p)

        ensure_mydb_is_connected()
        cur = mydb.cursor()

        cur.execute("SELECT 1 FROM `registered_customers` WHERE `email` = %s", (email,))
        exists = cur.fetchone()

        if exists:
            cur.close()
            return render_template("signup.html", message="Email already exists")

        cur.execute(
            "INSERT INTO `registered_customers` (`email`,`fname`, `lname`, `date_of_birth`, `passport`, `password`, `registration_date`) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (email, first_name, last_name, date_of_birth, passport_number, password, now)
        )

        sql_phone = """
            INSERT INTO `phone_numbers` (`email`, `phone_number`)
            VALUES (%s, %s)
        """
        for phone in clean_phones:
            cur.execute(sql_phone, (email, phone))

        cur.close()
        session["role"] = "user"
        session["username"] = email
        return redirect("/user_home")

    return render_template("signup.html")

@app.route("/user_home")
def user_home():
    if session.get("role") != "user":
        return redirect("/login")
    return render_template("user_home.html", username=session["username"])


def _sold_count_for_flight(cur, flight_date, departure_time):
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM tickets t
        JOIN bookings b ON b.booking_code = t.booking_code
        WHERE t.flight_date = %s
          AND t.departure_time = %s
          AND LOWER(b.status) NOT LIKE '%cancel%'
    """, (flight_date, departure_time))
    row = cur.fetchone()
    return int(row["cnt"] or 0)

def col_labels(n: int):
    letters = list(string.ascii_uppercase)
    return letters[:n]


@app.route("/flights", methods=["GET"])
def flights():
    flight_date = request.args.get("flight_date", "").strip()          # YYYY-MM-DD
    dep = request.args.get("departure_airport", "").strip().upper()    # TLV
    dest = request.args.get("destination_airport", "").strip().upper() # ATH

    # מציגים רק active וגם רק לא מלאות
    sql = """
        SELECT
            f.Flight_Date, f.Departure_Time, f.Landing_Time,
            f.Departure_Airport, f.Destination_Airport, f.Plane_ID, f.status,
            cap.capacity AS capacity,
            COALESCE(sold.sold_count, 0) AS sold_count
        FROM flights f

        -- capacity לפי Plane_ID מתוך classes
        JOIN (
            SELECT Plane_ID, SUM(Number_of_Rows * Number_of_Columns) AS capacity
            FROM classes
            GROUP BY Plane_ID
        ) cap ON cap.Plane_ID = f.Plane_ID

        -- כמה נמכר בפועל לכל טיסה (לא cancelled)
        LEFT JOIN (
            SELECT
                t.flight_date,
                t.departure_time,
                COUNT(*) AS sold_count
            FROM tickets t
            JOIN bookings b ON b.booking_code = t.booking_code
            WHERE LOWER(b.status) NOT LIKE '%cancel%'
            GROUP BY t.flight_date, t.departure_time
        ) sold
          ON sold.flight_date = f.Flight_Date
         AND sold.departure_time = f.Departure_Time

        WHERE f.status = 'active'
          AND COALESCE(sold.sold_count, 0) < cap.capacity
    """
    params = []

    if flight_date:
        sql += " AND f.Flight_Date = %s"
        params.append(flight_date)

    if dep:
        sql += " AND f.Departure_Airport = %s"
        params.append(dep)

    if dest:
        sql += " AND f.Destination_Airport = %s"
        params.append(dest)

    sql += " ORDER BY f.Flight_Date, f.Departure_Time"

    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)
    cur.execute(sql, params)
    flights_rows = cur.fetchall()
    cur.close()

    return render_template(
        "flights.html",
        flights=flights_rows,
        flight_date=flight_date,
        departure_airport=dep,
        destination_airport=dest
    )


@app.route("/seats")
def seats():
    flight_date = request.args.get("flight_date")
    departure_time = request.args.get("departure_time")

    if not flight_date or not departure_time:
        return "Missing flight info", 400

    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)

    # 1) שליפת טיסה
    cur.execute("""
        SELECT Plane_ID, Departure_Airport, Destination_Airport
        FROM flights
        WHERE Flight_Date = %s AND Departure_Time = %s
        LIMIT 1
    """, (flight_date, departure_time))
    flight = cur.fetchone()

    if not flight:
        cur.close()
        return "Flight not found", 404

    plane_id = flight["Plane_ID"]

    # 2) מחלקות (Business ואז Economy)
    cur.execute("""
        SELECT Class_Type, Number_of_Rows, Number_of_Columns
        FROM classes
        WHERE Plane_ID = %s
        ORDER BY
          CASE
            WHEN Class_Type = 'Business' THEN 1
            WHEN Class_Type = 'Economy' THEN 2
            ELSE 99
          END
    """, (plane_id,))
    classes = cur.fetchall()

    # אם אין classes בכלל — לא מאפשרים להזמין
    if not classes:
        cur.close()
        return render_template(
            "seats.html",
            sections=[],
            flight=flight,
            flight_date=flight_date,
            departure_time=departure_time,
            message="This flight has no seating configuration."
        )

    capacity = _flight_capacity_for_plane(classes)

    # 3) מושבים שנמכרו (לא cancelled)
    cur.execute("""
        SELECT t.`row`, t.`col`
        FROM tickets t
        JOIN bookings b ON b.booking_code = t.booking_code
        WHERE t.flight_date = %s
          AND t.departure_time = %s
          AND LOWER(b.status) NOT LIKE '%cancel%'
    """, (flight_date, departure_time))
    sold_set = {(r["row"], r["col"]) for r in cur.fetchall()}

    # ✅ אם הטיסה מלאה — מציגים הודעה ולא מאפשרים להמשיך
    # (עדיין יראו את המפה כדי להבין שהיא מלאה, אבל בפועל הכל יהיה sold)
    is_full = (len(sold_set) >= capacity)
    if is_full:
        # נהפוך את כל המושבים ל-"sold" כדי שלא יוכלו לבחור
        sold_set = set()
        offset_tmp = 0
        for c in classes:
            rows = int(c["Number_of_Rows"])
            cols = int(c["Number_of_Columns"])
            start_row = offset_tmp + 1
            end_row = offset_tmp + rows
            for r in range(start_row, end_row + 1):
                for col_i in range(1, cols + 1):
                    sold_set.add((r, col_i))
            offset_tmp += rows

    cur.close()

    # 4) בניית המפה עם מספור רציף
    sections = []
    offset = 0

    for c in classes:
        class_type = c["Class_Type"]
        rows = int(c["Number_of_Rows"])
        cols = int(c["Number_of_Columns"])
        labels = [chr(ord('A') + i) for i in range(cols)]

        start_row = offset + 1
        end_row = offset + rows

        grid = []
        for r in range(start_row, end_row + 1):
            row_seats = []
            for col_i in range(1, cols + 1):
                row_seats.append({
                    "row": r,
                    "col": col_i,
                    "label": labels[col_i - 1],
                    "sold": (r, col_i) in sold_set
                })
            grid.append({"row": r, "seats": row_seats})

        sections.append({
            "class_type": class_type,
            "col_labels": labels,
            "grid": grid
        })

        offset += rows

    return render_template(
        "seats.html",
        sections=sections,
        flight=flight,
        flight_date=flight_date,
        departure_time=departure_time,
        message=("This flight is full. You can’t book tickets for it." if is_full else "")
    )


def seat_to_row_col(seat_code: str):
    m = re.match(r"^(\d+)([A-Z])$", (seat_code or "").strip().upper())
    if not m:
        return None
    row = int(m.group(1))
    col = ord(m.group(2)) - ord('A') + 1
    return row, col

@app.route("/order/new", methods=["GET"])
def order_new():
    flight_date = request.args.get("flight_date", "").strip()
    departure_time = request.args.get("departure_time", "").strip()
    if not flight_date or not departure_time:
        return "Missing flight_date or departure_time", 400

    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)

    # flight + plane
    cur.execute("""
        SELECT Plane_ID, Departure_Airport, Destination_Airport, status
        FROM flights
        WHERE Flight_Date=%s AND Departure_Time=%s
        LIMIT 1
    """, (flight_date, departure_time))
    flight = cur.fetchone()
    if not flight:
        cur.close()
        return "Flight not found", 404
    plane_id = flight["Plane_ID"]

    # classes ordered Business -> Economy
    cur.execute("""
        SELECT Class_Type, Number_of_Rows, Number_of_Columns
        FROM classes
        WHERE Plane_ID=%s
        ORDER BY CASE
          WHEN Class_Type='Business' THEN 1
          WHEN Class_Type='Economy' THEN 2
          ELSE 3 END
    """, (plane_id,))
    classes = cur.fetchall()

    # sold seats (ignore cancelled)
    cur.execute("""
        SELECT t.`row`, t.`col`
        FROM tickets t
        JOIN bookings b ON b.booking_code = t.booking_code
        WHERE t.flight_date = %s
          AND t.departure_time = %s
          AND LOWER(b.status) NOT LIKE '%cancel%'
    """, (flight_date, departure_time))

    sold_set = {(x["row"], x["col"]) for x in cur.fetchall()}
    cur.close()

    # build sections with continuous rows across classes

    def col_labels(n): return list(string.ascii_uppercase)[:n]

    sections = []
    offset = 0
    total_seats = 0
    sold_count = 0

    for c in classes:
        r = int(c["Number_of_Rows"])
        k = int(c["Number_of_Columns"])
        labels = col_labels(k)

        start_row = offset + 1
        end_row = offset + r

        sector = {"class_type": c["Class_Type"], "col_labels": labels, "grid": []}

        for row_i in range(start_row, end_row + 1):
            row_seats = []
            for col_i in range(1, k + 1):
                row_seats.append({
                    "row": row_i,
                    "col": col_i,
                    "label": labels[col_i - 1],
                    "sold": (row_i, col_i) in sold_set
                })
            sector["grid"].append({"row": row_i, "seats": row_seats})

        sections.append(sector)
        offset += r
        total_seats += r * k
        sold_count += sum(1 for (rr, cc) in sold_set if start_row <= rr <= end_row and 1 <= cc <= k)

    available = total_seats - sold_count

    return render_template(
        "seats_select.html",
        flight_date=flight_date,
        departure_time=departure_time,
        flight=flight,
        plane_id=plane_id,
        sections=sections,
        available=available,
        message=""
    )
def seat_to_row_col(seat_code: str):
    m = re.match(r"^(\d+)([A-Z])$", seat_code.strip().upper())
    if not m:
        return None
    row = int(m.group(1))
    col = ord(m.group(2)) - ord('A') + 1
    return row, col

def generate_booking_code(cur):
    # booking_code אצלך INT => נייצר 6 ספרות שלא קיימות
    ensure_mydb_is_connected()
    while True:
        code = random.randint(100000, 999999)
        cur.execute("SELECT 1 FROM bookings WHERE booking_code=%s LIMIT 1", (code,))
        if not cur.fetchone():
            return code

def get_class_ranges(cur, plane_id):
    # מחזיר טווחי שורות רציפים לכל מחלקה (Business ואז Economy)
    ensure_mydb_is_connected()
    cur.execute("""
        SELECT Class_Type, Number_of_Rows, Number_of_Columns
        FROM classes
        WHERE Plane_ID=%s
        ORDER BY CASE
          WHEN Class_Type='Business' THEN 1
          WHEN Class_Type='Economy' THEN 2
          ELSE 3 END
    """, (plane_id,))
    classes = cur.fetchall()

    ranges = []  # [{"class":"Business","start":1,"end":6,"cols":4}, ...]
    offset = 0
    for c in classes:
        rows = int(c["Number_of_Rows"])
        cols = int(c["Number_of_Columns"])
        start = offset + 1
        end = offset + rows
        ranges.append({"class": c["Class_Type"], "start": start, "end": end, "cols": cols})
        offset += rows
    return ranges

def class_for_row(ranges, row):
    for rg in ranges:
        if rg["start"] <= row <= rg["end"]:
            return rg["class"]
    return None

# ---------- Flask: /order/preview (UPDATED - unified form for ALL users + prefill) ----------
# ---------- Flask: /order/preview (FULL UPDATED per your rules) ----------
@app.route("/order/preview", methods=["GET", "POST"])
def order_preview():
    flight_date = request.form.get("flight_date", "").strip()
    departure_time = request.form.get("departure_time", "").strip()
    selected = request.form.get("selected_seats", "").strip()

    if not flight_date or not departure_time:
        return "Missing flight info", 400

    # אם לא בחרו מושב -> חוזרים לעמוד ההושבה עם הודעה (לא 400)
    if not selected:
        return redirect(f"/seats?flight_date={flight_date}&departure_time={departure_time}&message=Please+select+at+least+one+seat")

    # מי הלקוח?
    email = session.get("username")
    if not email:
        email = request.form.get("guest_email", "").strip()
        if not email:
            return "Missing email", 400

    if not session.get("username"):
        session["guest_email"] = email

    seat_codes = [x.strip().upper() for x in selected.split(",") if x.strip()]
    seats = []
    for code in seat_codes:
        rc = seat_to_row_col(code)
        if rc is None:
            return f"Bad seat code: {code}", 400
        seats.append(rc)  # (row,col)

    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)

    # flight + plane
    cur.execute("""
        SELECT Plane_ID, Departure_Airport, Destination_Airport, status
        FROM flights
        WHERE Flight_Date=%s AND Departure_Time=%s
        LIMIT 1
    """, (flight_date, departure_time))
    flight = cur.fetchone()
    if not flight:
        cur.close()
        return "Flight not found", 404

    plane_id = flight["Plane_ID"]
    ranges = get_class_ranges(cur, plane_id)

    # בדיקת תפוסה בזמן preview
    cur.execute("""
        SELECT t.`row`, t.`col`
        FROM tickets t
        JOIN bookings b ON b.booking_code = t.booking_code
        WHERE t.flight_date = %s
          AND t.departure_time = %s
          AND LOWER(b.status) NOT LIKE '%cancel%'
    """, (flight_date, departure_time))
    sold_set = {(x["row"], x["col"]) for x in cur.fetchall()}

    for (r, c) in seats:
        if (r, c) in sold_set:
            cur.close()
            return f"Seat already taken: {r},{c}", 400

    # ✅ האם רשום
    cur.execute("SELECT 1 FROM registered_customers WHERE email=%s LIMIT 1", (email,))
    is_registered = cur.fetchone() is not None

    # ✅ ברירת מחדל: כולם ממלאים לבד
    customer_fname = ""
    customer_lname = ""
    customer_passport_number = ""
    customer_date_of_birth = ""   # string ל-input type="date" (YYYY-MM-DD)
    phones = [""]

    # ✅ אם רשום: prefill
    if is_registered:
        cur.execute("""
            SELECT fname, lname, passport, date_of_birth
            FROM registered_customers
            WHERE email=%s
            LIMIT 1
        """, (email,))
        row = cur.fetchone() or {}

        customer_fname = (row.get("fname") or "").strip()
        customer_lname = (row.get("lname") or "").strip()
        customer_passport_number = (row.get("passport") or "").strip()

        dob = row.get("date_of_birth")
        # dob יכול להגיע כ-date או כ-str
        if dob is None:
            customer_date_of_birth = ""
        elif isinstance(dob, date):
            customer_date_of_birth = dob.strftime("%Y-%m-%d")
        else:
            customer_date_of_birth = str(dob)[:10]  # "YYYY-MM-DD..."

        # phones from phone_numbers(email, phone_number)
        cur.execute("""
            SELECT phone_number
            FROM phone_numbers
            WHERE email=%s
            ORDER BY phone_number
        """, (email,))
        tmp = []
        for r in cur.fetchall():
            p = r.get("phone_number")
            if isinstance(p, (bytes, bytearray)):
                p = p.decode("utf-8", errors="ignore")
            p = (p or "").strip()
            if p:
                tmp.append(p)
        phones = tmp if tmp else [""]

    # תמחור: Business=200, Economy=100
    seat_items = []
    total_price = 0
    for (r, c) in seats:
        cls = class_for_row(ranges, r)
        price = 200 if cls == "Business" else 100
        total_price += price
        seat_items.append({
            "seat": f"{r}{chr(ord('A') + c - 1)}",
            "row": r,
            "col": c,
            "class": cls,
            "price": price
        })

    # קוד הזמנה
    cur2 = mydb.cursor()
    booking_code = generate_booking_code(cur2)
    cur2.close()
    cur.close()

    session["pending_order"] = {
        "booking_code": booking_code,
        "email": email,
        "flight_date": flight_date,
        "departure_time": departure_time,
        "seats": [(r, c) for (r, c) in seats],
        "total_price": total_price
    }

    return render_template(
        "order_preview.html",
        order_code=booking_code,
        email=email,
        flight=flight,
        flight_date=flight_date,
        departure_time=departure_time,
        seat_items=seat_items,
        total_price=total_price,

        is_registered=is_registered,
        customer_fname=customer_fname,
        customer_lname=customer_lname,
        customer_passport_number=customer_passport_number,
        customer_date_of_birth=customer_date_of_birth,
        phones=phones
    )


@app.route("/order/confirm", methods=["POST"])
def order_confirm():
    pending = session.get("pending_order")
    if not pending:
        return "No pending order", 400

    booking_code = pending["booking_code"]
    email = pending["email"]
    flight_date = pending["flight_date"]
    departure_time = pending["departure_time"]
    seats = pending["seats"]
    total_price = pending["total_price"]

    # פרטי אורח (אם צריך)
    fname = request.form.get("fname", "").strip()
    lname = request.form.get("lname", "").strip()
    phones = request.form.getlist("phone")

    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)

    try:
        mydb.start_transaction()

        # בדיקה האם הלקוח רשום
        cur.execute(
            "SELECT 1 FROM registered_customers WHERE email=%s LIMIT 1",
            (email,)
        )
        is_registered = cur.fetchone() is not None

        # בדיקה האם אורח קיים
        cur.execute(
            "SELECT 1 FROM unregistered_customers WHERE email=%s LIMIT 1",
            (email,)
        )
        is_unregistered = cur.fetchone() is not None

        # אם לא רשום ולא אורח – ניצור unregistered_customer
        if not is_registered and not is_unregistered:
            if not fname or not lname or not phones:
                mydb.rollback()
                cur.close()
                return "Missing guest details", 400

            cur.execute("""
                INSERT INTO unregistered_customers (email, fname, lname)
                VALUES (%s,%s,%s)
            """, (email, fname, lname))

            for phone in phones:
                cur.execute("""
                    INSERT INTO phone_numbers (email, phone_number)
                    VALUES (%s,%s)
                """, (email, phone))

            is_unregistered = True

        # בדיקת תפוסה מחדש
        cur.execute("""
            SELECT t.`row`, t.`col`
            FROM tickets t
            JOIN bookings b ON b.booking_code = t.booking_code
            WHERE t.flight_date = %s
              AND t.departure_time = %s
              AND LOWER(b.status) NOT LIKE '%cancel%'
        """, (flight_date, departure_time))

        sold_set = {(x["row"], x["col"]) for x in cur.fetchall()}

        for (r, c) in seats:
            if (r, c) in sold_set:
                raise ValueError(f"Seat already taken: {r},{c}")

        # הכנסת booking – לפי סוג לקוח
        if is_registered:
            cur.execute("""
                INSERT INTO bookings
                (booking_code, registered_email, unregistered_email, status, total_price)
                VALUES (%s,%s,NULL,%s,%s)
            """, (booking_code, email, "paid", total_price))
        else:
            cur.execute("""
                INSERT INTO bookings
                (booking_code, registered_email, unregistered_email, status, total_price)
                VALUES (%s,NULL,%s,%s,%s)
            """, (booking_code, email, "paid", total_price))

        # הכנסת כרטיסים
        for (r, c) in seats:
            cur.execute("""
                INSERT INTO tickets (`row`, `col`, booking_code, flight_date, departure_time)
                VALUES (%s,%s,%s,%s,%s)
            """, (r, c, booking_code, flight_date, departure_time))

        mydb.commit()
        cur.close()

        session.pop("pending_order", None)
        return redirect(f"/order/success?code={booking_code}")

    except Exception as e:
        mydb.rollback()
        cur.close()
        return f"order failed: {e}", 400



@app.route("/order/success")
def order_success():
    code = request.args.get("code")
    return render_template("order_success.html", code=code)


@app.route("/my_booking", methods=["GET"])
def my_bookings():
    booking_code = (request.args.get("booking_code") or "").strip()

    # ----- חיפוש לפי קוד הזמנה -----
    if booking_code:
        if not booking_code.isdigit():
            return render_template(
                "my_booking.html",
                email="",
                upcoming=[],
                history=[],
                single_booking=None,
                message="Booking code must be a number.",
                is_registered=False,
                selected_status="",
                all_statuses=[]
            )

        ensure_mydb_is_connected()
        cur = mydb.cursor(dictionary=True)

        cur.execute("""
            SELECT
                b.booking_code,
                b.status,
                b.total_price,
                b.registered_email,
                b.unregistered_email,
                f.Flight_Date,
                f.Departure_Time,
                f.Landing_Time,
                f.Departure_Airport,
                f.Destination_Airport,
                GROUP_CONCAT(CONCAT(t.`row`, CHAR(64 + t.`col`)) ORDER BY t.`row`, t.`col` SEPARATOR ', ') AS seats
            FROM bookings b
            JOIN tickets t
              ON t.booking_code = b.booking_code
            JOIN flights f
              ON f.Flight_Date = t.flight_date
             AND f.Departure_Time = t.departure_time
            WHERE b.booking_code = %s
            GROUP BY
                b.booking_code, b.status, b.total_price, b.registered_email, b.unregistered_email,
                f.Flight_Date, f.Departure_Time, f.Landing_Time,
                f.Departure_Airport, f.Destination_Airport
            LIMIT 1
        """, (int(booking_code),))

        one = cur.fetchone()
        cur.close()

        if not one:
            return render_template(
                "my_booking.html",
                email="",
                upcoming=[],
                history=[],
                single_booking=None,
                message="Booking code not found.",
                is_registered=False,
                selected_status="",
                all_statuses=[]
            )

        seat = one.get("seats", "")
        if isinstance(seat, (bytes, bytearray)):
            seat = seat.decode("utf-8", errors="ignore")
        one["seats"] = seat

        return render_template(
            "my_booking.html",
            email="",
            upcoming=[],
            history=[],
            single_booking=one,
            message="",
            is_registered=False,
            selected_status="",
            all_statuses=[]
        )

    # ----- חיפוש לפי אימייל (משתמש מחובר / אורח / שדה חיפוש) -----
    email = (
        session.get("username")
        or session.get("guest_email")
        or (request.args.get("email") or "").strip()
    )

    if not email:
        return render_template(
            "my_booking.html",
            email="",
            upcoming=[],
            history=[],
            single_booking=None,
            message="",
            is_registered=False,
            selected_status="",
            all_statuses=[]
        )

    ensure_mydb_is_connected()

    selected_status = (request.args.get("status") or "").strip()

    # משתמש רשום?
    cur0 = mydb.cursor()
    cur0.execute("SELECT 1 FROM registered_customers WHERE email=%s LIMIT 1", (email,))
    is_registered = cur0.fetchone() is not None
    cur0.close()

    # ✅ כל הסטטוסים של הלקוח *לפני* סינון (רק לרשומים)
    all_statuses = []
    if is_registered:
        curS = mydb.cursor()
        curS.execute("""
            SELECT DISTINCT b.status
            FROM bookings b
            WHERE b.registered_email = %s OR b.unregistered_email = %s
        """, (email, email))  # ✅ שני פרמטרים
        raw = curS.fetchall()
        curS.close()

        tmp = []
        for row in raw:
            st = row[0]
            if isinstance(st, (bytes, bytearray)):
                st = st.decode("utf-8", errors="ignore")
            st = (st or "").strip()
            if st:
                tmp.append(st)

        all_statuses = sorted(set(tmp), key=lambda x: x.lower())

    # פילטר סטטוס רק לרשומים
    params = [email, email]  # ✅ תמיד שני פרמטרים ל-WHERE
    status_filter_sql = ""
    if is_registered and selected_status:
        status_filter_sql = " AND b.status = %s "
        params.append(selected_status)

    # ✅ אם לא רשום — אל תשלוף טיסות עבר בכלל (אין היסטוריה)
    time_filter_sql = ""
    if not is_registered:
        time_filter_sql = " AND TIMESTAMP(f.Flight_Date, f.Departure_Time) >= NOW() "

    cur = mydb.cursor(dictionary=True)
    cur.execute(f"""
        SELECT
            b.booking_code,
            b.status,
            b.total_price,
            b.registered_email,
            b.unregistered_email,
            f.Flight_Date,
            f.Departure_Time,
            f.Landing_Time,
            f.Departure_Airport,
            f.Destination_Airport,
            GROUP_CONCAT(CONCAT(t.`row`, CHAR(64 + t.`col`)) ORDER BY t.`row`, t.`col` SEPARATOR ', ') AS seats
        FROM bookings b
        JOIN tickets t
          ON t.booking_code = b.booking_code
        JOIN flights f
          ON f.Flight_Date = t.flight_date
         AND f.Departure_Time = t.departure_time
        WHERE b.registered_email = %s OR b.unregistered_email = %s
        {status_filter_sql}
        {time_filter_sql}
        GROUP BY
            b.booking_code, b.status, b.total_price, b.registered_email, b.unregistered_email,
            f.Flight_Date, f.Departure_Time, f.Landing_Time,
            f.Departure_Airport, f.Destination_Airport
        ORDER BY f.Flight_Date DESC, f.Departure_Time DESC
    """, tuple(params))
    rows = cur.fetchall()
    cur.close()

    now = datetime.now()
    upcoming, history = [], []

    for r in rows:
        seat = r.get("seats", "")
        if isinstance(seat, (bytes, bytearray)):
            seat = seat.decode("utf-8", errors="ignore")
        r["seats"] = seat

        fd = r["Flight_Date"]
        dep = r["Departure_Time"]

        if isinstance(fd, date) and isinstance(dep, time):
            flight_dt = datetime.combine(fd, dep)
        else:
            flight_dt = datetime.strptime(f"{fd} {dep}", "%Y-%m-%d %H:%M:%S")

        if flight_dt >= now:
            upcoming.append(r)
        else:
            history.append(r)

    # ✅ הגנה נוספת: אורח לא רואה היסטוריה
    if not is_registered:
        history = []

    return render_template(
        "my_booking.html",
        email=email,
        upcoming=upcoming,
        history=history,
        single_booking=None,
        message="",
        is_registered=is_registered,
        selected_status=selected_status,
        all_statuses=all_statuses
    )


@app.route("/booking/cancel", methods=["POST"])
def booking_cancel():
    booking_code = (request.form.get("booking_code") or "").strip()
    page_email = (request.form.get("email") or "").strip()

    if not booking_code or not page_email:
        return "Missing booking_code or email", 400

    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)

    try:
        mydb.start_transaction()

        # ✅ לוודא שההזמנה קיימת + להביא את האימייל ששייך להזמנה (לפי הסכמה החדשה)
        cur.execute("""
            SELECT booking_code,
                   registered_email,
                   unregistered_email,
                   status,
                   total_price
            FROM bookings
            WHERE booking_code = %s
            LIMIT 1
        """, (booking_code,))
        b = cur.fetchone()
        if not b:
            mydb.rollback()
            cur.close()
            return "Booking not found", 404

        booking_email = (b.get("registered_email") or b.get("unregistered_email") or "").strip()

        # ✅ בדיקת בעלות מול האימייל שמוצג בדף
        if booking_email.lower() != page_email.strip().lower():
            mydb.rollback()
            cur.close()
            return "Not allowed", 403

        # אם כבר בוטלה
        status_lower = (b.get("status") or "").strip().lower()
        if status_lower.startswith("cancel") or status_lower.endswith("cancelled") or "cancel" in status_lower:
            mydb.rollback()
            cur.close()
            return redirect(f"/my_booking?email={page_email}")

        # להביא תאריך/שעת הטיסה מהכרטיסים
        cur.execute("""
            SELECT f.Flight_Date, f.Departure_Time
            FROM tickets t
            JOIN flights f
              ON f.Flight_Date = t.flight_date
             AND f.Departure_Time = t.departure_time
            WHERE t.booking_code = %s
            LIMIT 1
        """, (booking_code,))
        ft = cur.fetchone()
        if not ft:
            mydb.rollback()
            cur.close()
            return "No flight found for this booking", 400

        fd = ft["Flight_Date"]
        dep = ft["Departure_Time"]

        # normalize date
        if not isinstance(fd, date):
            fd = datetime.strptime(str(fd)[:10], "%Y-%m-%d").date()

        # normalize time
        if isinstance(dep, timedelta):
            dep = (datetime.min + dep).time()
        elif not isinstance(dep, time):
            dep = datetime.strptime(str(dep).split(".")[0], "%H:%M:%S").time()

        flight_dt = datetime.combine(fd, dep)
        now = datetime.now()
        hours_left = (flight_dt - now).total_seconds() / 3600.0

        original_total = float(b.get("total_price") or 0)

        if hours_left > 36:
            fee = round(original_total * 0.05, 2)  # דמי ביטול = 5%
            cur.execute("""
                UPDATE bookings
                SET status = %s, total_price = %s
                WHERE booking_code = %s
            """, ("customer cancelled", fee, booking_code))
        else:
            cur.execute("""
                UPDATE bookings
                SET status = %s
                WHERE booking_code = %s
            """, ("customer cancelled", booking_code))

        mydb.commit()
        cur.close()

        return redirect(f"/my_booking?email={page_email}")

    except Exception as e:
        mydb.rollback()
        cur.close()
        return f"cancel failed: {e}", 400

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        if (session.get("admin_id") or session.get("admin_name")) and session.get("role") != "admin":
            session.clear()
        if session.get("role") == "admin" and not session.get("admin_id"):
            session.clear()
        return render_template("admin_login.html", message="")   # ✅ חייב להיות פה

    # POST
    admin_id = (request.form.get("admin_id") or "").strip()
    pw = (request.form.get("password") or "").strip()

    if not admin_id.isdigit():
        return render_template("admin_login.html", message="ID must be a number")

    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)
    cur.execute("""
        SELECT ID, fname, lname, password
        FROM admin
        WHERE ID = %s
        LIMIT 1
    """, (int(admin_id),))
    row = cur.fetchone()
    cur.close()

    if not row:
        return render_template("admin_login.html", message="Admin not found")

    if (row.get("password") or "") != pw:
        return render_template("admin_login.html", message="Wrong password")

    session.clear()
    session["role"] = "admin"
    session["admin_id"] = row["ID"]
    session["admin_name"] = f'{row["fname"]} {row["lname"]}'

    return redirect("/admin_dashboard")  # ✅ רק אחרי הצלחה

@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return render_template("Homepage.html")


@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/admin_login")

    # ✅ status filter (GET param)
    selected_status = (request.args.get("status", "all") or "all").strip()

    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)

    # ✅ בונים SQL דינמי + פרמטרים
    sql = """
        SELECT Flight_Date, Departure_Time, Landing_Time,
               Departure_Airport, Destination_Airport, Plane_ID, status
        FROM flights
    """
    params = []

    if selected_status.lower() != "all":
        sql += " WHERE status = %s "
        params.append(selected_status)

    sql += " ORDER BY Flight_Date DESC, Departure_Time DESC "

    cur.execute(sql, params)
    flights_rows = cur.fetchall()
    cur.close()

    now = datetime.now()
    flights_view = []

    for f in flights_rows:
        fd = f["Flight_Date"]
        dt = f["Departure_Time"]

        # normalize to datetime
        if not isinstance(fd, date):
            fd = datetime.strptime(str(fd)[:10], "%Y-%m-%d").date()
        if not isinstance(dt, time):
            dt = datetime.strptime(str(dt).split(".")[0], "%H:%M:%S").time()

        flight_dt = datetime.combine(fd, dt)
        hours_left = (flight_dt - now).total_seconds() / 3600.0

        status_lower = (f["status"] or "").strip().lower()

        can_cancel = (
            flight_dt > now and
            hours_left > 72 and
            ("cancel" not in status_lower) and
            (status_lower != "completed")
        )

        f["can_cancel"] = can_cancel
        f["hours_left"] = round(hours_left, 1)
        flights_view.append(f)

    # ✅ אם בא לך שה-dropdown יציג רק סטטוסים שקיימים בפועל:
    # (אפשר גם להחליף לרשימה קבועה אם יש לכם סטטוסים ידועים)
    cur2 = mydb.cursor()
    cur2.execute("SELECT DISTINCT status FROM flights ORDER BY status")
    statuses = [row[0] for row in cur2.fetchall() if row[0] is not None and str(row[0]).strip() != ""]
    cur2.close()

    return render_template(
        "admin_dashboard.html",
        admin_name=session.get("admin_name", "Admin"),
        flights=flights_view,
        statuses=statuses,
        selected_status=selected_status
    )


def add_flight_with_rules(mydb, flight_date, departure_time, plane_id, landing_time, dep_airport, dest_airport, status="active"):
    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)
    try:
        # build a flight_row-like dict for validation
        flight_row = {
            "flight_date": flight_date,
            "departure_time": departure_time,
            "plane_id": int(plane_id),
            "landing_time": landing_time,
            "dep_airport": dep_airport,
            "dest_airport": dest_airport,
            "status": status
        }

        # enforce long-flight rule vs plane size
        validate_long_flight_plane_size(cur, flight_row)

        # ----------- התוספת שדיברנו עליה עכשיו -----------
        ok, msg = can_use_plane(cur, flight_row, int(plane_id))
        if not ok:
            return False, msg
        # ---------------------------------------------------

        cur.execute("""
            INSERT INTO `flights`
            (`flight_date`, `departure_time`, `Plane_ID`, `Landing_Time`,
             `Departure_Airport`, `Destination_Airport`, `status`)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (flight_date, departure_time, int(plane_id),
              landing_time if landing_time else None,
              dep_airport, dest_airport, status))

        mydb.commit()
        return True, ""
    except Exception as e:
        mydb.rollback()
        return False, str(e)
    finally:
        cur.close()


def assign_staff_to_flight_with_rules(mydb, flight_date, departure_time, plane_id, staff_id):
    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)
    try:
        flight_row = fetch_flight(cur, flight_date, departure_time, plane_id)
        if not flight_row:
            return False, "Flight not found"

        ok, msg = can_assign_staff(cur, flight_row, int(staff_id))
        if not ok:
            return False, msg

        # prevent duplicate assignment (optional but recommended)
        cur.execute("""
            SELECT 1 FROM `staff_on_flight`
            WHERE `flight_date`=%s AND `departure_time`=%s AND `plane_ID`=%s AND `ID`=%s
            LIMIT 1
        """, (flight_date, departure_time, int(plane_id), int(staff_id)))
        if cur.fetchone():
            return False, "Staff already assigned to this flight"

        cur.execute("""
            INSERT INTO `staff_on_flight` (`flight_date`, `departure_time`, `plane_ID`, `ID`)
            VALUES (%s,%s,%s,%s)
        """, (flight_date, departure_time, int(plane_id), int(staff_id)))

        mydb.commit()
        return True, ""
    except Exception as e:
        mydb.rollback()
        return False, str(e)
    finally:
        cur.close()
def lock_booking_price_after_tickets(mydb, booking_code, flight_date, departure_time, plane_id, base_per_hour=120.0):
    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)
    try:
        total = lock_total_price_at_booking_time(
            cur,
            int(booking_code),
            flight_date,
            departure_time,
            int(plane_id),
            base_per_hour=float(base_per_hour)
        )
        mydb.commit()
        return True, total
    except Exception as e:
        mydb.rollback()
        return False, str(e)
    finally:
        cur.close()

@app.route("/admin_cancel_flight", methods=["POST"])
def admin_cancel_flight():
    if not session.get("admin_id"):
        return redirect("/admin_login")

    flight_date = (request.form.get("flight_date") or "").strip()
    departure_time = (request.form.get("departure_time") or "").strip()
    if len(departure_time) == 5:
        departure_time += ":00"

    if not flight_date or not departure_time:
        return "Missing flight_date or departure_time", 400

    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)
    try:
        mydb.start_transaction()

        cur.execute("""
            SELECT Flight_Date, Departure_Time, status
            FROM flights
            WHERE Flight_Date=%s AND Departure_Time=%s
            LIMIT 1
        """, (flight_date, departure_time))
        f = cur.fetchone()
        if not f:
            mydb.rollback()
            cur.close()
            return "Flight not found", 404

        # eligibility check (72h+ and future)
        fd = f["Flight_Date"]
        dt = f["Departure_Time"]

        if not isinstance(fd, date):
            fd = datetime.strptime(str(fd)[:10], "%Y-%m-%d").date()
        if not isinstance(dt, time):
            dt = datetime.strptime(str(dt).split(".")[0], "%H:%M:%S").time()

        flight_dt = datetime.combine(fd, dt)
        now = datetime.now()
        hours_left = (flight_dt - now).total_seconds() / 3600.0

        status_lower = (f["status"] or "").strip().lower()
        if not (flight_dt > now and hours_left > 72 and ("cancel" not in status_lower) and status_lower != "completed"):
            mydb.rollback()
            cur.close()
            return "Not allowed: can cancel only if flight is future and >72h left", 400

        # 1) cancel the flight
        cur.execute("""
            UPDATE flights
            SET status='cancelled'
            WHERE Flight_Date=%s AND Departure_Time=%s
        """, (flight_date, departure_time))

        #  refund & mark bookings as admin cancelled (for bookings connected to this flight via tickets)
        cur.execute("""
            UPDATE bookings b
            JOIN (
                SELECT DISTINCT booking_code
                FROM tickets
                WHERE flight_date=%s AND departure_time=%s
            ) x ON x.booking_code = b.booking_code
            SET b.status = 'flyTAU cancelled',
                b.total_price = 0.00
            WHERE LOWER(b.status) NOT LIKE '%cancel%'
              AND LOWER(b.status) <> 'completed'
        """, (flight_date, departure_time))

        #  free staff: remove assignments for this flight
        cur.execute("""
            DELETE FROM staff_on_flight
            WHERE flight_date=%s AND departure_time=%s
        """, (flight_date, departure_time))

        mydb.commit()
        cur.close()
        return redirect("/admin_dashboard")

    except Exception as e:
        mydb.rollback()
        cur.close()
        return f"Cancel failed: {e}", 400


def insert_plane_to_db(plane_id, manufacturer, size, purchase_date):
    """
    מכניס מטוס לטבלה plane.
    אם plane_id ריק/None -> מכניס בלי ID (רק אם בעמודה ID מוגדר AUTO_INCREMENT).
    """
    manufacturer = (manufacturer or "").strip()
    size = (size or "").strip()
    purchase_date = (purchase_date or "").strip()

    if not manufacturer or not size or not purchase_date:
        raise ValueError("Missing required plane fields.")

    cursor = mydb.cursor()

    # אם המשתמש נתן ID — נכניס עם ID
    if plane_id is not None and str(plane_id).strip() != "":
        sql = """
            INSERT INTO plane (ID, Manufacturer, Size, Purchase_Date)
            VALUES (%s, %s, %s, %s)
        """
        params = (int(plane_id), manufacturer, size, purchase_date)
    else:
        # בלי ID (מתאים רק אם ID הוא AUTO_INCREMENT)
        sql = """
            INSERT INTO plane (Manufacturer, Size, Purchase_Date)
            VALUES (%s, %s, %s)
        """
        params = (manufacturer, size, purchase_date)

    cursor.execute(sql, params)
    cursor.close()

@app.route("/admin_add_plane", methods=["GET", "POST"])
def admin_add_plane():
    if session.get("role") != "admin":
        return redirect("/admin_login")

    if request.method == "GET":
        return render_template("admin_add_plane.html")

    # ---------- POST ----------
    plane_id = (request.form.get("plane_id") or "").strip()
    manufacturer = (request.form.get("manufacturer") or "").strip()
    size = (request.form.get("size") or "").strip()
    purchase_date = (request.form.get("purchase_date") or "").strip()  # YYYY-MM-DD

    eco_rows = (request.form.get("eco_rows") or "").strip()
    eco_cols = (request.form.get("eco_cols") or "").strip()
    biz_rows = (request.form.get("biz_rows") or "").strip()
    biz_cols = (request.form.get("biz_cols") or "").strip()

    try:
        if not plane_id.isdigit():
            raise ValueError("Plane ID must be a number.")
        plane_id_val = int(plane_id)

        if size not in ("Small", "Large"):
            raise ValueError("Size must be Small or Large.")

        if not eco_rows.isdigit() or int(eco_rows) <= 0:
            raise ValueError("Economy rows must be a positive number.")
        if not eco_cols.isdigit() or int(eco_cols) <= 0:
            raise ValueError("Economy columns must be a positive number.")

        eco_rows_val = int(eco_rows)
        eco_cols_val = int(eco_cols)

        if size == "Large":
            if not biz_rows.isdigit() or int(biz_rows) <= 0:
                raise ValueError("Business rows must be a positive number for Large planes.")
            if not biz_cols.isdigit() or int(biz_cols) <= 0:
                raise ValueError("Business columns must be a positive number for Large planes.")
            biz_rows_val = int(biz_rows)
            biz_cols_val = int(biz_cols)
        else:
            biz_rows_val = None
            biz_cols_val = None

        ensure_mydb_is_connected()
        cur = mydb.cursor()

        # 1) insert plane
        cur.execute("""
            INSERT INTO plane (ID, Manufacturer, Size, Purchase_Date)
            VALUES (%s, %s, %s, %s)
        """, (plane_id_val, manufacturer, size, purchase_date))

        # 2) insert classes
        # תמיד Economy
        cur.execute("""
            INSERT INTO classes (Plane_ID, Class_Type, Number_of_Rows, Number_of_Columns)
            VALUES (%s, 'Economy', %s, %s)
        """, (plane_id_val, eco_rows_val, eco_cols_val))

        # אם Large אז גם Business
        if size == "Large":
            cur.execute("""
                INSERT INTO classes (Plane_ID, Class_Type, Number_of_Rows, Number_of_Columns)
                VALUES (%s, 'Business', %s, %s)
            """, (plane_id_val, biz_rows_val, biz_cols_val))

        mydb.commit()
        cur.close()

        return render_template("admin_add_plane.html", success="Plane and classes added successfully!")

    except mysql.connector.Error as e:
        try:
            mydb.rollback()
        except Exception:
            pass
        return render_template("admin_add_plane.html", error=f"Database error: {e}")

    except ValueError as e:
        try:
            mydb.rollback()
        except Exception:
            pass
        return render_template("admin_add_plane.html", error=str(e))

    except Exception as e:
        try:
            mydb.rollback()
        except Exception:
            pass
        return render_template("admin_add_plane.html", error=f"Unexpected error: {e}")

# ===== constants =====
ALLOWED_ROLES = {"pilot", "flight_attendant"}
ALLOWED_TRAINING = {"short", "long"}

def insert_crew_member_to_db(role, crew_id, fname, lname, start_date, city, street, house_number, phone, training):
    """
    מכניס איש צוות לטבלה:
    - role='pilot' -> pilot
    - role='flight_attendant' -> flight_attendant
    עמודות לפי התמונות: ID, fname, lname, start_date, city, street, house_number, phone, training
    """
    role = (role or "").strip()
    if role not in ALLOWED_ROLES:
        raise ValueError("Role must be pilot or flight_attendant.")

    training = (training or "").strip()
    if training not in ALLOWED_TRAINING:
        raise ValueError("Training must be short or long.")

    # basic clean
    fname = (fname or "").strip()
    lname = (lname or "").strip()
    start_date = (start_date or "").strip()  # YYYY-MM-DD
    city = (city or "").strip()
    street = (street or "").strip()
    phone = (phone or "").strip()

    if not all([crew_id, fname, lname, start_date, city, street, house_number, phone, training]):
        raise ValueError("Please fill in all fields.")

    table_name = "pilot" if role == "pilot" else "flight_attendant"

    sql = f"""
        INSERT INTO {table_name}
            (ID, fname, lname, start_date, city, street, house_number, phone, training)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    params = (
        int(crew_id),
        fname,
        lname,
        start_date,
        city,
        street,
        int(house_number),
        phone,
        training
    )

    cursor = mydb.cursor()
    cursor.execute(sql, params)
    cursor.close()


@app.route("/admin_add_crew", methods=["GET", "POST"])
def admin_add_crew():
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        crew_id = request.form.get("id", "").strip()
        fname = request.form.get("fname", "").strip()
        lname = request.form.get("lname", "").strip()
        start_date = request.form.get("start_date", "").strip()
        city = request.form.get("city", "").strip()
        street = request.form.get("street", "").strip()
        house_number = request.form.get("house_number", "").strip()
        phone = request.form.get("phone", "").strip()
        training = request.form.get("training", "").strip()

        try:
            insert_crew_member_to_db(
                role=role,
                crew_id=crew_id,
                fname=fname,
                lname=lname,
                start_date=start_date,
                city=city,
                street=street,
                house_number=house_number,
                phone=phone,
                training=training
            )
            return render_template("admin_add_crew.html", success="Crew member added successfully!")
        except mysql.connector.Error as e:
            # למשל Duplicate entry על ID
            return render_template("admin_add_crew.html", error=f"Database error: {e}")
        except ValueError as e:
            return render_template("admin_add_crew.html", error=str(e))

    return render_template("admin_add_crew.html")





@app.route("/admin_add_flight", methods=["GET", "POST"])
def admin_add_flight():
    if session.get("role") != "admin":
        return redirect("/admin_login")

    TEMPLATE = "admin_add_flight.html"  # ✅ אצלכם זה שם הקובץ
    ensure_mydb_is_connected()
    cur = mydb.cursor(dictionary=True)

    # ---------- GET ----------
    if request.method == "GET":
        airports = fetch_airports_from_flight_duration(cur)
        cur.close()
        return render_template(TEMPLATE, airports=airports, step=1)

    step = (request.form.get("step", "1") or "1").strip()

    # =========================================================
    # STEP 1: date/time/route (לא לשנות)
    # =========================================================
    if step == "1":
        try:
            flight_date = _normalize_date(request.form.get("flight_date", "").strip())
            departure_time = _normalize_time(request.form.get("departure_time", "").strip())
            dep_airport = request.form.get("departure_airport", "").strip().upper()
            dest_airport = request.form.get("destination_airport", "").strip().upper()

            landing_time, available_planes, available_pilots, available_attendants = _fetch_available_resources(
                cur, flight_date, departure_time, dep_airport, dest_airport
            )

            MIN_PILOTS = 2
            MIN_ATT = 3

            missing = []
            if len(available_pilots) < MIN_PILOTS:
                missing.append("אין מספיק טייסים")
            if len(available_attendants) < MIN_ATT:
                missing.append("אין מספיק דיילים")

            if missing:
                msg = f"{' ו'.join(missing)} בתאריך/שעה/שדה שבחרת. חזור לdashboard."
                airports = fetch_airports_from_flight_duration(cur)
                cur.close()
                return render_template(
                    TEMPLATE,
                    step=1,
                    error=msg,
                    airports=airports,
                    selected_flight_date=str(flight_date),
                    selected_departure_time=departure_time.strftime("%H:%M"),
                    selected_dep_airport=dep_airport,
                    selected_dest_airport=dest_airport,
                    show_back_only=True
                )

            cur.close()
            return render_template(
                TEMPLATE,
                step=2,
                flight_date=str(flight_date),
                departure_time=departure_time.strftime("%H:%M"),
                departure_airport=dep_airport,
                destination_airport=dest_airport,
                landing_time=landing_time.strftime("%H:%M") if landing_time else None,
                available_planes=available_planes,
                selected_plane_id=""
            )

        except Exception as e:
            airports = fetch_airports_from_flight_duration(cur)
            cur.close()
            return render_template(TEMPLATE, step=1, error=str(e), airports=airports, show_back_only=True)

    # =========================================================
    # STEP 2: choose plane -> proceed to step 3
    # =========================================================
    if step == "2":
        try:
            flight_date = _normalize_date(request.form.get("flight_date", "").strip())
            departure_time = _normalize_time(request.form.get("departure_time", "").strip())
            dep_airport = request.form.get("departure_airport", "").strip().upper()
            dest_airport = request.form.get("destination_airport", "").strip().upper()
            plane_id = (request.form.get("plane_id", "") or "").strip()

            landing_time, available_planes, _, _ = _fetch_available_resources(
                cur, flight_date, departure_time, dep_airport, dest_airport
            )

            if not plane_id:
                html = render_template(
                    TEMPLATE,
                    step=2,
                    error="Please choose a plane.",
                    flight_date=str(flight_date),
                    departure_time=departure_time.strftime("%H:%M"),
                    departure_airport=dep_airport,
                    destination_airport=dest_airport,
                    landing_time=landing_time.strftime("%H:%M") if landing_time else None,
                    available_planes=available_planes,
                    selected_plane_id=""
                )
                cur.close()
                return html

            if int(plane_id) not in set(available_planes):
                html = render_template(
                    TEMPLATE,
                    step=2,
                    error="Selected plane is not available for this flight.",
                    flight_date=str(flight_date),
                    departure_time=departure_time.strftime("%H:%M"),
                    departure_airport=dep_airport,
                    destination_airport=dest_airport,
                    landing_time=landing_time.strftime("%H:%M") if landing_time else None,
                    available_planes=available_planes,
                    selected_plane_id=plane_id
                )
                cur.close()
                return html

            # ✅ plane size מהטבלה plane
            cur.execute("SELECT Size FROM plane WHERE ID=%s LIMIT 1", (int(plane_id),))
            p = cur.fetchone()
            if not p or not p.get("Size"):
                raise ValueError("Plane size not found in plane table.")
            plane_size = str(p["Size"]).strip()
            show_business = (plane_size.lower() == "large")

            req = required_crew_by_plane_size(plane_size)
            req_pilots = req["pilots"]
            req_attendants = req["attendants"]

            _, _, available_pilots, available_attendants = _fetch_available_resources(
                cur, flight_date, departure_time, dep_airport, dest_airport
            )

            req_text = f"Plane {plane_id} is {plane_size}. You must select exactly {req_pilots} pilots and {req_attendants} attendants."

            html = render_template(
                TEMPLATE,
                step=3,
                flight_date=str(flight_date),
                departure_time=departure_time.strftime("%H:%M"),
                departure_airport=dep_airport,
                destination_airport=dest_airport,
                landing_time=landing_time.strftime("%H:%M") if landing_time else None,
                selected_plane_id=plane_id,
                plane_size=plane_size,
                show_business=show_business,
                req_pilots=req_pilots,
                req_attendants=req_attendants,
                req_text=req_text,
                available_pilots=available_pilots,
                available_attendants=available_attendants,
                selected_pilot_ids=[],
                selected_attendant_ids=[],
                economy_price="",
                business_price=""
            )
            cur.close()
            return html

        except Exception as e:
            cur.close()
            return render_template(TEMPLATE, step=2, error=str(e))

    # =========================================================
    # STEP 3: crew (checkboxes) + prices (editable) -> insert
    # =========================================================
    try:
        flight_date = _normalize_date(request.form.get("flight_date", "").strip())
        departure_time = _normalize_time(request.form.get("departure_time", "").strip())
        dep_airport = request.form.get("departure_airport", "").strip().upper()
        dest_airport = request.form.get("destination_airport", "").strip().upper()

        plane_id = (request.form.get("plane_id", "") or "").strip()
        chosen_pilots = request.form.getlist("pilot_ids")          # ✅ checkboxes
        chosen_attendants = request.form.getlist("attendant_ids")  # ✅ checkboxes

        economy_price_raw = (request.form.get("economy_price") or "").strip()
        business_price_raw = (request.form.get("business_price") or "").strip()

        landing_time, available_planes, available_pilots, available_attendants = _fetch_available_resources(
            cur, flight_date, departure_time, dep_airport, dest_airport
        )

        if not plane_id:
            raise ValueError("Missing plane.")

        if int(plane_id) not in set(available_planes):
            raise ValueError("Selected plane is not available for this flight.")

        # ✅ size מהטבלה plane
        cur.execute("SELECT Size FROM plane WHERE ID=%s LIMIT 1", (int(plane_id),))
        p = cur.fetchone()
        if not p or not p.get("Size"):
            raise ValueError("Plane size not found in plane table.")
        plane_size = str(p["Size"]).strip()
        show_business = (plane_size.lower() == "large")

        req = required_crew_by_plane_size(plane_size)

        def render_step3_error(msg):
            req_text = f"Plane {plane_id} is {plane_size}. You must select exactly {req['pilots']} pilots and {req['attendants']} attendants."
            return render_template(
                TEMPLATE,
                step=3,
                error=msg,
                flight_date=str(flight_date),
                departure_time=departure_time.strftime("%H:%M"),
                departure_airport=dep_airport,
                destination_airport=dest_airport,
                landing_time=landing_time.strftime("%H:%M") if landing_time else None,
                selected_plane_id=plane_id,
                plane_size=plane_size,
                show_business=show_business,
                req_pilots=req["pilots"],
                req_attendants=req["attendants"],
                req_text=req_text,
                available_pilots=available_pilots,
                available_attendants=available_attendants,
                selected_pilot_ids=[int(x) for x in chosen_pilots if str(x).isdigit()],
                selected_attendant_ids=[int(x) for x in chosen_attendants if str(x).isdigit()],
                economy_price=economy_price_raw,
                business_price=business_price_raw
            )

        # ✅ בדיקת כמויות צוות
        if len(chosen_pilots) != req["pilots"]:
            cur.close()
            return render_step3_error(f"You must select exactly {req['pilots']} pilots.")

        if len(chosen_attendants) != req["attendants"]:
            cur.close()
            return render_step3_error(f"You must select exactly {req['attendants']} attendants.")

        # ✅ בדיקת זמינות הצוות
        avail_pilot_ids = {p["id"] for p in available_pilots}
        avail_att_ids = {a["id"] for a in available_attendants}

        for sid in chosen_pilots:
            if not str(sid).isdigit() or int(sid) not in avail_pilot_ids:
                cur.close()
                return render_step3_error("One selected pilot is not available.")

        for sid in chosen_attendants:
            if not str(sid).isdigit() or int(sid) not in avail_att_ids:
                cur.close()
                return render_step3_error("One selected attendant is not available.")

        # ✅ ולידציה למחירים (מנהל מקליד)
        try:
            economy_price = Decimal(economy_price_raw)
        except (InvalidOperation, ValueError):
            cur.close()
            return render_step3_error("Economy price must be a valid number.")

        if economy_price <= 0:
            cur.close()
            return render_step3_error("Economy price must be greater than 0.")

        business_price = None
        if show_business:
            try:
                business_price = Decimal(business_price_raw)
            except (InvalidOperation, ValueError):
                cur.close()
                return render_step3_error("Business price must be a valid number for Large planes.")
            if business_price <= 0:
                cur.close()
                return render_step3_error("Business price must be greater than 0.")
        else:
            business_price = None  # Small -> אין ביזנס

        # הגנות נוספות
        flight_row = _build_flight_row_for_checks(
            flight_date, departure_time, landing_time, dep_airport, dest_airport, int(plane_id)
        )
        validate_long_flight_plane_size(cur, flight_row)

        # ✅ INSERT לטבלת Flights כולל מחירים
        cur.execute("""
            INSERT INTO `flights`
              (`Flight_Date`, `Departure_Time`, `Plane_ID`, `Landing_Time`,
               `Departure_Airport`, `Destination_Airport`, `status`,
               `economy_price`, `business_price`)
            VALUES
              (%s, %s, %s, %s, %s, %s, 'active', %s, %s)
        """, (
            flight_date, departure_time, int(plane_id), landing_time,
            dep_airport, dest_airport,
            float(economy_price),
            float(business_price) if business_price is not None else None
        ))

        # ✅ INSERT Staff_On_Flight
        all_staff_ids = [int(x) for x in chosen_pilots] + [int(x) for x in chosen_attendants]
        for sid in all_staff_ids:
            cur.execute("""
                INSERT INTO `staff_on_flight`
                  (`ID`, `flight_date`, `departure_time`, `plane_ID`)
                VALUES
                  (%s, %s, %s, %s)
            """, (sid, flight_date, departure_time, int(plane_id)))

        mydb.commit()
        cur.close()
        return render_template(TEMPLATE, step=1, success="Flight created successfully!")

    except Exception as e:
        mydb.rollback()
        cur.close()
        return render_template(TEMPLATE, step=1, error=str(e))

def generate_admin_stats_report(mydb, app_root_path):

    # 🎨 Colors
    LIGHT_PURPLE = "#EAE6FF"
    TURQUOISE = "#8FB9A8"

    # 📁 Output folder
    out_dir = os.path.join(app_root_path, "static", "reports")
    os.makedirs(out_dir, exist_ok=True)

    cancel_img = "reports/cancellation_rate.png"
    dest_pie_img = "reports/popular_destination_pie.png"

    cancel_img_path = os.path.join(out_dir, "cancellation_rate.png")
    dest_pie_path = os.path.join(out_dir, "popular_destination_pie.png")

    cur = mydb.cursor(dictionary=True)

    # ==========================================================
    # 1️⃣ Cancellation rate – last 3 months
    # ==========================================================
    cur.execute("""
        SELECT
            YEAR(t.flight_date) AS yy,
            MONTH(t.flight_date) AS mm,
            COUNT(DISTINCT b.booking_code) AS total_bookings,
            COUNT(DISTINCT CASE
                WHEN LOWER(b.status) LIKE '%customer cancelled%' THEN b.booking_code
            END) AS cancelled
        FROM tickets t
        JOIN bookings b ON b.booking_code = t.booking_code
        WHERE t.flight_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
        GROUP BY yy, mm
        ORDER BY yy, mm
    """)
    rows = cur.fetchall()

    monthly_rows = []

    if rows:
        df = pd.DataFrame(rows)
        df["rate"] = df.apply(
            lambda r: float(r["cancelled"]) / float(r["total_bookings"])
            if r["total_bookings"] else 0,
            axis=1
        )
        df["month_dt"] = df.apply(lambda r: datetime(int(r.yy), int(r.mm), 1), axis=1)
        df["MonthLabel"] = df["month_dt"].dt.strftime("%b-%Y")

        # 📈 Plot
        plt.figure(figsize=(8, 4))
        plt.plot(
            df["month_dt"],
            df["rate"],
            color=TURQUOISE,
            linewidth=3,
            marker="o",
            markerfacecolor=LIGHT_PURPLE,
            markeredgecolor=TURQUOISE
        )
        plt.title("Customer Cancellation Rate (Last 3 Months)")
        plt.xlabel("Month")
        plt.ylabel("Cancellation Rate")
        plt.ylim(0, 1)
        plt.grid(True, alpha=0.35)
        plt.xticks(df["month_dt"], df["MonthLabel"], rotation=45)
        plt.tight_layout()
        plt.savefig(cancel_img_path, dpi=150)
        plt.close()

    # ==========================================================
    # 2️⃣ Most popular destination – pie chart
    # ==========================================================
    cur.execute("""
        SELECT
            f.Destination_Airport AS destination,
            COUNT(*) AS tickets_sold
        FROM tickets t
        JOIN bookings b ON b.booking_code = t.booking_code
        JOIN flights f
          ON f.Flight_Date = t.flight_date
         AND f.Departure_Time = t.departure_time
        WHERE t.flight_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
          AND LOWER(b.status) NOT LIKE '%cancel%'
        GROUP BY destination
        ORDER BY tickets_sold DESC
    """)
    dest_rows = cur.fetchall()

    top_destination = None
    top_destination_tickets = 0

    if dest_rows:
        ddf = pd.DataFrame(dest_rows)
        labels = ddf["destination"].tolist()
        values = ddf["tickets_sold"].tolist()

        top_destination = labels[0]
        top_destination_tickets = int(values[0])

        explode = [0.08] + [0] * (len(values) - 1)
        colors = plt.cm.PRGn(np.linspace(0.15, 0.85, len(values)))

        plt.figure(figsize=(7, 5))
        plt.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            explode=explode,
            colors=colors
        )
        plt.title(f"Most Popular Destination: {top_destination}")
        plt.tight_layout()
        plt.savefig(dest_pie_path, dpi=150)
        plt.close()

    # הנתונים לפי הפלט ששלחת
    data = [
        {"Size": "Large", "Manufacturer": "Airbus", "Class_Type": "business", "revenue": 1840.00},
        {"Size": "Large", "Manufacturer": "Airbus", "Class_Type": "economy", "revenue": 915.00},
        {"Size": "Small", "Manufacturer": "Airbus", "Class_Type": "economy", "revenue": 0.00},
        {"Size": "Large", "Manufacturer": "Boeing", "Class_Type": "business", "revenue": 0.00},
        {"Size": "Large", "Manufacturer": "Boeing", "Class_Type": "economy", "revenue": 0.00},
        {"Size": "Small", "Manufacturer": "Boeing", "Class_Type": "economy", "revenue": 460.00},
        {"Size": "Small", "Manufacturer": "Dassault", "Class_Type": "economy", "revenue": 100.00},
    ]

    df = pd.DataFrame(data)

    # יצירת קטגוריה לכל "מטוס" (כאן: Manufacturer + Size)
    df["plane_group"] = df["Manufacturer"] + " " + df["Size"]

    # Pivot לטבלה רחבה לגרף (business/economy כעמודות)
    pivot = (df.pivot_table(index="plane_group",
                            columns="Class_Type",
                            values="revenue",
                            aggfunc="sum",
                            fill_value=0)
             .reset_index())

    # ודא ששתי העמודות קיימות (גם אם אין business בכלל בחלק מהקבוצות)
    if "business" not in pivot.columns:
        pivot["business"] = 0
    if "economy" not in pivot.columns:
        pivot["economy"] = 0

    # סדר עמודות קבוע
    pivot = pivot[["plane_group", "business", "economy"]]

    print(pivot)  # זו הטבלה שתוכל להשתמש בה גם לכל צורך נוסף

    # --- גרף ---
    labels = pivot["plane_group"].tolist()
    x = np.arange(len(labels))
    width = 0.38

    business_vals = pivot["business"].values
    economy_vals = pivot["economy"].values

    # צבעים: לילך + ירוק
    lilac = "#EAE6FF"
    green = "#8FB9A8"

    plt.figure(figsize=(10, 5))
    plt.bar(x - width / 2, business_vals, width, label="business", color=lilac)
    plt.bar(x + width / 2, economy_vals, width, label="economy", color=green)

    plt.xticks(x, labels, rotation=0)
    plt.xlabel("Plane group (Manufacturer + Size)")
    plt.ylabel("Revenue")
    plt.title("Revenue Comparison: Business vs Economy")
    plt.legend()
    plt.tight_layout()
    revenue_by_plane_group_group_path = os.path.join(out_dir, "revenue_by_plane_group.png")
    plt.savefig(revenue_by_plane_group_group_path, dpi=150, bbox_inches="tight")
    plt.close()
    # ==========================================================
    # 3️⃣ Monthly averages table – last 3 months
    # ==========================================================
    cur.execute("""
        SELECT
            DATE_FORMAT(t.flight_date, '%b-%Y') AS MonthLabel,
            COUNT(DISTINCT CONCAT(t.flight_date, t.departure_time)) AS flights_count,
            COUNT(DISTINCT b.booking_code) AS bookings_count,
            ROUND(SUM(b.total_price), 2) AS revenue_total,
            ROUND(
                SUM(CASE WHEN LOWER(b.status) LIKE '%customer cancelled%' THEN 1 ELSE 0 END)
                / COUNT(DISTINCT b.booking_code), 2
            ) AS customer_cancel_rate
        FROM tickets t
        JOIN bookings b ON b.booking_code = t.booking_code
        WHERE t.flight_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
        GROUP BY MonthLabel
        ORDER BY MIN(t.flight_date)
    """)
    monthly_rows = cur.fetchall()

    cur.close()

    return {
        "cancel_img": cancel_img,
        "dest_pie_img": dest_pie_img,
        "monthly_rows": monthly_rows,
        "top_destination": top_destination,
        "top_destination_tickets": top_destination_tickets
    }

@app.route("/admin_statistics", methods=["GET"])
def admin_statistics():
    # אם אצלך יש בדיקת אדמין אחרת - תשאיר אותה כמו שהיא
    if session.get("role") != "admin":
        return redirect("/admin_login")

    ensure_mydb_is_connected()

    report = generate_admin_stats_report(mydb, app.root_path)

    return render_template(
        "admin_statistics.html",
        cancel_img=report["cancel_img"],
        dest_pie_img=report["dest_pie_img"],
        monthly_rows=report["monthly_rows"],
        top_destination=report["top_destination"],
        top_destination_tickets=report["top_destination_tickets"]
    )
@app.route('/board')
def board_page():
    return render_template('board.html')
# if __name__ == "__main__": # uncomment if using local, comment if using pythonanywhere.
#     app.run(debug=True)
