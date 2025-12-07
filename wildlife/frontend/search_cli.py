import requests
from pyscript import document, when


SOLR_URL = "http://localhost:8983/solr/wild_life/select"



def search(query, rows=10):
    params = {
        "q": f"{query}~2",
        "defType": "edismax",
        "qf": "name^4 species_name^4 scientific_name^4 summary^2 overview^2 how_to_identify^2 distribution^1 did_you_know^1 conservation_status^1 statistics^1 about^1 why_they_matter^1 threats^0.5 facts^0.5",
        "rows": rows,
        "wt": "json"
    }

    resp = requests.get(SOLR_URL, params=params).json()
    
    return resp["response"]["docs"]



searchbar = document.querySelector("#search")

@when(searchbar, "search")
def on_search(event):
    query = searchbar.value
    results = search(query)
    resultsContainer = document.querySelector("#results")
    resultsContainer.innerHTML = ""
    for r in results:
        item = document.createElement("div")
        item.className = "result-item"
        item.innerHTML = f"""
            <h3><a href="{r.get('url')}" target="_blank">{r.get('name')}</a></h3>
            <p><em>{r.get('scientific_name')}</em></p>
        """
        resultsContainer.appendChild(item)










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


