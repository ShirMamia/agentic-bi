"""In-memory sales fixture adapted from the approved teaching notebook."""

import sqlite3


def build_warehouse() -> sqlite3.Connection:
    """Seed a fresh database with the fictional classroom data."""
    con = sqlite3.connect(":memory:")
    cur = con.cursor()

    cur.executescript("""
    CREATE TABLE dim_date (
        date_id INTEGER PRIMARY KEY,
        date TEXT NOT NULL,
        month TEXT NOT NULL,
        week INTEGER NOT NULL,
        is_weekend INTEGER NOT NULL
    );

    CREATE TABLE dim_city (
        city_id INTEGER PRIMARY KEY,
        city TEXT NOT NULL,
        region TEXT NOT NULL
    );

    CREATE TABLE dim_product (
        product_id INTEGER PRIMARY KEY,
        category TEXT NOT NULL
    );

    CREATE TABLE fact_daily_sales (
        date_id INTEGER NOT NULL,
        city_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        gross_revenue REAL NOT NULL,
        discounts REAL NOT NULL,
        refunds REAL NOT NULL,
        orders INTEGER NOT NULL,
        checkout_attempts INTEGER NOT NULL,
        payment_failures INTEGER NOT NULL,
        cancellations INTEGER NOT NULL,
        avg_delivery_minutes REAL NOT NULL,
        FOREIGN KEY(date_id) REFERENCES dim_date(date_id),
        FOREIGN KEY(city_id) REFERENCES dim_city(city_id),
        FOREIGN KEY(product_id) REFERENCES dim_product(product_id)
    );
    """)

    cities = [(1, "Haifa", "North"), (2, "Tel Aviv", "Center"), (3, "Jerusalem", "Center"), (4, "Beer Sheva", "South")]
    products = [(1, "Electronics"), (2, "Home"), (3, "Fashion")]
    cur.executemany("INSERT INTO dim_city VALUES (?, ?, ?)", cities)
    cur.executemany("INSERT INTO dim_product VALUES (?, ?)", products)

    calendar = []
    date_id = 1
    for month, dates in {
        "2026-05": ["2026-05-03", "2026-05-10", "2026-05-17", "2026-05-24"],
        "2026-06": ["2026-06-07", "2026-06-14", "2026-06-21", "2026-06-28"]
    }.items():
        for week, d in enumerate(dates, start=1):
            calendar.append((date_id, d, month, week, 0))
            date_id += 1
    cur.executemany("INSERT INTO dim_date VALUES (?, ?, ?, ?, ?)", calendar)

    rows = []
    for date_id, d, month, week, _ in calendar:
        for city_id, city, region in cities:
            for product_id, category in products:
                base_orders = {"Haifa": 120, "Tel Aviv": 180, "Jerusalem": 140, "Beer Sheva": 80}[city]
                price = {"Electronics": 95, "Home": 60, "Fashion": 45}[category]
                multiplier = 1.0
                cancellations = 4
                delivery = 34
                payment_failures = 3
                attempts_extra = 8
                discounts_rate = 0.06
                refunds_rate = 0.02

                if month == "2026-06" and city == "Haifa":
                    multiplier = 0.56
                    cancellations = 26
                    delivery = 79
                    payment_failures = 4
                    attempts_extra = 12
                elif month == "2026-06" and city in ["Tel Aviv", "Jerusalem"]:
                    multiplier = 1.02
                    delivery = 35
                elif month == "2026-06" and city == "Beer Sheva":
                    multiplier = 0.98

                orders = int(base_orders * multiplier * {"Electronics": 0.7, "Home": 1.0, "Fashion": 0.9}[category])
                gross = orders * price
                discounts = gross * discounts_rate
                refunds = gross * refunds_rate
                attempts = orders + cancellations + attempts_extra
                rows.append((date_id, city_id, product_id, gross, discounts, refunds, orders, attempts, payment_failures, cancellations, delivery))

    cur.executemany("""
    INSERT INTO fact_daily_sales
    (date_id, city_id, product_id, gross_revenue, discounts, refunds, orders, checkout_attempts, payment_failures, cancellations, avg_delivery_minutes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    con.commit()
    return con
