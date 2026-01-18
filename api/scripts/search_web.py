from ddgs import DDGS
from openai import OpenAI
from neo4j import GraphDatabase
import requests
import os
import csv
import pandas

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "password123"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def fetch_menu_data(name: str, place: str):
    select = f"MATCH (n:Restaurant:{{name: '{name}'}}) RETURN n"

    results = DDGS().text(name + " " + place + " menu", max_results=1)

    for res in results:
        html = requests.get(res["href"], headers=headers)

        response = client.responses.create(
            model="gpt-5-nano",
            instructions="Bellow are contents of a page in html format. What can I order from the menu? Format the output as json containing an array of dishes and their prices",
            input=html.text,
        )

        csv_resp = client.responses.create(
            model="gpt-5-nano",
            instructions="1. Carefully read the text provided by the user. 2. Identify any dishes mentioned and list them in CSV format with each value enclosed in quotes. The first column should be labelled 'Dish' and contain the dish name. The second column should be labelled 'Price' and contain the dishes price. Ommit the data about the currency 3. If you don’t know a value, say 'unknown'. ",
            input=response.output_text,
        )


def insert_from_csv(
    rest_name: str, csv_path: str, delimiter: str = ",", encoding: str = "utf-8"
):
    rows = []
    try:
        with open(csv_path, newline="", encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                dish = (row.get("Dish") or row.get("dish") or "").strip()
                if not dish:
                    continue
                price_raw = (row.get("Price") or row.get("price") or "").strip()
                price = None
                if price_raw and price_raw.lower() != "unknown":
                    try:
                        price = float(price_raw)
                    except ValueError:
                        price = None
                rows.append({"dish": dish, "price": price})
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    if not rows:
        print("No valid rows found in CSV.")
        return

    for row in rows:
        pass

    with driver.session() as session:

        def _bulk(tx, rest_name_param, rows_param):
            tx.run(
                """
                UNWIND $rows AS row
                MERGE (r:Restaurant {name: $rest_name})
                MERGE (m:Menu {name: row.dish})
                FOREACH (ignore IN CASE WHEN row.price IS NOT NULL THEN [1] ELSE [] END |
                    SET m.price = row.price
                )
                MERGE (m)-[:servedIn]->(r)
                """,
                rest_name=rest_name_param,
                rows=rows_param,
            )

        session.execute_write(_bulk, rest_name, rows)


if __name__ == "__main__":
    # fetch_menu_data("Restauracja Studencka", "Warszawa")
    insert_from_csv("Restauracja Studencka", "buff.csv")
