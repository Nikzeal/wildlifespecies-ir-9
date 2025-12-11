import requests
from pyscript import document, when
from js import console

SOLR_URL = "http://localhost:8983/solr/wild_life/select"

def search(query, rows=10):
   
    params = {
        "q": f"{query}~1",
        "defType": "edismax",
        "qf": "name^5 species_name^5 scientific_name^5 summary^3 overview^3 about^3 how_to_identify^3 did_you_know^2 why_they_matter^2 conservation_status^2 statistics^2 distribution^2 habitats^1 places^1 related_species^1 predators^1 population^1 status^1 length^1 location^1 facts^0.8 threats^0.8 diet^0.5 gestation^0.5 lifespan^0.5 weight^0.5 height^0.5 source^0.2 url^0.2 image_url^0.2",
        "pf": "name^10 scientific_name^6 species_name^6",
        "pf2": "summary^3 overview^3",
        "pf3": "about^2",
        "mm": "2<75%",
        "tie": "0.1",
        "rows": rows,
        "fl": "id,name,scientific_name,image_url,url,dirty_overview,overview,summary",
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
    console.log(f"Returned result for: {query} is \n{results}")
    for r in results:
        item = document.createElement("div")
        item.className = "item"
        item.innerHTML = f"""
            <img src="{r.get('image_url')}" alt="{r.get('name')}"  />
            <div class="text">


                <a href="{r.get('url')}" target="_blank">{r.get('name')} - {r.get('scientific_name')}</a>
                <p class="overview">{r.get('dirty_overview')}</p> 

            </div>
        """

        resultsContainer.appendChild(item)
