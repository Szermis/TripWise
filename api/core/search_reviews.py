from ddgs import DDGS
from openai import OpenAI
from neo4j import GraphDatabase
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def fetch_review_data(name: str, place: str):
    results = DDGS().text(name + " " + place + " opinie", max_results=10) # TODO: Szermis the language specyfic up to LLM
    print("Search for reviews for: " + name)

    response = client.responses.create(
        model="gpt-5-nano",
        instructions="Below is an array of restaurants and urls to websites with reviews. Return the ids of the entries sorted in order of which is most likely to contain rewiews. Return id's seperated by comma",
        input=str(results),
    )
    o = response.output_text
    ids = str(o).split(',')


    for i in ids:
        res = results[int(i)]

        html = requests.get(res["href"], headers=headers)

        website = html.text[:300_000]

        try:
            response = client.responses.create(
                model="gpt-5-nano",
                instructions="Bellow are contents of a page in html format. What are rewiews for restaurant? Format the output as json containing an array of rewiews and scores. Keep score from 1 to 5 and use following format: [{\"review\":\"review_text\", \"score\":1.5}]",
                input=website,
            )
            output = response.output_text

            insert_from_json(name, output)
            break;
        except:
                print("Website to big")


def insert_from_json(rest_name: str, json_string: str, delimiter: str = ","):
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
                review = parts[0]
                score = parts[1] if len(parts) > 1 else None
                data.append({"review": review, "score": score})

    if isinstance(data, dict):
        if "review" in data or "name" in data:
            review = data.get("review") or data.get("name")
            score = data.get("score")
            items = [{"review": str(review), "score": score}]
        else:
            items = []
    elif isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                review = row.get("review") or row.get("name") or row.get("item")
                score = row.get("score")
                if review is not None:
                    items.append({"review": str(review), "score": score})
            else:
                continue
    else:
        items = []

    if not items:
        print(f"No valid reviews extracted for {rest_name}")
        raise Exception("No reviews")

    with driver.session() as session:

        def _bulk(tx, rest_name_param, rows_param):
            tx.run(
                """
                UNWIND $rows AS row
                MERGE (r:Restaurant {name: $rest_name})
                MERGE (m:Reviews {name: row.review})
                FOREACH (ignore IN CASE WHEN row.score IS NOT NULL THEN [1] ELSE [] END |
                    SET m.score = row.score
                )
                MERGE (m)-[:isAbout]->(r)
                """,
                rest_name=rest_name_param,
                rows=rows_param,
            )

        session.execute_write(_bulk, rest_name, items)


if __name__ == "__main__":
    fetch_review_data("Restauracja Studencka", "Warszawa")
