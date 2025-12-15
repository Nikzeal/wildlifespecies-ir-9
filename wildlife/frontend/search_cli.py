import requests
from pyscript import document, when
from js import console
import re

SOLR_URL = "http://localhost:8983/solr/wild_life/select"

NUMERIC_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")

FILTER_KEYWORDS = {
    "weight": ["weight", "weigh", "kg", "kilogram"],
    "size": ["size", "length", "height", "cm", "meter", "metre"],
    "population": ["population", "pop", "individuals"],
    "lifespan": ["lifespan", "age", "years"],
}

def detect_source(url: str):
    url = url.lower()
    if "awf.org" in url:
        return {
            "logo": "../resources/images/awf_logo.png",
            "name": "African Wildlife Foundation"
        }
    elif "worldwildlife.org" in url:
        return {
            "logo": "../resources/images/wwf_logo.png",
            "name": "World Wildlife Fund"
        }
    elif "wildlifetrusts.org" in url:
        return {
            "logo": "../resources/images/wildlifetrusts_logo.png",
            "name": "The Wildlife Trusts"
        }


def parse_query_intent(query):
    query_lower = query.lower()

    numbers = [float(n) for n in NUMERIC_PATTERN.findall(query_lower)]

    intent = {
        "text": query,
        "numeric": numbers,
        "filters": {}
    }

    for key, keywords in FILTER_KEYWORDS.items():
        if any(k in query_lower for k in keywords):
            if numbers:
                intent["filters"][key] = numbers

    return intent

def build_numeric_filter(field, values, tolerance=0.25):
    v = values[0]

    min_v = v * (1 - tolerance)
    max_v = v * (1 + tolerance)

    return f"{field}:[{min_v} TO {max_v}]"

def build_range_filter(field, min_v, max_v):
    return f"{field}:[{min_v} TO {max_v}]"


def search(query, rows=10):
    intent = parse_query_intent(query)

    fq = []

    if "weight" in intent["filters"]:
        v = intent["filters"]["weight"][0]
        fq.append(build_range_filter(
            "weight_kg",
            v * 0.75,
            v * 1.25
        ))

    if "size" in intent["filters"]:
        v = intent["filters"]["size"][0]
        fq.append(build_range_filter(
            "length_cm",
            v * 0.75,
            v * 1.25
        ))

    if "population" in intent["filters"]:
        v = intent["filters"]["population"][0]
        fq.append(
            f"population_min:[* TO {v}] AND population_max:[{v} TO *]"
        )

    params = {
        "q": query if query.strip() else "*:*",
        "defType": "edismax",
        "qf": (
            "name^8 scientific_name^6 species_name^6 "
            "summary^4 overview^4 about^3 "
            "habitats^2 distribution^2 "
            "facts^1.5 threats^1 diet^1"
        ),
        "pf": "name^12 scientific_name^8",
        "mm": "1<75%",
        "tie": "0.1",
        "rows": rows,
        "fl": "id,name,scientific_name,animal_type,image_url,url,dirty_overview",
        "wt": "json"
    }

    if fq:
        params["fq"] = fq

    resp = requests.get(SOLR_URL, params=params)
    try:
        data = resp.json()
    except Exception:
        console.error("Invalid JSON from Solr")
        return []

    if "error" in data:
        console.error("Solr error:", data["error"]["msg"])
        return []

    return data.get("response", {}).get("docs", [])


searchbar = document.querySelector("#search")
searchbtn = document.querySelector("#search-btn")


@when("click", searchbtn)
def on_search_click(event):

    filters = document.querySelectorAll(".filter")
    for f in filters:
        filter_name = f.querySelector("label").innerText
        filter_value_min = f.querySelector(".min-input").value
        filter_value_max = f.querySelector(".max-input").value 
        console.log(f"Filter applied: {filter_name} : {filter_value_min} - {filter_value_max}")
    


    
    query = searchbar.value
    console.log(f"Searching for: {query}")

    results = search(query)
    resultsContainer = document.querySelector("#results")
    resultsContainer.innerHTML = ""

    for r in results:
        source = detect_source(r.get("url", ""))

        item = document.createElement("div")
        item.className = "item"

        item.innerHTML = f"""
            <div class="logo">
                <img class="logo-img" src="{source['logo']}" alt="{source['name']}">
                <p>{source['name']}</p>
            </div>

            <div class="result">
                <div class="text">
                    <a href="{r.get('url')}" target="_blank">
                        {r.get('name')} - {r.get('scientific_name')}
                    </a>
                    <p class="overview">
                        {r.get('dirty_overview', '')}
                    </p>
                </div>

                <img class="animal-img"
                    src="{r.get('image_url', '')}"
                    alt="{r.get('name', '')}">
            </div>
        """

        resultsContainer.appendChild(item)

