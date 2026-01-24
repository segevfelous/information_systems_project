#2
WITH
-- כל היצרנים/גדלים שקיימים בצי
dims AS (
    SELECT DISTINCT
        p.Size,
        p.Manufacturer
    FROM plane p
),

-- שתי המחלקות הנדרשות
class_dim AS (
    SELECT 'business' AS Class_Type
    UNION ALL
    SELECT 'economy'
),

-- כל השילובים (כדי להציג גם הכנסה 0)
-- ✅ תיקון: מטוס קטן לא מציג מחלקת ביזנס
all_combinations AS (
    SELECT
        d.Size,
        d.Manufacturer,
        c.Class_Type
    FROM dims d
    CROSS JOIN class_dim c
    WHERE NOT (
        LOWER(TRIM(d.Size)) = 'small'
        AND LOWER(TRIM(c.Class_Type)) = 'business'
    )
),

-- טווחי שורות לכל מחלקה במטוס (business קודם ואז economy)
class_blocks AS (
    SELECT
        c.Plane_ID,
        LOWER(c.Class_Type) AS Class_Type,
        COALESCE(
            SUM(c.Number_of_Rows) OVER (
                PARTITION BY c.Plane_ID
                ORDER BY CASE LOWER(c.Class_Type) WHEN 'business' THEN 1 ELSE 2 END
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ),
            0
        ) + 1 AS start_row,
        SUM(c.Number_of_Rows) OVER (
            PARTITION BY c.Plane_ID
            ORDER BY CASE LOWER(c.Class_Type) WHEN 'business' THEN 1 ELSE 2 END
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS end_row
    FROM classes c
    WHERE LOWER(c.Class_Type) IN ('business','economy')
),

-- כמה כרטיסים יש בכל הזמנה (כדי לחלק total_price בין הכרטיסים)
tickets_per_booking AS (
    SELECT
        booking_code,
        COUNT(*) AS ticket_count
    FROM tickets
    GROUP BY booking_code
),

-- כל כרטיס מסווג למחלקה ומקבל "חלק יחסי" מה-total_price של ההזמנה
ticket_revenue AS (
    SELECT
        p.Size,
        p.Manufacturer,
        cb.Class_Type,
        (b.total_price / tp.ticket_count) AS ticket_amount
    FROM tickets t
    JOIN bookings b
      ON b.booking_code = t.booking_code
    JOIN tickets_per_booking tp
      ON tp.booking_code = t.booking_code
    JOIN flights f
      ON f.Flight_Date = t.flight_date
     AND f.Departure_Time = t.departure_time
    JOIN plane p
      ON p.ID = f.Plane_ID
    JOIN class_blocks cb
      ON cb.Plane_ID = f.Plane_ID
     AND t.row BETWEEN cb.start_row AND cb.end_row

    -- ✅ תיקון: לא מחשבים בכלל revenue ל-business במטוס קטן
    WHERE NOT (
        LOWER(TRIM(p.Size)) = 'small'
        AND LOWER(TRIM(cb.Class_Type)) = 'business'
    )
),

-- סיכום הכנסות בפועל לכל שילוב
revenue_by_group AS (
    SELECT
        Size,
        Manufacturer,
        Class_Type,
        ROUND(SUM(ticket_amount), 2) AS revenue
    FROM ticket_revenue
    GROUP BY Size, Manufacturer, Class_Type
)

-- החזרה של כל השילובים + 0 איפה שאין הכנסות
SELECT
    ac.Size,
    ac.Manufacturer,
    ac.Class_Type,
    COALESCE(rg.revenue, 0) AS revenue
FROM all_combinations ac
LEFT JOIN revenue_by_group rg
  ON rg.Size = ac.Size
 AND rg.Manufacturer = ac.Manufacturer
 AND rg.Class_Type = ac.Class_Type
ORDER BY ac.Manufacturer, ac.Size, ac.Class_Type;

#3
WITH completed_flights AS (
    SELECT
        f.Flight_Date,
        f.Departure_Time,
        f.Plane_ID,
        fd.Duration_in_Hours,
        CASE
            WHEN fd.Duration_in_Hours > 6 THEN 'long'
            ELSE 'short'
        END AS flight_type
    FROM flights f
    JOIN flight_duration fd
      ON fd.Departure_Airport = f.Departure_Airport
     AND fd.Destination_Airport = f.Destination_Airport
    WHERE f.status = 'completed'   -- רק טיסות שהתקיימו
),
valid_employees AS (
    SELECT ID FROM pilot
    UNION
    SELECT ID FROM flight_attendant
),
employee_flight_hours AS (
    SELECT
        sof.ID AS employee_id,
        cf.flight_type,
        cf.Duration_in_Hours
    FROM staff_on_flight sof
    JOIN completed_flights cf
      ON cf.Flight_Date = sof.flight_date
     AND cf.Departure_Time = sof.departure_time
     AND cf.Plane_ID = sof.plane_ID
    JOIN valid_employees ve
      ON ve.ID = sof.ID
),
types AS (
    SELECT 'short' AS flight_type
    UNION ALL
    SELECT 'long'
)
SELECT
    ve.ID AS ID,
    t.flight_type,
    ROUND(COALESCE(SUM(CASE WHEN efh.flight_type = t.flight_type THEN efh.Duration_in_Hours END), 0), 2) AS total_hours
FROM valid_employees ve
CROSS JOIN types t
LEFT JOIN employee_flight_hours efh
  ON efh.employee_id = ve.ID
 AND efh.flight_type = t.flight_type
GROUP BY ve.ID, t.flight_type
ORDER BY ve.ID, t.flight_type;

#4
SELECT
    DATE_FORMAT(booking_date, '%b-%Y') AS month_label,  -- לדוגמה: Jan-2026
    ROUND(
        1.0 * SUM(CASE WHEN status = 'customer cancelled' THEN 1 ELSE 0 END) / COUNT(*),
        4
    ) AS customer_cancellation_rate
FROM bookings
GROUP BY DATE_FORMAT(booking_date, '%Y-%m'), DATE_FORMAT(booking_date, '%b-%Y')
ORDER BY DATE_FORMAT(booking_date, '%Y-%m');

#5
WITH flights_norm AS (
    SELECT
        f.Plane_ID,
        f.Flight_Date,
        f.Departure_Time,
        f.Departure_Airport,
        f.Destination_Airport,
        DATE_FORMAT(f.Flight_Date, '%Y-%m') AS ym,
        DATE_FORMAT(f.Flight_Date, '%b-%Y') AS month_label,
        LOWER(TRIM(f.status)) AS flight_status
    FROM flights f
    WHERE f.Flight_Date <= CURDATE()   -- רק חודשים שכבר הגיעו
),

/* טיסות שבוצעו בפועל */
completed_counts AS (
    SELECT
        Plane_ID,
        ym,
        MAX(month_label) AS month_label,
        COUNT(*) AS flights_completed
    FROM flights_norm
    WHERE flight_status = 'completed'
    GROUP BY Plane_ID, ym
),

/* טיסות שבוטלו (ביטול טיסה אמיתי ע"י FLYTAU) */
flytau_cancelled_counts AS (
    SELECT
        Plane_ID,
        ym,
        MAX(month_label) AS month_label,
        COUNT(*) AS flights_flytau_cancelled
    FROM flights_norm
    WHERE flight_status = 'flytau cancelled'
    GROUP BY Plane_ID, ym
),

/* בסיס חודשי: כל מטוס-חודש שיש בו ביצוע או ביטול טיסה */
plane_months AS (
    SELECT Plane_ID, ym, month_label FROM completed_counts
    UNION
    SELECT Plane_ID, ym, month_label FROM flytau_cancelled_counts
),

/* ניצולת: ימים שבהם הייתה לפחות המראה אחת של טיסה שלא בוטלה */
utilization_days AS (
    SELECT
        Plane_ID,
        ym,
        COUNT(DISTINCT Flight_Date) AS days_with_departure
    FROM flights_norm
    WHERE flight_status <> 'flytau cancelled'
    GROUP BY Plane_ID, ym
),

/* מסלול שולט: בין טיסות שלא בוטלו */
route_counts AS (
    SELECT
        Plane_ID,
        ym,
        Departure_Airport,
        Destination_Airport,
        COUNT(*) AS route_count
    FROM flights_norm
    WHERE flight_status <> 'flytau cancelled'
    GROUP BY Plane_ID, ym, Departure_Airport, Destination_Airport
),

dominant_route AS (
    SELECT
        Plane_ID,
        ym,
        CONCAT(Departure_Airport, '-', Destination_Airport) AS dominant_route_pair
    FROM (
        SELECT
            Plane_ID,
            ym,
            Departure_Airport,
            Destination_Airport,
            route_count,
            ROW_NUMBER() OVER (
                PARTITION BY Plane_ID, ym
                ORDER BY route_count DESC, Departure_Airport, Destination_Airport
            ) AS rn
        FROM route_counts
    ) r
    WHERE rn = 1
)

SELECT
    pm.Plane_ID,
    pm.month_label,
    COALESCE(cc.flights_completed, 0) AS flights_completed,
    COALESCE(fc.flights_flytau_cancelled, 0) AS flights_flytau_cancelled,
    ROUND(100 * COALESCE(ud.days_with_departure, 0) / 30, 2) AS utilization_percent,
    dr.dominant_route_pair
FROM plane_months pm
LEFT JOIN completed_counts cc
  ON cc.Plane_ID = pm.Plane_ID AND cc.ym = pm.ym
LEFT JOIN flytau_cancelled_counts fc
  ON fc.Plane_ID = pm.Plane_ID AND fc.ym = pm.ym
LEFT JOIN utilization_days ud
  ON ud.Plane_ID = pm.Plane_ID AND ud.ym = pm.ym
LEFT JOIN dominant_route dr
  ON dr.Plane_ID = pm.Plane_ID AND dr.ym = pm.ym
ORDER BY pm.Plane_ID, pm.ym;

