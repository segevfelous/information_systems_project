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
),

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

/* --- טיסות ייחודיות שבוטלו לפי BOOKING, משויכות למטוס דרך tickets->flights --- */
booking_flights_cancel AS (
    SELECT DISTINCT
        f.Plane_ID,
        f.Flight_Date,
        f.Departure_Time,
        DATE_FORMAT(f.Flight_Date, '%Y-%m') AS ym,
        DATE_FORMAT(f.Flight_Date, '%b-%Y') AS month_label,
        LOWER(TRIM(b.status)) AS booking_status
    FROM bookings b
    JOIN tickets t
      ON t.booking_code = b.booking_code
    JOIN flights f
      ON f.Flight_Date = t.flight_date
     AND f.Departure_Time = t.departure_time
    WHERE LOWER(TRIM(b.status)) IN ('customer cancelled', 'flytau cancelled')
),

/* כאן הספירה היא על טיסות ייחודיות (Plane_ID + Flight_Date + Departure_Time) */
customer_cancelled_counts AS (
    SELECT
        Plane_ID,
        ym,
        MAX(month_label) AS month_label,
        COUNT(DISTINCT CONCAT(Plane_ID,'|',Flight_Date,'|',Departure_Time)) AS flights_customer_cancelled
    FROM booking_flights_cancel
    WHERE booking_status = 'customer cancelled'
    GROUP BY Plane_ID, ym
),

flytau_cancelled_counts AS (
    SELECT
        Plane_ID,
        ym,
        MAX(month_label) AS month_label,
        COUNT(DISTINCT CONCAT(Plane_ID,'|',Flight_Date,'|',Departure_Time)) AS flights_flytau_cancelled
    FROM booking_flights_cancel
    WHERE booking_status = 'flytau cancelled'
    GROUP BY Plane_ID, ym
),

plane_months AS (
    SELECT Plane_ID, ym, month_label FROM completed_counts
    UNION
    SELECT Plane_ID, ym, month_label FROM customer_cancelled_counts
    UNION
    SELECT Plane_ID, ym, month_label FROM flytau_cancelled_counts
),

utilization_days AS (
    SELECT
        Plane_ID,
        ym,
        COUNT(DISTINCT Flight_Date) AS days_with_departure
    FROM flights_norm
    WHERE flight_status = 'completed'
    GROUP BY Plane_ID, ym
),

route_counts AS (
    SELECT
        Plane_ID,
        ym,
        Departure_Airport,
        Destination_Airport,
        COUNT(*) AS route_count
    FROM flights_norm
    WHERE flight_status = 'completed'
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
    COALESCE(cu.flights_customer_cancelled, 0) AS flights_customer_cancelled,
    COALESCE(fc.flights_flytau_cancelled, 0) AS flights_flytau_cancelled,
    ROUND(100 * COALESCE(ud.days_with_departure, 0) / 30, 2) AS utilization_percent,
    dr.dominant_route_pair
FROM plane_months pm
LEFT JOIN completed_counts cc
  ON cc.Plane_ID = pm.Plane_ID AND cc.ym = pm.ym
LEFT JOIN customer_cancelled_counts cu
  ON cu.Plane_ID = pm.Plane_ID AND cu.ym = pm.ym
LEFT JOIN flytau_cancelled_counts fc
  ON fc.Plane_ID = pm.Plane_ID AND fc.ym = pm.ym
LEFT JOIN utilization_days ud
  ON ud.Plane_ID = pm.Plane_ID AND ud.ym = pm.ym
LEFT JOIN dominant_route dr
  ON dr.Plane_ID = pm.Plane_ID AND dr.ym = pm.ym
ORDER BY pm.Plane_ID, pm.ym;
