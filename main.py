from flask import Flask, render_template, redirect, request, session
from flask_session import Session
import mysql.connector
from datetime import timedelta, datetime, date, time
import string
import re
import random
from utilities import (
    validate_long_flight_plane_size,
    fetch_flight,
    can_assign_staff,
    can_use_plane,
    lock_total_price_at_booking_time,
)





app = Flask(__name__)

app.config.update(
    SESSION_TYPE="filesystem",
    SESSION_FILE_DIR="flask_session_data",   # עדיף תיקייה יחסית בפרויקט
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=10),
    SESSION_REFRESH_EACH_REQUEST=True,
    SESSION_COOKIE_SECURE=False              # אם אתה עובד על localhost (לא https)
)

Session(app)

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="flytau",
    autocommit=True
)

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
            return redirect("/")
        else:
            return render_template("login.html", message="Incorrect password")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()      # מוחק את כל הסשן (user / admin / role)
    return redirect("/login")


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

        session["username"] = email
        return redirect("/")

    return render_template("signup.html")


@app.route("/flights", methods=["GET"])
def flights():
    # אם אתה רוצה שרק משתמש מחובר יראה:

    flight_date = request.args.get("flight_date", "").strip()          # YYYY-MM-DD
    dep = request.args.get("departure_airport", "").strip().upper()    # TLV
    dest = request.args.get("destination_airport", "").strip().upper() # ATH

    # בונים query דינמי לפי מה שהמשתמש מילא
    sql = """
        SELECT Flight_Date, Departure_Time, Landing_Time,
               Departure_Airport, Destination_Airport, Plane_ID, status
        FROM flights
        WHERE status = 'active'
    """
    params = []

    if flight_date:
        sql += " AND Flight_Date = %s"
        params.append(flight_date)

    if dep:
        sql += " AND Departure_Airport = %s"
        params.append(dep)

    if dest:
        sql += " AND Destination_Airport = %s"
        params.append(dest)

    sql += " ORDER BY Flight_Date, Departure_Time"

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

def col_labels(n: int):
    # A, B, C, ... (עד 26 טורים מספיק לרוב)
    letters = list(string.ascii_uppercase)
    return letters[:n]

@app.route("/seats")
def seats():
    flight_date = request.args.get("flight_date")
    departure_time = request.args.get("departure_time")

    cur = mydb.cursor(dictionary=True)

    # 1️⃣ שליפת המטוס של הטיסה
    cur.execute("""
        SELECT Plane_ID, Departure_Airport, Destination_Airport
        FROM flights
        WHERE Flight_Date = %s AND Departure_Time = %s
    """, (flight_date, departure_time))
    flight = cur.fetchone()

    if not flight:
        cur.close()
        return "Flight not found"

    plane_id = flight["Plane_ID"]

    # 2️⃣ שליפת המחלקות לפי סדר: Business ואז Economy
    cur.execute("""
        SELECT Class_Type, Number_of_Rows, Number_of_Columns
        FROM Classes
        WHERE Plane_ID = %s
        ORDER BY
          CASE
            WHEN Class_Type = 'Business' THEN 1
            WHEN Class_Type = 'Economy' THEN 2
          END
    """, (plane_id,))
    classes = cur.fetchall()

    # 3️⃣ שליפת מושבים שכבר נמכרו (עם מספור רציף!)
    cur.execute("""
        SELECT t.`row`, t.`col`
        FROM tickets t
        JOIN bookings b ON b.booking_code = t.booking_code
        WHERE t.flight_date = %s
          AND t.departure_time = %s
          AND LOWER(b.status) NOT LIKE '%cancel%'
    """, (flight_date, departure_time))
    sold = {(r["row"], r["col"]) for r in cur.fetchall()}

    cur.close()

    # 4️⃣ בניית מפת מושבים — כאן קורה ה־B+1 עד B+E
    sections = []
    offset = 0   # כמה שורות כבר היו במטוס

    for c in classes:
        class_type = c["Class_Type"]
        rows = int(c["Number_of_Rows"])
        cols = int(c["Number_of_Columns"])
        labels = [chr(ord('A') + i) for i in range(cols)]

        start_row = offset + 1        # Business: 1, Economy: B+1
        end_row = offset + rows       # Business: B, Economy: B+E

        grid = []
        for r in range(start_row, end_row + 1):
            row_seats = []
            for col_i in range(1, cols + 1):
                row_seats.append({
                    "row": r,
                    "col": col_i,
                    "label": labels[col_i - 1],
                    "sold": (r, col_i) in sold
                })
            grid.append({"row": r, "seats": row_seats})

        sections.append({
            "class_type": class_type,
            "grid": grid
        })

        offset += rows   # ⬅️ זה מה שגורם לאקונומי להתחיל מ־B+1

    return render_template(
        "seats.html",
        sections=sections,
        flight=flight,
        flight_date=flight_date,
        departure_time=departure_time
    )

