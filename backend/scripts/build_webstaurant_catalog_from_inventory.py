#!/usr/bin/env python3
"""Build a Webstaurant UPC CSV from standalone_inventory order URLs.

This script scrapes Webstaurant product pages referenced in standalone inventory
rows and emits a CSV ready for import via scripts/import_inventory_product_catalog.py.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = SCRIPT_DIR.parent / "data" / "retreat_ops.db"
DEFAULT_OUTPUT_CSV = Path("/tmp/webstaurant_upcs_from_inventory.csv")

UPC_RE = re.compile(r'"upc"\s*:\s*"(\d{8,14})"', re.IGNORECASE)
TITLE_RE = re.compile(r'"title"\s*:\s*"([^"]{3,400})"')
VENDOR_RE = re.compile(r'"sourceVendor"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"', re.IGNORECASE)
IMAGE_RE = re.compile(
    r'"openGraphMeta"\s*:\s*\{.*?"image"\s*:\s*"([^"]+)"',
    re.IGNORECASE | re.DOTALL,
)
ITEM_NUMBER_RE = re.compile(r'"itemNumber"\s*:\s*"([A-Za-z0-9\-]+)"')
OG_TITLE_RE = re.compile(r'<meta\s+property="og:title"\s+content="([^"]+)"', re.IGNORECASE)
WEBSTAURANT_HOST_RE = re.compile(r"(^|\.)webstaurantstore\.com$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Webstaurant UPC catalog CSV from standalone_inventory.order_url."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help=f"SQLite DB path (default: {DEFAULT_DB_PATH})")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT_CSV})",
    )
    parser.add_argument("--max-urls", type=int, default=0, help="Limit number of unique URLs to fetch (0 = all)")
    parser.add_argument("--timeout-seconds", type=float, default=25.0, help="HTTP timeout per request")
    parser.add_argument("--delay-seconds", type=float, default=0.25, help="Delay between requests")
    parser.add_argument("--verbose", action="store_true", help="Print per-URL status")
    return parser.parse_args()


def normalize_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text if text else None


def decode_web_text(value: str | None) -> str | None:
    if not value:
        return None
    text = value
    text = text.replace("\\/", "/").replace('\\"', '"')
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    text = html.unescape(text)
    text = text.strip()
    return text or None


def normalize_url(raw_url: str | None) -> str | None:
    value = str(raw_url or "").strip()
    if not value:
        return None
    parsed = urlsplit(value)
    if not parsed.scheme:
        parsed = urlsplit("https://" + value)
    if parsed.scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower()
    if not WEBSTAURANT_HOST_RE.search(host):
        return None
    normalized = urlunsplit((parsed.scheme, host, parsed.path, "", ""))
    return normalized


def extract_source_sku_from_url(url: str) -> str | None:
    path = urlsplit(url).path or ""
    tail = path.rsplit("/", 1)[-1]
    if not tail.lower().endswith(".html"):
        return None
    code = tail[:-5]
    if not code:
        return None
    if "/" in code:
        return None
    return code.upper()


def pick_preferred(current: str | None, candidate: str | None) -> str | None:
    if current:
        return current
    return candidate


def fetch_page(url: str, timeout_seconds: float) -> tuple[str, str]:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(req, timeout=timeout_seconds) as resp:
        final_url = normalize_url(resp.geturl()) or url
        body = resp.read().decode("utf-8", errors="ignore")
    return final_url, body


def extract_page_metadata(page_html: str) -> dict[str, str | None]:
    upc_match = UPC_RE.search(page_html)
    title_match = TITLE_RE.search(page_html)
    vendor_match = VENDOR_RE.search(page_html)
    image_match = IMAGE_RE.search(page_html)
    item_number_match = ITEM_NUMBER_RE.search(page_html)
    og_title_match = OG_TITLE_RE.search(page_html)

    title = decode_web_text(title_match.group(1)) if title_match else None
    if not title and og_title_match:
        title = decode_web_text(og_title_match.group(1))

    metadata = {
        "upc": upc_match.group(1) if upc_match else None,
        "title": title,
        "brand": decode_web_text(vendor_match.group(1)) if vendor_match else None,
        "image_url": decode_web_text(image_match.group(1)) if image_match else None,
        "source_sku": decode_web_text(item_number_match.group(1)) if item_number_match else None,
    }
    return metadata


def main() -> None:
    args = parse_args()
    if not args.db.exists():
        raise FileNotFoundError(f"DB not found: {args.db}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, item_name, category, unit, order_url
            FROM standalone_inventory
            WHERE order_url IS NOT NULL
              AND trim(order_url) != ''
              AND lower(order_url) LIKE '%webstaurantstore.com%'
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    by_url: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        normalized_url = normalize_url(row["order_url"])
        if not normalized_url:
            continue
        by_url[normalized_url].append(row)

    urls = sorted(by_url.keys())
    if args.max_urls and args.max_urls > 0:
        urls = urls[: args.max_urls]

    catalog_by_upc: dict[str, dict[str, str]] = {}
    fetch_ok = 0
    fetch_fail = 0
    no_upc = 0

    for index, url in enumerate(urls, start=1):
        status = "ok"
        final_url = url
        upc = None
        try:
            final_url, page_html = fetch_page(url, timeout_seconds=max(1.0, args.timeout_seconds))
            metadata = extract_page_metadata(page_html)
            upc = metadata.get("upc")
            if not upc:
                status = "no_upc"
                no_upc += 1
            else:
                fetch_ok += 1
                linked_rows = by_url[url]
                item_names = [normalize_text(r["item_name"]) for r in linked_rows]
                categories = [normalize_text(r["category"]) for r in linked_rows]
                units = [normalize_text(r["unit"]) for r in linked_rows]

                local_name = next((v for v in item_names if v), None)
                local_category = next((v for v in categories if v), None)
                local_unit = next((v for v in units if v), None)
                source_row_ids = ",".join(str(int(r["id"])) for r in linked_rows)

                row_data = {
                    "barcode": upc,
                    "product_name": pick_preferred(metadata.get("title"), local_name) or "",
                    "brand": metadata.get("brand") or "",
                    "category": local_category or "",
                    "unit": local_unit or "",
                    "image_url": metadata.get("image_url") or "",
                    "product_url": final_url,
                    "source_sku": metadata.get("source_sku") or extract_source_sku_from_url(final_url) or "",
                    "notes": f"scraped_from=standalone_inventory; source_row_ids={source_row_ids}",
                }
                existing = catalog_by_upc.get(upc)
                if existing:
                    for key in ("product_name", "brand", "category", "unit", "image_url", "product_url", "source_sku"):
                        if not existing.get(key) and row_data.get(key):
                            existing[key] = row_data[key]
                    existing_notes = str(existing.get("notes", ""))
                    if source_row_ids and source_row_ids not in existing_notes:
                        existing["notes"] = f"{existing_notes}; source_row_ids+={source_row_ids}"
                else:
                    catalog_by_upc[upc] = row_data
        except Exception as exc:
            fetch_fail += 1
            status = f"error: {exc}"

        if args.verbose:
            print(f"[{index}/{len(urls)}] {status} :: {url}")

        if index < len(urls) and args.delay_seconds > 0:
            time.sleep(max(0.0, args.delay_seconds))

    out_rows = [catalog_by_upc[k] for k in sorted(catalog_by_upc.keys())]
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "barcode",
                "product_name",
                "brand",
                "category",
                "unit",
                "image_url",
                "product_url",
                "source_sku",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"standalone_inventory rows with Webstaurant URLs: {len(rows)}")
    print(f"unique URLs fetched: {len(urls)}")
    print(f"fetch_ok_with_upc: {fetch_ok}")
    print(f"fetch_fail: {fetch_fail}")
    print(f"fetched_without_upc: {no_upc}")
    print(f"unique UPC rows emitted: {len(out_rows)}")
    print(f"output_csv: {args.output_csv}")


if __name__ == "__main__":
    main()
