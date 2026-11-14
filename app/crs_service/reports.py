"""Claims summary reports.

The reference estate runs the database as a protocol stub, so report rows are
generated deterministically from the business date. The shape matches what the
reporting database view (``reporting.v_claims_daily``) returns.
"""

from __future__ import annotations

import random
from datetime import date

STATUSES = ("PAID", "PAID", "PAID", "PENDED", "DENIED", "ADJUSTED")
LINES_OF_BUSINESS = ("COMMERCIAL", "MEDICARE_ADV", "MEDICAID", "INDIVIDUAL")


def claims_summary(business_date: date) -> list[dict]:
    rng = random.Random(business_date.toordinal())
    rows = []
    for lob in LINES_OF_BUSINESS:
        for status in sorted(set(STATUSES)):
            count = rng.randint(40, 900)
            rows.append({
                "business_date": business_date.isoformat(),
                "line_of_business": lob,
                "status": status,
                "claim_count": count,
                "billed_amount": round(count * rng.uniform(180, 1400), 2),
            })
    return rows
