#!/usr/bin/env python3
"""Build an IKEA catalog CSV from standalone_inventory order URLs.

This script scrapes IKEA product pages referenced in standalone_inventory rows
and emits a CSV ready for import via scripts/import_inventory_product_catalog.py.

If an explicit UPC/GTIN is not available on the page, it falls back to the
IKEA article number extracted from the URL (8 digits) as `barcode`.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = SCRIPT_DIR.parent / "data" / "retreat_ops.db"
DEFAULT_OUTPUT_CSV = Path("/tmp/ikea_catalog_from_inventory.csv")

BARCODE_RE = re.compile(r"^\d{8,14}$")
BARCODE_HINT_RE = re.compile(
    r'"(?:upc|gtin|ean(?:13)?|globalTradeItemNumber|barcode)"\s*:\s*"(\d{8,14})"',
    re.IGNORECASE,
)
JSON_LD_PIP_RE = re.compile(
    r'<script[^>]+id="pip-range-json-ld"[^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
OG_TITLE_RE = re.compile(r'<meta\s+property="og:title"\s+content="([^"]+)"', re.IGNORECASE)
OG_IMAGE_RE = re.compile(r'<meta\s+property="og:image"\s+content="([^"]+)"', re.IGNORECASE)
IKEA_HOST_RE = re.compile(r"(^|\.)ikea\.com$", re.IGNORECASE)
IKEA_URL_SKU_RE = re.compile(r"-([0-9]{8})/?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build IKEA catalog CSV from standalone_inventory.order_url and optional manual URLs."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help=f"SQLite DB path (default: {DEFAULT_DB_PATH})")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT_CSV})",
    )
    parser.add_argument("--url", action="append", default=[], help="Extra IKEA product URL to include (repeatable)")
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


def normalize_barcode(value: object) -> str | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    if not BARCODE_RE.fullmatch(digits):
        return None
    return digits


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
    if not IKEA_HOST_RE.search(host):
        return None
    normalized = urlunsplit((parsed.scheme, host, parsed.path, "", ""))
    return normalized


def extract_source_sku_from_url(url: str) -> str | None:
    path = (urlsplit(url).path or "").strip()
    if not path:
        return None
    match = IKEA_URL_SKU_RE.search(path)
    if not match:
        return None
    return match.group(1)


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


def extract_json_ld_product(page_html: str) -> dict[str, object] | None:
    match = JSON_LD_PIP_RE.search(page_html)
    if not match:
        return None
    raw = match.group(1).strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def pick_json_ld_name(payload: dict[str, object] | None) -> str | None:
    if not payload:
        return None
    name = payload.get("name")
    if isinstance(name, str):
        return decode_web_text(name)
    return None


def pick_json_ld_brand(payload: dict[str, object] | None) -> str | None:
    if not payload:
        return None
    brand = payload.get("brand")
    if isinstance(brand, dict):
        name = brand.get("name")
        if isinstance(name, str):
            return decode_web_text(name)
    if isinstance(brand, str):
        return decode_web_text(brand)
    return None


def pick_json_ld_image(payload: dict[str, object] | None) -> str | None:
    if not payload:
        return None
    image = payload.get("image")
    if isinstance(image, str):
        return decode_web_text(image)
    if isinstance(image, list):
        for item in image:
            if isinstance(item, str):
                normalized = decode_web_text(item)
                if normalized:
                    return normalized
            elif isinstance(item, dict):
                url = item.get("contentUrl")
                if isinstance(url, str):
                    normalized = decode_web_text(url)
                    if normalized:
                        return normalized
    return None


def pick_json_ld_sku(payload: dict[str, object] | None) -> str | None:
    if not payload:
        return None
    for key in ("sku", "mpn"):
        value = payload.get(key)
        if isinstance(value, str):
            digits = re.sub(r"\D+", "", value)
            if len(digits) == 8:
                return digits
    return None


def extract_page_metadata(page_html: str, *, fallback_sku: str | None) -> dict[str, str | None]:
    json_ld = extract_json_ld_product(page_html)

    og_title_match = OG_TITLE_RE.search(page_html)
    og_image_match = OG_IMAGE_RE.search(page_html)
    explicit_barcode_match = BARCODE_HINT_RE.search(page_html)

    explicit_barcode = explicit_barcode_match.group(1) if explicit_barcode_match else None
    name = pick_json_ld_name(json_ld) or (decode_web_text(og_title_match.group(1)) if og_title_match else None)
    brand = pick_json_ld_brand(json_ld)
    image_url = pick_json_ld_image(json_ld) or (decode_web_text(og_image_match.group(1)) if og_image_match else None)
    source_sku = pick_json_ld_sku(json_ld) or fallback_sku

    return {
        "barcode": normalize_barcode(explicit_barcode),
        "name": name,
        "brand": brand,
        "image_url": image_url,
        "source_sku": source_sku,
    }


def add_row_if_missing(by_url: dict[str, list[dict[str, object]]], url: str) -> None:
    if url not in by_url:
        by_url[url] = [
            {
                "id": 0,
                "item_name": None,
                "category": None,
                "unit": None,
                "barcode": None,
            }
        ]


def main() -> None:
    args = parse_args()
    if not args.db.exists():
        raise FileNotFoundError(f"DB not found: {args.db}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        db_rows = conn.execute(
            """
            SELECT id, item_name, category, unit, barcode, order_url
            FROM standalone_inventory
            WHERE order_url IS NOT NULL
              AND trim(order_url) != ''
              AND lower(order_url) LIKE '%ikea.com%'
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    by_url: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in db_rows:
        normalized_url = normalize_url(row["order_url"])
        if not normalized_url:
            continue
        by_url[normalized_url].append(
            {
                "id": int(row["id"]),
                "item_name": normalize_text(row["item_name"]),
                "category": normalize_text(row["category"]),
                "unit": normalize_text(row["unit"]),
                "barcode": normalize_barcode(row["barcode"]),
            }
        )

    for extra_url in args.url:
        normalized_url = normalize_url(extra_url)
        if normalized_url:
            add_row_if_missing(by_url, normalized_url)

    urls = sorted(by_url.keys())
    if args.max_urls and args.max_urls > 0:
        urls = urls[: args.max_urls]

    catalog_by_barcode: dict[str, dict[str, str]] = {}
    fetch_ok = 0
    fetch_fail = 0
    no_barcode = 0

    for index, url in enumerate(urls, start=1):
        status = "ok"
        final_url = url
        try:
            final_url, page_html = fetch_page(url, timeout_seconds=max(1.0, args.timeout_seconds))
            sku_from_url = extract_source_sku_from_url(final_url) or extract_source_sku_from_url(url)
            metadata = extract_page_metadata(page_html, fallback_sku=sku_from_url)

            linked_rows = by_url[url]
            local_name = next((normalize_text(r.get("item_name")) for r in linked_rows if normalize_text(r.get("item_name"))), None)
            local_category = next((normalize_text(r.get("category")) for r in linked_rows if normalize_text(r.get("category"))), None)
            local_unit = next((normalize_text(r.get("unit")) for r in linked_rows if normalize_text(r.get("unit"))), None)
            local_barcode = next((normalize_barcode(r.get("barcode")) for r in linked_rows if normalize_barcode(r.get("barcode"))), None)
            source_row_ids = ",".join(str(int(r["id"])) for r in linked_rows if int(r.get("id") or 0) > 0)

            resolved_barcode = metadata.get("barcode") or local_barcode or sku_from_url
            resolved_barcode = normalize_barcode(resolved_barcode)
            if not resolved_barcode:
                no_barcode += 1
                status = "no_barcode"
            else:
                fetch_ok += 1
                if metadata.get("barcode"):
                    barcode_kind = "upc_from_page"
                elif local_barcode:
                    barcode_kind = "local_inventory_barcode"
                else:
                    barcode_kind = "ikea_article_number_fallback"
                notes_parts = [f"barcode_kind={barcode_kind}", "scraped_from=standalone_inventory"]
                if source_row_ids:
                    notes_parts.append(f"source_row_ids={source_row_ids}")

                row_data = {
                    "barcode": resolved_barcode,
                    "product_name": metadata.get("name") or local_name or "",
                    "brand": metadata.get("brand") or "IKEA",
                    "category": local_category or "",
                    "unit": local_unit or "",
                    "image_url": metadata.get("image_url") or "",
                    "product_url": final_url,
                    "source_sku": metadata.get("source_sku") or sku_from_url or "",
                    "notes": "; ".join(notes_parts),
                }
                existing = catalog_by_barcode.get(resolved_barcode)
                if existing:
                    for key in ("product_name", "brand", "category", "unit", "image_url", "product_url", "source_sku"):
                        if not existing.get(key) and row_data.get(key):
                            existing[key] = row_data[key]
                else:
                    catalog_by_barcode[resolved_barcode] = row_data
        except Exception as exc:
            fetch_fail += 1
            status = f"error: {exc}"

        if args.verbose:
            print(f"[{index}/{len(urls)}] {status} :: {url}")
        if index < len(urls) and args.delay_seconds > 0:
            time.sleep(max(0.0, args.delay_seconds))

    out_rows = [catalog_by_barcode[key] for key in sorted(catalog_by_barcode.keys())]
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

    print(f"standalone_inventory rows with IKEA URLs: {len(db_rows)}")
    print(f"unique URLs fetched: {len(urls)}")
    print(f"fetch_ok_with_barcode: {fetch_ok}")
    print(f"fetch_fail: {fetch_fail}")
    print(f"fetched_without_barcode: {no_barcode}")
    print(f"unique catalog rows emitted: {len(out_rows)}")
    print(f"output_csv: {args.output_csv}")


if __name__ == "__main__":
    main()
