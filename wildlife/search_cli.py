import requests

SOLR_URL = "http://localhost:8983/solr/wild_life/select"

def search(query, rows=10):
    params = {
        "q": query,
        "defType": "edismax",
        "qf": "name^4 species_name^4 scientific_name^4 summary^2 overview^2 how_to_identify^2 distribution^1 did_you_know^1 conservation_status^1 statistics^1 about^1 why_they_matter^1 threats^0.5 facts^0.5",
        "rows": rows,
        "wt": "json"
    }

    resp = requests.get(SOLR_URL, params=params).json()
    print(resp)
    return resp["response"]["docs"]

if __name__ == "__main__":
    while True:
        q = input("Query: ")
        if not q:
            break

        results = search(q)
        print()
        for r in results:
            print("•", r.get("name"), "-", r.get("scientific_name"))
            print(" ", r.get("url"))
        print()
