import requests
from pyscript import document, when
from js import console

SOLR_URL = "http://localhost:8983/solr/wild_life/select"

def search(query, rows=10):
   
    params = {
        "q": f"{query}~1",
        "defType": "edismax",
        "qf": "name^5 species_name^5 scientific_name^5 summary^3 overview^3 about^3 how_to_identify^3 did_you_know^2 why_they_matter^2 conservation_status^2 statistics^2 distribution^2 habitats^1 places^1 related_species^1 predators^1 population^1 status^1 length^1 location^1 facts^0.8 threats^0.8 diet^0.5 gestation^0.5 lifespan^0.5 weight^0.5 height^0.5",
        "pf": "name^10 scientific_name^6 species_name^6",
        "pf2": "summary^3 overview^3",
        "pf3": "about^2",
        "mm": "2<75%",
        "tie": "0.1",
        "rows": rows,
        "fl": "id,name,scientific_name,animal_type,image_url,url,dirty_overview,summary",
        "wt": "json"
    }
   
    resp = requests.get(SOLR_URL, params=params).json()
    
    return resp["response"]["docs"]



searchbar = document.querySelector("#search")
searchbtn = document.querySelector("#search-btn")


@when("click", searchbtn)
def on_search_click(event):

    weight_div = document.querySelector("#weight_cm")
    size_div = document.querySelector("#length_cm")
    population_div = document.querySelector("#population")

    weight_value_min = weight_div.querySelector(".min-input").value
    weight_value_max = weight_div.querySelector(".max-input").value
    weight_range = [float(weight_value_min), float(weight_value_max)]

    size_value_min = size_div.querySelector(".min-input").value
    size_value_max = size_div.querySelector(".max-input").value
    size_range = [float(size_value_min), float(size_value_max)]

    population_value_min = population_div.querySelector(".min-input").value
    population_value_max = population_div.querySelector(".max-input").value
    population_range = [float(population_value_min), float(population_value_max)]


    
    query = searchbar.value
    console.log(f"Searching for: {query}")

    results = search(query)
    resultsContainer = document.querySelector("#results")
    resultsContainer.innerHTML = ""
    # console.log(f"Returned result for: {query} is \n{results}")
    for r in results:

        weight = [r.get("weight_kg_min", None), r.get("weight_kg_max", None)]
        size = [r.get("length_cm_min", None), r.get("length_cm_max", None)]
        population = [r.get("population_min", None), r.get("population_max", None)]


        if not None in weight :
            if not max(weight[0], weight_range[0]) <= min(weight[-1], weight_range[1]):
                continue
        if not None in size:
            if not max(size[0], size_range[0]) <= min(size[-1], size_range[1]):
                continue
        if not None in population:
            if not max(population[0], population_range[0]) <= min(population[-1], population_range[1]):
                continue


        item = document.createElement("div")
        item.className = "item"
        item.innerHTML = f"""
            
            <div class="text">


                <a href="{r.get('url')}" target="_blank">{r.get('name')} - {r.get('scientific_name')}</a>
                <p class="overview">{r.get('dirty_overview')}</p> 

            </div>
            <img class="animal-img" src="{r.get('image_url')}" alt="{r.get('name')}"  />
        """

        resultsContainer.appendChild(item)
