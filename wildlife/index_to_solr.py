import json
import requests

SOLR_URL = "http://localhost:8983/solr/wild_life/update?commit=true"

def index_file(path, source):
    print(f"Indexing: {path} ({source})")
    with open(path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    for item in raw_items:
        item["id"] = item.get("url")
        item["source"] = source

    resp = requests.post(SOLR_URL, json=raw_items)
    print(resp.status_code, resp.text)


if __name__ == "__main__":
    index_file("wt-all_wildlifetrusts_animals.json", "WT")
