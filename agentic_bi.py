"""Run a fixed BI investigation over a synthetic SQLite warehouse."""

from dataclasses import dataclass
from sqlite3 import Connection


NET_REVENUE = "SUM(f.gross_revenue - f.discounts - f.refunds)"
CITY_SQL = f"""
SELECT c.city, d.month, ROUND({NET_REVENUE}, 2)
FROM fact_daily_sales f
JOIN dim_date d ON f.date_id = d.date_id
JOIN dim_city c ON f.city_id = c.city_id
WHERE c.region = ? AND d.month IN (?, ?)
GROUP BY c.city, d.month
ORDER BY c.city, d.month
"""
OPERATIONS_SQL = """
SELECT d.month, SUM(f.orders), SUM(f.cancellations) * 1.0 / NULLIF(SUM(f.checkout_attempts), 0),
       SUM(f.payment_failures) * 1.0 / NULLIF(SUM(f.checkout_attempts), 0),
       SUM(f.avg_delivery_minutes * f.orders) / NULLIF(SUM(f.orders), 0)
FROM fact_daily_sales f
JOIN dim_date d ON f.date_id = d.date_id
JOIN dim_city c ON f.city_id = c.city_id
WHERE c.region = ? AND c.city = ? AND d.month IN (?, ?)
GROUP BY d.month
"""


@dataclass(frozen=True)
class Context:
    city: str
    period: str
    topic: str
    text: str


DELIVERY_CONTEXT = Context(
    "Haifa", "2026-06", "delivery",
    "In this fictional scenario, roadworks disrupted some delivery routes.",
)
NOISY_CONTEXT = (
    Context("Haifa", "2026-06", "sports", "A football team won a match."),
    Context("Haifa", "2026-05", "delivery", "A past delivery disruption was reported."),
    Context("Tel Aviv", "2026-06", "delivery", "Another city reported roadworks."),
)


def _delta_line(label, before, after, scale, unit):
    if before is None or after is None:
        return f"{label}: unavailable for comparison."
    return f"{label}: {(after - before) * scale:+.2f}{unit}."


def investigate(
    database: Connection,
    region: str,
    baseline: str,
    current: str,
    contexts: tuple[Context, ...] = (),
) -> dict:
    """Compare two periods, follow the largest negative city change, and report evidence."""
    if baseline >= current:
        raise ValueError("Specify an earlier baseline and a later current period.")
    city_period_rows = database.execute(CITY_SQL, (region, baseline, current)).fetchall()
    prior = {city: value for city, month, value in city_period_rows if month == baseline}
    recent = {city: value for city, month, value in city_period_rows if month == current}
    result = {
        "metric": NET_REVENUE,
        "region": region,
        "periods": (baseline, current),
        "city_period_rows": city_period_rows,
        "focus_city": None,
        "accepted_context": [],
        "excluded_context": len(contexts),
    }
    if not prior or prior.keys() != recent.keys():
        return {
            **result,
            "status": "insufficient_data",
            "finding": "The periods need comparable data for the same cities.",
        }

    changes = {city: round(recent[city] - prior[city], 2) for city in prior}
    change = round(sum(changes.values()), 2)
    direction = "fell" if change < 0 else "rose" if change > 0 else "was unchanged"
    result.update(
        status="decline" if change < 0 else "no_decline",
        baseline_revenue=round(sum(prior.values()), 2),
        current_revenue=round(sum(recent.values()), 2),
        revenue_change=change,
        city_changes=changes,
        finding=f"Net revenue in {region} {direction} ({change:+,.2f}) from {baseline} to {current}.",
    )
    if change >= 0:
        return result

    city = min(changes, key=changes.__getitem__)
    operations = {
        month: values
        for month, *values in database.execute(OPERATIONS_SQL, (region, city, baseline, current))
    }
    old, new = operations[baseline], operations[current]
    delivery_pressure = all(
        old[index] is not None and new[index] is not None and new[index] > old[index]
        for index in (1, 3)
    )
    accepted = [
        item.text for item in contexts
        if delivery_pressure and (item.city, item.period, item.topic) == (city, current, "delivery")
    ]
    result.update(
        focus_city=city,
        finding=f"{result['finding']} The largest negative city change was {city} ({changes[city]:+,.2f}).",
        operational_evidence=[
            _delta_line("Orders", old[0], new[0], 1, ""),
            _delta_line("Cancellation rate", old[1], new[1], 100, " percentage points"),
            _delta_line("Payment failure rate", old[2], new[2], 100, " percentage points"),
            _delta_line("Order-weighted delivery time", old[3], new[3], 1, " minutes"),
        ],
        accepted_context=accepted,
        excluded_context=len(contexts) - len(accepted),
        interpretation=(
            "Rising cancellation rates and delivery times support investigating delivery capacity."
            if delivery_pressure else
            "The cancellation and delivery measures do not jointly support a delivery-capacity hypothesis."
        ),
        caveat="The warehouse comparison and fictional context are observational evidence.",
    )
    return result
