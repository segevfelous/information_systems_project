from datetime import datetime, timedelta, date, time

# =========================================================
# A) Fetch helpers (Flights / Plane / Booking / Tickets)
# =========================================================

def fetch_flight(cur, flight_date, departure_time, plane_id):
    """
    Flights (Flight_Date, Departure_Time, Plane_ID, Landing_Time,
            Departure_Airport, Destination_Airport, status)
    """
    cur.execute("""
        SELECT
            `Flight_Date`            AS flight_date,
            `Departure_Time`         AS departure_time,
            `Plane_ID`             AS plane_id,
            `Landing_Time`           AS landing_time,
            `Departure_Airport`      AS dep_airport,
            `Destination_Airport`    AS dest_airport,
            `status`                 AS status
        FROM `flights`
        WHERE `Flight_Date`=%s AND `Departure_Time`=%s AND `Plane_ID`=%s
        LIMIT 1
    """, (flight_date, departure_time, int(plane_id)))
    return cur.fetchone()


def fetch_plane_size(cur, plane_id):
    """
    Plane (ID, Manufacturer, Size, Purchase Date)
    """
    cur.execute("""
        SELECT `Size` AS size
        FROM `plane`
        WHERE `ID`=%s
        LIMIT 1
    """, (int(plane_id),))
    row = cur.fetchone()
    return row["size"] if row else None


def fetch_booking(cur, booking_code: int):
    """
    Bookings (booking_code, email, status, total_price)
    """
    cur.execute("""
        SELECT
            `booking_code` AS booking_code,
             COALESCE(registered_email, unregistered_email) AS email,            `status`       AS status,
            `total_price`  AS total_price
        FROM `bookings`
        WHERE `booking_code`=%s
        LIMIT 1
    """, (int(booking_code),))
    return cur.fetchone()


