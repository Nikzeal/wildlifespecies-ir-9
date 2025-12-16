import requests
from pyscript import document, when
from js import console
import re
from collections import defaultdict
from pyodide.ffi import create_proxy

SOLR_URL = "http://localhost:8983/solr/wild_life/select"

NUMERIC_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")

FILTER_KEYWORDS = {
    "weight": ["weight", "weigh", "kg", "kilogram"],
    "size": ["size", "length", "height", "cm", "meter", "metre"],
    "population": ["population", "pop", "individuals"],
    "lifespan": ["lifespan", "age", "years"],
}

def solr_get(elem):
    if not elem:
        return 1.0
    if isinstance(elem, list):
        elem = elem[0]
    return elem

def solr_float(elem):
    val = solr_get(elem)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

def detect_source(url: str):
    if not url:
        return None
    if isinstance(url, list):
        url = url[0]
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

def cluster_by_animal_type(results):
    clusters = defaultdict(lambda: {"count": 0, "docs": []})

    for r in results:
        animal_types = r.get("animal_type", ["Animal"])

        for atype in animal_types:
            clusters[atype]["count"] += 1
            clusters[atype]["docs"].append(r)

    sorted_clusters = sorted(
        clusters.items(),
        key=lambda item: item[1]["count"],
        reverse=True
    )

    return sorted_clusters


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
        "qf": "name^8 scientific_name^6 summary^4 overview^4 habitats^2 distribution^2 facts^1.5 threats^1 diet^1",
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
    
    results_to_display = 3
    clusters = cluster_by_animal_type(results=results[results_to_display:])
    for r in results[:results_to_display]:
        source = detect_source(r.get("url", ""))

        weight = [
            solr_float(r.get("weight_kg_min")),
            solr_float(r.get("weight_kg_max"))
        ]

        size = [
            solr_float(r.get("length_cm_min")),
            solr_float(r.get("length_cm_max"))
        ]

        population = [
            solr_float(r.get("population_min")),
            solr_float(r.get("population_max"))
        ]

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
            <div class="logo">
                <img class="logo-img" src="{source['logo']}" alt="{source['name']}">
                <p>{source['name']}</p>
            </div>

            <div class="result">
                <div class="text">
                    <a href="{solr_get(r.get('url'))}" target="_blank">
                        {solr_get(r.get('name'))} - {solr_get(r.get('scientific_name'))}
                    </a>
                    <p class="overview">
                        {solr_get(r.get('dirty_overview'))}
                    </p>
                </div>

                <img class="animal-img"
                    src="{solr_get(r.get('image_url'))}"
                    alt="{solr_get(r.get('name'))}">
            </div>
        """

        resultsContainer.appendChild(item)

    clusterContainer = document.querySelector("#topics-container")
    clusterContainer.innerHTML = ""
    title = document.querySelector("#related-topics-title")
    title.innerHTML = ""
    for animal_type, data in clusters:
        title.innerHTML = "Related Topics"

        toggle_btn = document.createElement("button")
        toggle_btn.className = "filter-toggle"
        toggle_btn.innerText = f"{animal_type} ▼"

        cluster_div = document.createElement("div")
        cluster_div.className = "cluster"
        cluster_div.style.display = "none"

        def make_toggle(btn, container, label):
            def toggle(evt):
                open_ = container.style.display == "block"
                container.style.display = "none" if open_ else "block"
                btn.innerText = f"{label} {'▲' if not open_ else '▼'}"
            return toggle

        toggle_handler = create_proxy(
            make_toggle(toggle_btn, cluster_div, animal_type)
        )

        toggle_btn.addEventListener("click", toggle_handler)


        clusterContainer.appendChild(toggle_btn)
        clusterContainer.appendChild(cluster_div)

        for r in data["docs"]:
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
                        <a href="{solr_get(r.get('url'))}" target="_blank">
                            {solr_get(r.get('name'))} - {solr_get(r.get('scientific_name'))}
                        </a>
                        <p class="overview">{solr_get(r.get('dirty_overview'))}</p>
                    </div>

                    <img class="animal-img"
                         src="{solr_get(r.get('image_url'))}"
                         alt="{solr_get(r.get('name'))}">
                </div>
            """

            cluster_div.appendChild(item)
