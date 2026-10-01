import json
import os
import sys
from datetime import datetime, timezone

import requests


RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
API_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

CONFIG_FILE = "mandi_config.json"
OUTPUT_FILE = "mandi_data.json"

API_KEY = os.environ.get("DATA_GOV_API_KEY")

if not API_KEY:
    print("ERROR: DATA_GOV_API_KEY GitHub Secret is not configured.")
    sys.exit(1)


with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)


states = config["supported_states"]
priority_commodities = {
    str(x).strip().lower()
    for x in config["priority_commodities"]
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def commodity_matches(value):
    name = clean(value).lower()

    if not name:
        return False

    return any(
        target in name or name in target
        for target in priority_commodities
    )


records = []

for state in states:
    print(f"Fetching: {state}")

    offset = 0
    page_size = 1000

    while True:
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": page_size,
            "offset": offset,
            "filters[State]": state
        }

        response = requests.get(
            API_URL,
            params=params,
            timeout=60,
            headers={
                "User-Agent": "AgriGuard2.0-Mandi-Updater"
            }
        )

        response.raise_for_status()

        payload = response.json()
        page = payload.get("records", [])

        if not page:
            break

        for row in page:
            commodity = clean(
                row.get("Commodity") or
                row.get("commodity")
            )

            if not commodity_matches(commodity):
                continue

            records.append({
                "state": clean(row.get("State")),
                "district": clean(row.get("District")),
                "market": clean(row.get("Market")),
                "commodity": commodity,
                "variety": clean(row.get("Variety")),
                "grade": clean(row.get("Grade")),
                "arrival_date": clean(
                    row.get("Arrival_Date") or
                    row.get("arrival_date")
                ),
                "min_price": clean(
                    row.get("Min_Price") or
                    row.get("min_price")
                ),
                "max_price": clean(
                    row.get("Max_Price") or
                    row.get("max_price")
                ),
                "modal_price": clean(
                    row.get("Modal_Price") or
                    row.get("modal_price")
                )
            })

        print(
            f"  received {len(page)} records "
            f"(offset {offset})"
        )

        if len(page) < page_size:
            break

        offset += page_size


output = {
    "source": "Government of India — AGMARKNET / data.gov.in",
    "resource_id": RESOURCE_ID,
    "region": config["region"],
    "price_unit": config["price_unit"],
    "update_frequency": config["granularity"],
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "record_count": len(records),
    "records": records
}


with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("✓ Mandi data generated")
print("Filtered records:", len(records))
print("Output:", OUTPUT_FILE)
