import requests
from pyscript import document, when
from js import console



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
searchbtn = document.querySelector("#search-btn")


@when("click", searchbtn)
def on_search_click(event):
    
    query = searchbar.value
    console.log(f"Searching for: {query}")

    results = search(query)
    resultsContainer = document.querySelector("#results")
    resultsContainer.innerHTML = ""
    for r in results:
        item = document.createElement("div")
        item.className = "item"
        item.innerHTML = f"""
            <img src="{r.get('image_url')}" alt="{r.get('name')}"  />
            <div class="text">


                <a href="{r.get('url')}" target="_blank">{r.get('name')} - {r.get('scientific_name')}</a>
                <p class="overview">{r.get('summary')}</p>

            </div>
        """

        resultsContainer.appendChild(item)



