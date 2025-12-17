import json
import requests

SOLR_URL = "http://localhost:8983/solr/wild_life"

def clear_index():
    url = f"{SOLR_URL}/update?commit=true"
    payload = {"delete": {"query": "*:*"}}
    resp = requests.post(url, json=payload)
    print("Delete all docs:", resp.status_code, resp.text)

def index_file(path, source):
    print(f"Indexing: {path} ({source})")
    with open(path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    for item in raw_items:
        item["id"] = item.get("url")
        item["source"] = source

    resp = requests.post(f"{SOLR_URL}/update?commit=true", json=raw_items)
    print(resp.status_code, resp.text)


if __name__ == "__main__":
    clear_index()

    index_file("wildlifetrusts.json", "WT")
    index_file("awf.json", "AWF")
    index_file("wwf.json", "WWF")
