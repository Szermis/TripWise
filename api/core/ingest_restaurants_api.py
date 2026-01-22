#!/usr/bin/env python3
"""Ingest Restaurants from OpenStreetMap Nominatim API into Neo4j

This script can fetch an API response (array of restaurant-like places) or ingest
from a local JSON file and upsert Restaurant nodes with:
- name: from the API (prefers 'name' then 'display_name')
- rating: default 0 (no rating from API)
- cuisine: inferred from common cuisine keywords in name/address

Usage:
  python ingest_restaurants_api.py --source api --api '<url>'
  python ingest_restaurants_api.py --source file --path data/restaurants.json
"""

import argparse
import os
import sys
from typing import List, Dict, Any

from .config import settings
from . import search_reviews
from . import search_web
from multiprocessing import Pool

try:
    from neo4j import GraphDatabase, Result, Record
except Exception:
    print(
        "Missing neo4j-driver. Install with: pip install neo4j-driver", file=sys.stderr
    )
    sys.exit(1)

import requests

driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

CUISINE_KEYWORDS = [
    "Japanese",
    "Chinese",
    "Korean",
    "Thai",
    "Indian",
    "Vietnamese",
    "Mexican",
    "American",
    "Italian",
    "French",
    "Turkish",
    "Greek",
    "Spanish",
    "Mediterranean",
    "Lebanese",
    "Middle Eastern",
    "Thai",
    "Asian",
    " barbecue",
    "Barbecue",
]


def guess_cuisine_from_text(text: str) -> str:
    t = (text or "").lower()
    for kw in CUISINE_KEYWORDS:
        if kw.lower() in t:
            return kw
    return "Unknown"


def extract_name(item: Dict[str, Any]) -> str:
    if isinstance(item.get("name"), str) and item["name"]:
        return item["name"]
    if isinstance(item.get("display_name"), str) and item["display_name"]:
        return item["display_name"]
    addr = item.get("address", {}) or {}
    if isinstance(addr, dict) and addr.get("amenity"):
        return addr["amenity"]
    return "Unknown Restaurant"


def normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    print(item)
    name = extract_name(item)
    text_sources = []
    # if isinstance(item, dict):
    #     text_sources.append(str(item.get("name")))
    #     text_sources.append(str(item.get("display_name")))
    #     if isinstance(item.get("address"), dict):
    #         for v in item["address"].values():
    #             if isinstance(v, str):
    #                 text_sources.append(v)
    # combined = " ".join([t for t in text_sources if t])
    # cuisine = guess_cuisine_from_text(combined)
    # rating = 0.0

    address = item.get("address")
    city = address.get("city", "")
    city_block = address.get("city_block", "")
    quarter = address.get("quarter", "")
    suburb = address.get("suburb", "")
    state = address.get("state", "")
    country = address.get("country", "")
    place_rank = item.get("place_rank", "")
    return {
        "name": name,
        # "city_block": city_block,
        # "quarter": quarter,
        # "suburb": suburb,
        # "state": state,
        "city": city,
        "country": country,
        "place_rank": place_rank,
    }


def load_restaurants(tx, rows: List[Dict[str, Any]]):
    tx.run(
        """
        UNWIND $rows AS row
        MERGE (r:Restaurant {name: row.name})
        SET 
            r.city = row.city,
            r.country = row.country,
            r.place_rank = row.place_rank
        """,
        rows=rows,
    )


def ingest(rows: List[Dict[str, Any]]):
    with driver.session() as session:
        session.execute_write(load_restaurants, rows)


url = "https://nominatim.openstreetmap.org/search?addressdetails=1&format=jsonv2&limit=8&q="


def populate_db():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--place", help="place"
    )
    args = parser.parse_args()
    download_to_db(args.place)


# query = "warsaw+restaurant+asian"
def download_to_db(place: str):
    data = []
    resp = requests.get(url + place + "+restaurant", headers=headers)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        norm = normalize_item(item)
        if norm.get("name"):
            rows.append(norm)

    if not rows:
        print("No valid restaurant records found.")
        sys.exit(0)

    ingest(rows)
    print(f"Ingested {len(rows)} restaurants into Neo4j.")

    pool = Pool(processes=8)

    for item in rows:
        pool.apply_async(search_web.fetch_menu_data, [item.get("name"), place, ])
        pool.apply_async(search_reviews.fetch_review_data, [item.get("name"), place, ])

    pool.close()
    pool.join()


def query_neo4j(query: str) -> list[Record]:
    """
    Query Neo4j.
    """
    with driver.session() as session:
        result = session.run(
            query=query
        )
        records = list(result)
        return records


if __name__ == "__main__":
    populate_db()