def seat_to_row_col(seat_code: str):
    m = re.match(r"^(\d+)([A-Z])$", seat_code.strip().upper())
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
        FROM Classes
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
    import string
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
    while True:
        code = random.randint(100000, 999999)
        cur.execute("SELECT 1 FROM bookings WHERE booking_code=%s LIMIT 1", (code,))
        if not cur.fetchone():
            return code

def get_class_ranges(cur, plane_id):
    # מחזיר טווחי שורות רציפים לכל מחלקה (Business ואז Economy)
    cur.execute("""
        SELECT Class_Type, Number_of_Rows, Number_of_Columns
        FROM Classes
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

# @app.route("/order/create", methods=["GET", "POST"])
@app.route("/order/preview", methods=["GET","POST"])
def order_preview():
    flight_date = request.form.get("flight_date", "").strip()
    departure_time = request.form.get("departure_time", "").strip()
    selected = request.form.get("selected_seats", "").strip()

    if not flight_date or not departure_time:
        return "Missing flight info", 400
    if not selected:
        return redirect(f"/order/new?flight_date={flight_date}&departure_time={departure_time}")

    # מי הלקוח?
    email = session.get("username")
    if not email:
        email = request.form.get("guest_email", "").strip()
        if not email:
            return "Missing email", 400

    # אם זה אורח (לא מחובר) - נשמור אימייל כדי שיראה הזמנות בלי להקליד שוב
    if not session.get("username"):
        session["guest_email"] = email

    seat_codes = [x.strip().upper() for x in selected.split(",") if x.strip()]
    seats = []
    for code in seat_codes:
        rc = seat_to_row_col(code)
        if rc is None:
            return f"Bad seat code: {code}", 400
        seats.append(rc)  # (row,col)

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

    # בדיקת תפוסה בזמן preview (מומלץ)
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

    # האם האימייל מוכר?
    cur.execute("SELECT 1 FROM registered_customers WHERE email=%s LIMIT 1", (email,))
    is_registered = cur.fetchone() is not None

    cur.execute("SELECT 1 FROM unregistered_customers WHERE email=%s LIMIT 1", (email,))
    is_unregistered = cur.fetchone() is not None

    need_unreg_details = (not is_registered) and (not is_unregistered)


    # תמחור: Business=200, Economy=100
    seat_items = []
    total_price = 0
    for (r, c) in seats:
        cls = class_for_row(ranges, r)
        if cls == "Business":
            price = 200
        else:
            price = 100
        total_price += price
        seat_items.append({
            "seat": f"{r}{chr(ord('A') + c - 1)}",
            "row": r,
            "col": c,
            "class": cls,
            "price": price
        })

    # קוד הזמנה ייחודי (עדיין לא נכתב ל-DB)
    cur2 = mydb.cursor()
    booking_code = generate_booking_code(cur2)
    cur2.close()
    cur.close()

    # נשמור את כל מה שצריך ל-confirm בתוך session (כדי שלא יסמכו על hidden)
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
        booking_code=booking_code,
        email=email,
        flight=flight,
        flight_date=flight_date,
        departure_time=departure_time,
        seat_items=seat_items,
        total_price=total_price,
        need_unreg_details=need_unreg_details
    )
@app.route("/order/confirm", methods=["POST"])
def order_confirm():
    pending = session.get("pending_order")
    if not pending:
        return "No pending order", 400

    booking_code = pending["booking_code"]
    email = pending["email"]
    if not session.get("username"):
        session["guest_email"] = email
    flight_date = pending["flight_date"]
    departure_time = pending["departure_time"]
    seats = pending["seats"]
    total_price = pending["total_price"]

    # אם צריך ליצור unregistered_customer — נקבל פרטים מהטופס
    fname = request.form.get("fname", "").strip()
    lname = request.form.get("lname", "").strip()
    phone_number = request.form.get("phone_number", "").strip()

    cur = mydb.cursor(dictionary=True)

    try:
        mydb.start_transaction()

        # האם email רשום / לא רשום?
        cur.execute("SELECT 1 FROM registered_customers WHERE email=%s LIMIT 1", (email,))
        is_registered = cur.fetchone() is not None

        cur.execute("SELECT 1 FROM unregistered_customers WHERE email=%s LIMIT 1", (email,))
        is_unregistered = cur.fetchone() is not None

        if (not is_registered) and (not is_unregistered):
            if not fname or not lname or not phone_number:
                mydb.rollback()
                cur.close()
                return "Missing guest details", 400

            cur.execute("""
                INSERT INTO unregistered_customers (email, fname, lname)
                VALUES (%s,%s,%s)
            """, (email, fname, lname))

            # נשמור טלפון
            cur.execute("""
                INSERT INTO Phone_numbers (email, phone_number)
                VALUES (%s,%s)
            """, (email, phone_number))

        # בדיקת תפוסה מחדש (חשוב!) לפני כתיבה
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

        # יצירת order (העמודות החדשות שלך: total_price, order_date)
        cur.execute("""
            INSERT INTO bookings (booking_code, email, status, total_price)
            VALUES (%s,%s,%s,%s)
        """, (booking_code, email, "paid", total_price))

        # הכנסת Tickets
        for (r, c) in seats:
            cur.execute("""
                INSERT INTO tickets (`row`, `col`, booking_code, flight_date, departure_time)
                VALUES (%s,%s,%s,%s,%s)
            """, (r, c, booking_code, flight_date, departure_time))

        mydb.commit()
        cur.close()

        # ניקוי pending
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

    email = session.get("username") or session.get("guest_email") or (request.args.get("email") or "").strip()

    if not email:
        return render_template("my_booking.html", email="", upcoming=[], history=[], message="")

    # משתמש רשום = אימייל שקיים ב-registered_customers
    cur0 = mydb.cursor()
    cur0.execute("SELECT 1 FROM registered_customers WHERE email=%s LIMIT 1", (email,))
    is_registered = cur0.fetchone() is not None
    cur0.close()

    cur = mydb.cursor(dictionary=True)

    cur.execute("""
        SELECT
            b.booking_code,
            b.email,
            b.status,
            b.total_price,
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
        WHERE b.email = %s
        GROUP BY
            b.booking_code, b.email, b.status, b.total_price,
            f.Flight_Date, f.Departure_Time, f.Landing_Time,
            f.Departure_Airport, f.Destination_Airport
        ORDER BY f.Flight_Date DESC, f.Departure_Time DESC
    """, (email,))

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

    # כלל ההרשאה החדש: היסטוריה רק אם האימייל רשום בטבלת Registered_customers
    if not is_registered:
        history = []

    return render_template(
        "my_booking.html",
        email=email,
        upcoming=upcoming,
        history=history,
        message=""
    )

@app.route("/booking/cancel", methods=["POST"])
def booking_cancel():
    booking_code = (request.form.get("booking_code") or "").strip()
    page_email = (request.form.get("email") or "").strip()

    if not booking_code or not page_email:
        return "Missing booking_code or email", 400

    cur = mydb.cursor(dictionary=True)

    try:
        mydb.start_transaction()

        # לוודא שההזמנה קיימת ושייכת לאותו אימייל שמוצג בדף
        cur.execute("""
            SELECT booking_code, email, status, total_price
            FROM bookings
            WHERE booking_code = %s
            LIMIT 1
        """, (booking_code,))
        b = cur.fetchone()
        if not b:
            mydb.rollback()
            cur.close()
            return "Booking not found", 404

        if (b["email"] or "").strip().lower() != page_email.strip().lower():
            mydb.rollback()
            cur.close()
            return "Not allowed", 403

        # אם כבר בוטלה
        status_lower = (b["status"] or "").strip().lower()
        if status_lower.startswith("cancel") or status_lower.endswith("cancelled") or "cancel" in status_lower:
            mydb.rollback()
            cur.close()
            return redirect(f"/my_booking?email={page_email}")

        # להביא את תאריך/שעת הטיסה מהכרטיסים (מספיק כרטיס אחד)
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

        # normalize time (יכול להגיע כ-time או timedelta או str)
        if isinstance(dep, timedelta):
            dep = (datetime.min + dep).time()
        elif not isinstance(dep, time):
            dep = datetime.strptime(str(dep).split(".")[0], "%H:%M:%S").time()

        flight_dt = datetime.combine(fd, dep)
        now = datetime.now()
        hours_left = (flight_dt - now).total_seconds() / 3600.0

        original_total = float(b["total_price"] or 0)

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
    return redirect("/admin_login")


@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get("role") != "admin":   # ✅ החלפה כאן
        return redirect("/admin_login")

    cur = mydb.cursor(dictionary=True)

    cur.execute("""
        SELECT Flight_Date, Departure_Time, Landing_Time,
               Departure_Airport, Destination_Airport, Plane_ID, status
        FROM flights
        ORDER BY Flight_Date DESC, Departure_Time DESC
    """)
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

    return render_template(
        "admin_dashboard.html",
        admin_name=session.get("admin_name", "Admin"),
        flights=flights_view
    )

@app.route("/admin_add_flight", methods=["GET", "POST"])
def admin_add_flight():
    if not session.get("admin_id"):
        return redirect("/admin_login")

    if request.method == "GET":
        return render_template("admin_add_flight.html", message="")

    # ---------- קלט ----------
    flight_date = (request.form.get("flight_date") or "").strip()
    departure_time = (request.form.get("departure_time") or "").strip()
    landing_time = (request.form.get("landing_time") or "").strip() or None
    plane_id = (request.form.get("plane_id") or "").strip()
    dep_airport = (request.form.get("departure_airport") or "").strip().upper()
    dest_airport = (request.form.get("destination_airport") or "").strip().upper()

    # ---------- ולידציה בסיסית ----------
    if not (flight_date and departure_time and plane_id and dep_airport and dest_airport):
        return render_template("admin_add_flight.html", message="Missing required fields")

    if not plane_id.isdigit():
        return render_template("admin_add_flight.html", message="Plane ID must be numeric")

    # נרמול שעה
    if len(departure_time) == 5:
        departure_time += ":00"
    if landing_time and len(landing_time) == 5:
        landing_time += ":00"

    # ---------- הלוגיקה האמיתית ----------
    ok, msg = add_flight_with_rules(
        mydb,
        flight_date,
        departure_time,
        int(plane_id),
        landing_time,
        dep_airport,
        dest_airport,
        status="active"
    )

    if not ok:
        return render_template("admin_add_flight.html", message=msg)

    return redirect("/admin_dashboard")


def add_flight_with_rules(mydb, flight_date, departure_time, plane_id, landing_time, dep_airport, dest_airport, status="active"):
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
            INSERT INTO `Flights`
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
            SELECT 1 FROM `Staff_On_Flight`
            WHERE `flight_date`=%s AND `departure_time`=%s AND `plane_ID`=%s AND `ID`=%s
            LIMIT 1
        """, (flight_date, departure_time, int(plane_id), int(staff_id)))
        if cur.fetchone():
            return False, "Staff already assigned to this flight"

        cur.execute("""
            INSERT INTO `Staff_On_Flight` (`flight_date`, `departure_time`, `plane_ID`, `ID`)
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

        # 2) refund & mark bookings as admin cancelled (for bookings connected to this flight via tickets)
        cur.execute("""
            UPDATE bookings b
            JOIN (
                SELECT DISTINCT booking_code
                FROM tickets
                WHERE flight_date=%s AND departure_time=%s
            ) x ON x.booking_code = b.booking_code
            SET b.status = 'admin cancelled',
                b.total_price = 0.00
            WHERE b.status NOT LIKE '%cancel%'
              AND b.status <> 'completed'
        """, (flight_date, departure_time))

        mydb.commit()
        cur.close()
        return redirect("/admin_dashboard")

    except Exception as e:
        mydb.rollback()
        cur.close()
        return f"Cancel failed: {e}", 400



if __name__ == "__main__":
    app.run(debug=True)
