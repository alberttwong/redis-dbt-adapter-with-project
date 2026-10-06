# Each pickup date's revenue as a z-score: how many standard deviations it is
# from the month's daily mean. A Python model: dbt runs it in its own process,
# with agg_daily_revenue read as a pyarrow Table, and bulk-ingests the result.

import pyarrow.compute as pc


def model(dbt, session):
    daily = dbt.ref("agg_daily_revenue").select(["pickup_date", "trips", "total_revenue"])
    revenue = daily["total_revenue"]
    zscore = pc.divide(pc.subtract(revenue, pc.mean(revenue)), pc.stddev(revenue, ddof=1))
    return daily.append_column("revenue_zscore", pc.round(zscore, 3)).sort_by("pickup_date")
