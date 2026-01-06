#!/usr/bin/env python3
"""Ingest Restaurants into Neo4j

This script reads a JSON array of restaurant objects and upserts them into Neo4j.
Each restaurant is stored as a Restaurant node with properties:
- name (string, unique key)
- rating (float, clamped 0-5)
- cuisine (string)

Usage:
  python ingest_restaurants.py --file restaurants.json
  or
  python ingest_restaurants.py --api https://example.com/api/restaurants
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Dict, Any

try:
    from neo4j import GraphDatabase
except ImportError:
    print(
        "Missing neo4j-driver. Install with: pip install neo4j-driver", file=sys.stderr
    )
    sys.exit(1)

# Connection config
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "password123"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def load_restaurants(tx, rows: List[Dict[str, Any]]):
    # Upsert a batch of restaurants
    tx.run(
        """
        UNWIND $rows AS row
        WITH row, toFloat(COALESCE(row.rating, 0)) AS rating
        MERGE (r:Restaurant {name: row.name})
        SET r.rating = CASE
                            WHEN rating < 0 THEN 0
                            WHEN rating > 5 THEN 5
                            ELSE rating
                          END,
            r.cuisine = row.cuisine
        """,
        rows=rows,
    )


def ingest(rows: List[Dict[str, Any]]):
    with driver.session() as session:
        session.write_transaction(load_restaurants, rows)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file", help="Path to JSON file containing restaurants (array)"
    )
    group.add_argument("--api", help="API URL to fetch restaurants (GET)")
    args = parser.parse_args()

    data: List[Dict[str, Any]] = []
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        import requests

        resp = requests.get(args.api, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    if not isinstance(data, list):
        print("Error: expected JSON array of restaurant objects.", file=sys.stderr)
        sys.exit(2)

    # Basic validation
    for item in data:
        if not isinstance(item, dict) or "name" not in item:
            print(
                "Warning: skipping invalid item (missing name):", item, file=sys.stderr
            )

    # Filter valid items
    valid = [item for item in data if isinstance(item, dict) and "name" in item]

    if not valid:
        print("No valid restaurant records found.")
        sys.exit(0)

    ingest(valid)
    print(f"Ingested {len(valid)} restaurants into Neo4j.")


if __name__ == "__main__":
    main()
