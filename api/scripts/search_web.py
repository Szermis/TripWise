from ddgs import DDGS
from openai import OpenAI
from neo4j import GraphDatabase
import requests
import os
import json

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

        # csv_resp = client.responses.create(
        #     model="gpt-5-nano",
        #     instructions="1. Carefully read the text provided by the user. 2. Identify any dishes mentioned and list them in CSV format with each value enclosed in quotes. The first column should be labelled 'Dish' and contain the dish name. The second column should be labelled 'Price' and contain the dishes price. Ommit the data about the currency 3. If you don’t know a value, say 'unknown'. ",
        #     input=response.output_text,
        # )

        insert_from_json(name, response.output_text)


def insert_from_json(rest_name: str, json_string: str, delimiter: str = ","):
    # Normalize input to a list of dicts with keys 'dish' and 'price'
    items = []
    if not json_string:
        print(f"No json data to insert for {rest_name}")
        return

    try:
        data = json.loads(json_string)
    except Exception as e:
        print(f"Failed to parse JSON data: {e}")
        # Fallback: attempt simple CSV-like parsing
        data = []
        lines = [l.strip() for l in json_string.splitlines() if l.strip()]
        for line in lines:
            parts = [p.strip() for p in line.split(delimiter)]
            if len(parts) >= 1:
                dish = parts[0]
                price = parts[1] if len(parts) > 1 else None
                data.append({"dish": dish, "price": price})

    # Normalize to expected structure: list of {"dish": ..., "price": ...}
    if isinstance(data, dict):
        if "dish" in data or "name" in data:
            dish = data.get("dish") or data.get("name")
            price = data.get("price")
            items = [{"dish": str(dish), "price": price}]
        else:
            items = []
    elif isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                dish = row.get("dish") or row.get("name") or row.get("item")
                price = row.get("price")
                if dish is not None:
                    items.append({"dish": str(dish), "price": price})
            else:
                continue
    else:
        items = []

    if not items:
        print(f"No valid menu items extracted for {rest_name}")
        return

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

        session.execute_write(_bulk, rest_name, items)


if __name__ == "__main__":
    fetch_menu_data("Restauracja Studencka", "Warszawa")