def count_tickets_in_booking(cur, booking_code: int) -> int:
    """
    Tickets (row, col, booking_code F, F -Flight_Date, F -Departure_Time)
    """
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM `tickets`
        WHERE `booking_code F`=%s
    """, (int(booking_code),))
    row = cur.fetchone()
    return int(row["cnt"]) if row else 0


def fetch_flight_airports(cur, flight_date, departure_time, plane_id):
    cur.execute("""
        SELECT
            `Departure_Airport`   AS dep_airport,
            `Destination_Airport` AS dest_airport
        FROM `flights`
        WHERE `Flight_Date`=%s AND `Departure_Time`=%s AND `Plane_ID`=%s
        LIMIT 1
    """, (flight_date, departure_time, int(plane_id)))
    return cur.fetchone()


# =========================================================
# B) Datetime + overlap helpers
# =========================================================

def _time_to_str(t):
    s = t.isoformat() if hasattr(t, "isoformat") else str(t)
    if len(s) == 5:  # HH:MM
        s += ":00"
    return s


def dep_datetime_from_flight(flight_row) -> datetime:
    d = flight_row["flight_date"]
    t = flight_row["departure_time"]
    d_str = d.isoformat() if hasattr(d, "isoformat") else str(d)
    t_str = _time_to_str(t)
    return datetime.strptime(f"{d_str} {t_str}", "%Y-%m-%d %H:%M:%S")


def land_datetime_from_flight(flight_row) -> datetime | None:
    if not flight_row.get("landing_time"):
        return None

    d = flight_row["flight_date"]
    dep_t = flight_row["departure_time"]
    land_t = flight_row["landing_time"]

    d_str = d.isoformat() if hasattr(d, "isoformat") else str(d)

    dep_str = _time_to_str(dep_t)
    land_str = _time_to_str(land_t)

    dep_dt = datetime.strptime(f"{d_str} {dep_str}", "%Y-%m-%d %H:%M:%S")
    land_dt = datetime.strptime(f"{d_str} {land_str}", "%Y-%m-%d %H:%M:%S")

    if land_dt < dep_dt:
        land_dt += timedelta(days=1)

    return land_dt


def flight_time_range(flight_row):
    start = dep_datetime_from_flight(flight_row)
    end = land_datetime_from_flight(flight_row) or start  # אם אין נחיתה -> 0 duration
    return start, end


def ranges_overlap(a_start, a_end, b_start, b_end) -> bool:
    return not (a_end <= b_start or a_start >= b_end)


# =========================================================
# C) Flight duration table + long flight definition (>= 6h)
# =========================================================

def fetch_route_duration_hours(cur, dep_airport: str, dest_airport: str) -> float | None:
    """
    Flight_Duration (Departure_Airport, Destination_Airport, Duration in Hours)
    """
    cur.execute("""
        SELECT `Duration_in_Hours` AS dur
        FROM `flight_duration`
        WHERE `Departure_Airport`=%s AND `Destination_Airport`=%s
        LIMIT 1
    """, (dep_airport, dest_airport))
    row = cur.fetchone()
    return float(row["dur"]) if row and row["dur"] is not None else None


def is_long_flight(cur, flight_row) -> bool:
    """
    טיסה ארוכה = 6 שעות ומעלה.
    מקור ראשי: Flight_Duration.
    Fallback: אם אין מסלול בטבלה, נחשב לפי זמנים אם יש Landing_Time.
    """
    dur = fetch_route_duration_hours(cur, flight_row["dep_airport"], flight_row["dest_airport"])
    if dur is not None:
        return dur >= 6.0

    start, end = flight_time_range(flight_row)
    return (end - start).total_seconds() >= 6 * 3600


# =========================================================
# D) Rule: long flight must be Large plane
# =========================================================

def validate_long_flight_plane_size(cur, flight_row) -> None:
    """
    ארוכה (>=6h) => רק מטוס גדול.
    """
    plane_size = fetch_plane_size(cur, flight_row["plane_id"])
    if not plane_size:
        raise ValueError("Plane not found")

    if is_long_flight(cur, flight_row) and plane_size.strip().lower() != "large":
        raise ValueError("Long flight (6h+) must use a large plane")


# =========================================================
# E) Crew requirements by plane size
# =========================================================

def required_crew_by_plane_size(plane_size: str):
    """
    מטוס גדול: 3 טייסים ו-6 דיילים
    מטוס קטן: 2 טייסים ו-3 דיילים
    """
    s = (plane_size or "").strip().lower()
    if s == "large":
        return {"pilots": 3, "attendants": 6}
    return {"pilots": 2, "attendants": 3}


# =========================================================
# F) Staff role inference (because Staff_On_Flight has no role column)
# =========================================================

def is_pilot(cur, staff_id: int) -> bool:
    cur.execute("SELECT 1 FROM `pilot` WHERE `ID`=%s LIMIT 1", (int(staff_id),))
    return cur.fetchone() is not None


def is_attendant(cur, staff_id: int) -> bool:
    cur.execute("SELECT 1 FROM `flight_attendant` WHERE `ID`=%s LIMIT 1", (int(staff_id),))
    return cur.fetchone() is not None


def staff_role(cur, staff_id: int) -> str | None:
    if is_pilot(cur, staff_id):
        return "pilot"
    if is_attendant(cur, staff_id):
        return "attendant"
    return None


# =========================================================
# G) Count staff on a flight + completeness check
# =========================================================

def staff_ids_on_flight(cur, flight_date, departure_time, plane_id):
    cur.execute("""
        SELECT `ID` AS staff_id
        FROM `staff_on_flight`
        WHERE `flight_date`=%s AND `departure_time`=%s AND `plane_ID`=%s
    """, (flight_date, departure_time, int(plane_id)))
    return [r["staff_id"] for r in (cur.fetchall() or [])]


def count_staff_on_flight(cur, flight_date, departure_time, plane_id):
    staff_ids = staff_ids_on_flight(cur, flight_date, departure_time, plane_id)

    pilots = 0
    attendants = 0
    for sid in staff_ids:
        if is_pilot(cur, sid):
            pilots += 1
        elif is_attendant(cur, sid):
            attendants += 1

    return {"pilots": pilots, "attendants": attendants, "total": len(staff_ids)}


def crew_complete_for_flight(cur, flight_row) -> bool:
    plane_size = fetch_plane_size(cur, flight_row["plane_id"])
    req = required_crew_by_plane_size(plane_size)
    counts = count_staff_on_flight(cur, flight_row["flight_date"], flight_row["departure_time"], flight_row["plane_id"])
    return (counts["pilots"] == req["pilots"]) and (counts["attendants"] == req["attendants"])


# =========================================================
# H) Time conflicts (staff / plane)
# =========================================================
def staff_assigned_flights(cur, staff_id: int, include_cancelled: bool = False):
    """
    כל הטיסות שה-ID הזה משובץ אליהן דרך Staff_On_Flight.
    ברירת מחדל: לא מחזירים טיסות cancelled (כדי שביטול ישחרר צוות).
    """
    sql = """
        SELECT
            f.`Flight_Date`         AS flight_date,
            f.`Departure_Time`      AS departure_time,
            f.`Plane_ID`            AS plane_id,
            f.`Landing_Time`        AS landing_time,
            f.`Departure_Airport`   AS dep_airport,
            f.`Destination_Airport` AS dest_airport,
            f.`status`              AS status
        FROM `staff_on_flight` sof
        JOIN `flights` f
          ON f.`Flight_Date`=sof.`flight_date`
         AND f.`Departure_Time`=sof.`departure_time`
         AND f.`Plane_ID`=sof.`plane_ID`
        WHERE sof.`ID`=%s
    """
    params = [int(staff_id)]

    if not include_cancelled:
        sql += " AND LOWER(f.`status`) NOT LIKE '%cancel%' "

    cur.execute(sql, tuple(params))
    return cur.fetchall() or []

def has_time_conflict_staff(cur, flight_row, staff_id: int) -> bool:
    new_start, new_end = flight_time_range(flight_row)

    # ✅ לא לכלול cancelled — כדי שביטול ישחרר צוות
    for f in staff_assigned_flights(cur, staff_id, include_cancelled=False):
        if (f["flight_date"], f["departure_time"], f["plane_id"]) == (
            flight_row["flight_date"], flight_row["departure_time"], flight_row["plane_id"]
        ):
            continue
        start, end = flight_time_range(f)
        if ranges_overlap(new_start, new_end, start, end):
            return True

    return False

def has_time_conflict_plane(cur, flight_row, plane_id: int) -> bool:
    new_start, new_end = flight_time_range(flight_row)

    cur.execute("""
        SELECT
            `Flight_Date`         AS flight_date,
            `Departure_Time`      AS departure_time,
            `Plane_ID`            AS plane_id,
            `Landing_Time`        AS landing_time,
            `Departure_Airport`   AS dep_airport,
            `Destination_Airport` AS dest_airport,
            `status`              AS status
        FROM `flights`
        WHERE `Plane_ID`=%s
          AND LOWER(`status`) NOT LIKE '%cancel%'   -- ✅ מתעלמים ממבוטלות
    """, (int(plane_id),))
    flights = cur.fetchall() or []

    for f in flights:
        if (f["flight_date"], f["departure_time"], f["plane_id"]) == (
            flight_row["flight_date"], flight_row["departure_time"], flight_row["plane_id"]
        ):
            continue
        start, end = flight_time_range(f)
        if ranges_overlap(new_start, new_end, start, end):
            return True

    return False

# =========================================================
# I) Location constraint (first assignment allowed)
# =========================================================
def last_location_staff_before(cur, staff_id: int, dep_dt: datetime) -> str | None:
    """
    מיקום = שדה יעד של הטיסה האחרונה שהסתיימה לפני dep_dt.
    ✅ מתעלמים ממבוטלות כדי שה"מיקום האחרון" לא ייתקע על טיסה cancelled.
    """
    best_end = None
    best_loc = None

    for f in staff_assigned_flights(cur, staff_id, include_cancelled=False):
        start, end = flight_time_range(f)
        if end < dep_dt:
            if best_end is None or end > best_end:
                best_end = end
                best_loc = f["dest_airport"]

    return best_loc

def last_location_plane_before(cur, plane_id: int, dep_dt: datetime) -> str | None:
    best_end = None
    best_loc = None

    cur.execute("""
        SELECT
            `Flight_Date`         AS flight_date,
            `Departure_Time`      AS departure_time,
            `Plane_ID`            AS plane_id,
            `Landing_Time`        AS landing_time,
            `Departure_Airport`   AS dep_airport,
            `Destination_Airport` AS dest_airport,
            `status`              AS status
        FROM `flights`
        WHERE `Plane_ID`=%s
          AND LOWER(`status`) NOT LIKE '%cancel%'   -- ✅ מתעלמים ממבוטלות
    """, (int(plane_id),))
    flights = cur.fetchall() or []

    for f in flights:
        start, end = flight_time_range(f)
        if end < dep_dt:
            if best_end is None or end > best_end:
                best_end = end
                best_loc = f["dest_airport"]

    return best_loc


def current_location_ok_staff(cur, flight_row, staff_id: int) -> bool:
    dep_dt = dep_datetime_from_flight(flight_row)
    last_loc = last_location_staff_before(cur, staff_id, dep_dt)
    return (last_loc is None) or (last_loc == flight_row["dep_airport"])


def current_location_ok_plane(cur, flight_row, plane_id: int) -> bool:
    dep_dt = dep_datetime_from_flight(flight_row)
    last_loc = last_location_plane_before(cur, plane_id, dep_dt)
    return (last_loc is None) or (last_loc == flight_row["dep_airport"])


# =========================================================
# J) Unified gatekeepers for assignment
# =========================================================

def can_assign_staff(cur, flight_row, staff_id: int):
    """
    Checks:
    1) ID exists in Pilot or Flight_Attendant
    2) no time conflict
    3) location constraint (first assignment allowed)
    Returns (ok, msg)
    """
    role = staff_role(cur, staff_id)
    if role is None:
        return False, "ID is not a pilot / flight_attendant"

    if has_time_conflict_staff(cur, flight_row, staff_id):
        return False, "Time conflict"

    if not current_location_ok_staff(cur, flight_row, staff_id):
        return False, "Departure airport cannot be chosen when the staff is in another airport."

    return True, ""


def can_use_plane(cur, flight_row, plane_id: int):
    """
    Checks:
    1) plane exists
    2) no time conflict
    3) location constraint (first use allowed)
    Returns (ok, msg)
    """
    if not fetch_plane_size(cur, plane_id):
        return False, "Plane not found"

    if has_time_conflict_plane(cur, flight_row, plane_id):
        return False, "Time conflict"

    if not current_location_ok_plane(cur, flight_row, plane_id):
        return False, "Departure airport cannot be chosen when the plane is in another airport."

    return True, ""


# =========================================================
# K) Price logic WITHOUT adding DB columns
#    - Use Flight_Duration for "current price per ticket"
#    - Store final locked total in Bookings.`total_price`
# =========================================================

def parse_ticket_price(value: str) -> float:
    """
    אם אצלך יש בשדה טופס של מנהל שמגדיר מספר,
    זו ולידציה בלבד (ה-"מדיניות" יכולה להיות גם base_per_hour).
    """
    s = (value or "").strip()
    if not s:
        raise ValueError("Missing price")
    try:
        p = float(s)
    except Exception:
        raise ValueError("Price must be a number")
    if p < 0:
        raise ValueError("Price must be non-negative")
    return p


def current_ticket_price_for_flight(cur, flight_date, departure_time, plane_id, base_per_hour: float = 120.0) -> float:
    """
    מחיר כרטיס נוכחי = base_per_hour * DurationHours(route)
    (אין שינוי סכימה)
    """
    a = fetch_flight_airports(cur, flight_date, departure_time, plane_id)
    if not a:
        raise ValueError("flight not found")

    dur = fetch_route_duration_hours(cur, a["dep_airport"], a["dest_airport"])
    if dur is None:
        raise ValueError("Missing route in flight_duration")

    return base_per_hour * dur


def set_booking_total_price(cur, booking_code: int, total_price: float):
    cur.execute("""
        UPDATE `bookings`
        SET `total_price`=%s
        WHERE `booking_code`=%s
    """, (float(total_price), int(booking_code)))


def lock_total_price_at_booking_time(cur, booking_code: int, flight_date, departure_time, plane_id, base_per_hour: float = 120.0) -> float:
    """
    נועל את המחיר בזמן יצירת הזמנה:
    total = (#tickets) * (current price per ticket)
    נשמר ב-Bookings.`total_price`
    """
    tickets_count = count_tickets_in_booking(cur, booking_code)
    price_per_ticket = current_ticket_price_for_flight(cur, flight_date, departure_time, plane_id, base_per_hour=base_per_hour)
    total = tickets_count * price_per_ticket
    set_booking_total_price(cur, booking_code, total)
    return total


def recalc_total_price_if_pending(cur, booking_code: int, flight_date, departure_time, plane_id, base_per_hour: float = 120.0) -> bool:
    """
    אם אתה רוצה ששינויי מנהל ישפיעו רק על הזמנות שעדיין לא סגורות:
    מעדכן total_price רק אם status == 'pending' (תשנה לפי הסטטוסים שלך!)
    """
    b = fetch_booking(cur, booking_code)
    if not b:
        raise ValueError("Booking not found")

    if (b["status"] or "").lower() != "pending":
        return False

    lock_total_price_at_booking_time(cur, booking_code, flight_date, departure_time, plane_id, base_per_hour=base_per_hour)
    return True

def update_completed_flights(mydb):
    """
    מעדכן בטבלת Flights:
    status = 'completed'
    עבור כל טיסה שזמן ההמראה שלה כבר עבר את הזמן הנוכחי,
    ורק אם היא עדיין במצב 'active'.
    """
    cur = mydb.cursor()

    try:
        cur.execute("""
            UPDATE `flights`
            SET `status` = 'completed'
            WHERE `status` = 'active'
              AND TIMESTAMP(`Flight_Date`, `Departure_Time`) < NOW()
        """)

        affected = cur.rowcount
        mydb.commit()
        return affected  # כמה טיסות עודכנו

    except Exception as e:
        mydb.rollback()
        raise e

    finally:
        cur.close()

def fetch_airports_from_flight_duration(cur):
    cur.execute("""
        SELECT DISTINCT Departure_Airport AS code FROM flight_duration
        UNION
        SELECT DISTINCT Destination_Airport AS code FROM flight_duration
        ORDER BY code
    """)
    return [r["code"] for r in (cur.fetchall() or [])]

def _fetch_available_resources(cur, flight_date, departure_time, dep_airport, dest_airport):
    """
    מחזיר:
      landing_time (מחושב),
      available_planes: list[int],
      available_pilots: list[dict{id,fname,lname}],
      available_attendants: list[dict{id,fname,lname}]
    """

    landing_time = _compute_landing_time(
        cur, dep_airport, dest_airport, flight_date, departure_time
    )

    # ---- PLANES ----
    cur.execute("SELECT `ID` AS id FROM `plane`")
    plane_ids = [r["id"] for r in (cur.fetchall() or [])]

    available_planes = []
    for pid in plane_ids:
        flight_row = _build_flight_row_for_checks(
            flight_date, departure_time, landing_time, dep_airport, dest_airport, pid
        )

        ok, _msg = can_use_plane(cur, flight_row, int(pid))
        if not ok:
            continue

        # כלל: טיסה ארוכה => רק Large
        try:
            validate_long_flight_plane_size(cur, flight_row)
        except Exception:
            continue

        available_planes.append(int(pid))

    # ---- STAFF (pilot / attendant) ----
    # לצוות לא באמת צריך plane_id "אמיתי" — הבדיקות שלך לצוות הן זמן+מיקום.
    # נשתמש ב-1 כדי לבנות flight_row, זה לא אמור להשפיע על can_assign_staff.
    staff_flight_row = _build_flight_row_for_checks(
        flight_date, departure_time, landing_time, dep_airport, dest_airport, 1
    )

    # ---- PILOTS ----
    cur.execute("SELECT `ID` AS id, `fname` AS fname, `lname` AS lname FROM `pilot`")
    pilots = cur.fetchall() or []

    available_pilots = []
    for p in pilots:
        ok, _msg = can_assign_staff(cur, staff_flight_row, int(p["id"]))
        if ok:
            available_pilots.append({
                "id": int(p["id"]),
                "fname": p.get("fname"),
                "lname": p.get("lname"),
            })

    # ---- ATTENDANTS ----
    cur.execute("SELECT `ID` AS id, `fname` AS fname, `lname` AS lname FROM `flight_attendant`")
    attendants = cur.fetchall() or []

    available_attendants = []
    for a in attendants:
        ok, _msg = can_assign_staff(cur, staff_flight_row, int(a["id"]))
        if ok:
            available_attendants.append({
                "id": int(a["id"]),
                "fname": a.get("fname"),
                "lname": a.get("lname"),
            })

    return landing_time, available_planes, available_pilots, available_attendants


def _normalize_date(d):
    if isinstance(d, date):
        return d
    return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()

def _normalize_time(t):
    if isinstance(t, time):
        return t
    s = str(t).split(".")[0]
    # יכול להגיע HH:MM
    if len(s) == 5:
        s += ":00"
    return datetime.strptime(s, "%H:%M:%S").time()

def _compute_landing_time(cur, dep_airport, dest_airport, flight_date, departure_time):
    """
    Landing_Time מחושב לפי Flight_Duration:
    landing_dt = dep_dt + duration_hours
    נשמור רק את ה-time לטבלת Flights.
    """
    dur = fetch_route_duration_hours(cur, dep_airport, dest_airport)
    if dur is None:
        raise ValueError("Missing route in flight_duration for this route.")

    dep_dt = datetime.combine(flight_date, departure_time)
    land_dt = dep_dt + timedelta(hours=float(dur))
    return land_dt.time()

def _build_flight_row_for_checks(flight_date, departure_time, landing_time, dep_airport, dest_airport, plane_id):
    return {
        "flight_date": flight_date,
        "departure_time": departure_time,
        "landing_time": landing_time,
        "dep_airport": dep_airport,
        "dest_airport": dest_airport,
        "plane_id": int(plane_id),
        "status": "active"
    }

def _flight_capacity_for_plane(classes_rows):
    # classes_rows: list of dicts with Number_of_Rows/Number_of_Columns
    cap = 0
    for c in classes_rows:
        cap += int(c["Number_of_Rows"]) * int(c["Number_of_Columns"])
    return cap
