import json
import requests
from pyscript import document, when, window
from js import console
import re
from collections import defaultdict


def show_for_you(user_profile):
    return


def dom_ready():
    ls = window.localStorage
    show_for_you(ls.getItem("user_profile"))
    return document.readyState == "complete"

while not dom_ready():
    pass

SOLR_URL = "http://localhost:8983/solr/wild_life/select"

NUMERIC_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")

FILTER_KEYWORDS = {
    "weight": ["weight", "weigh", "kg", "kilogram"],
    "size": ["size", "length", "height", "cm", "meter", "metre"],
    "population": ["population", "pop", "individuals"],
    "lifespan": ["lifespan", "age", "years"],
}

def safe_get(doc, key, default=""):
    val = doc.get(key, default)
    if isinstance(val, list) and val:
        return val[0]
    if val is None:
        return default
    return val

def is_filter_enabled(filter_id):
    checkbox = document.querySelector(f"#{filter_id} input.filter-enable")
    return checkbox.checked

def fmt(x, decimals=1, small_sig=3):
    if x == 0:
        return "0"
    if abs(x) < 1:
        return f"{x:.{small_sig}g}"
    return f"{x:.{decimals}f}".rstrip("0").rstrip(".")

def format_stat(stat, unit="", default="Unknown", decimals=1):
    if not stat or None in stat:
        return default
    s_min = stat[0][0]
    s_max = stat[1][0]
    def fmt_local(x):
        return fmt(x, decimals=decimals)
    if s_min == 0:
        return f"Up to {fmt_local(s_max)} {unit}"
    if s_min == s_max:
        return f"{fmt_local(s_min)} {unit}"
    return f"{fmt_local(s_min)}–{fmt_local(s_max)} {unit}"


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
        if any(k in query_lower for k in keywords) and numbers:
            intent["filters"][key] = numbers

    return intent

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

def text_similarity(a, b):
    if not a or not b:
        return 0.0

    tokens_a = set(re.findall(r"\w+", a.lower()))
    tokens_b = set(re.findall(r"\w+", b.lower()))

    if not tokens_a or not tokens_b:
        return 0.0

    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)

def range_overlap(a_min, a_max, b_min, b_max):
    if "" in (a_min, a_max, b_min, b_max):
        return 0.0

    a_min, a_max = float(a_min), float(a_max)
    b_min, b_max = float(b_min), float(b_max)

    overlap = max(0, min(a_max, b_max) - max(a_min, b_min))
    span = max(a_max - a_min, b_max - b_min)

    return overlap / span if span > 0 else 0.0

def compute_similarity(base, cand):
    score = 0.0

    # 0.4 text similarity
    score += 0.4 * text_similarity(
        safe_get(base, "overview"),
        safe_get(cand, "overview")
    )

    # 0.3 same animal type
    if safe_get(base, "animal_type") == safe_get(cand, "animal_type"):
        score += 0.3

    # 0.2 size overlap
    score += 0.2 * range_overlap(
        safe_get(base, "length_cm_min"),
        safe_get(base, "length_cm_max"),
        safe_get(cand, "length_cm_min"),
        safe_get(cand, "length_cm_max")
    )

    return score


def fetch_related(doc, rows=30):

    animal_type = doc.get("animal_type", ['Animal'])

    
    params = {
        "q": f"animal_type:{animal_type[0]}",
        "rows": rows,
        "fl": ",".join([
            "id", "name", "scientific_name", "animal_type",
            "overview",
            "length_cm_min", "length_cm_max",
            "image_url", "url"
        ]),
        "wt": "json"
    }

    resp = requests.get(SOLR_URL, params=params)
    data = resp.json()

    # console.log(
    #     "docs:",
    #     json.dumps(data.get("response", {}).get("docs", []), indent=2)
    # )

    return data.get("response", {}).get("docs", [])


def show_related(doc):

    candidates = fetch_related(doc)
    scored = []
    for cand in candidates:
        if cand.get("id") == doc.get("id"):
            continue 

        score = compute_similarity(doc, cand)
        scored.append((score, cand))

    # sort based on similarity
    scored.sort(key=lambda x: x[0], reverse=True)


    limit = 5
    reccomended = []

    for pair in scored[:limit]:
        doc = pair[1]
        reccomended.append(doc)


    results_container = document.querySelector(".reccomended-results")
    results_container.innerHTML = f"<h2>You might also like, based on {safe_get(doc, "animal_type")}</h2>"
    

    for r in reccomended:
        
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
                    <a href="{safe_get(r, "url", "Unknown")}" target="_blank">
                        {safe_get(r, "name", "Unknown")} - {safe_get(r, "scientific_name", "Unknown")}
                    </a>
                    <p class="overview">
                        {safe_get(r, "dirty_overview", "No overview available")}
                    </p>
                </div>

                <img class="animal-img"
                    src="{safe_get(r, "image_url", "../resources/images/anto19.png")}"
                    alt="{safe_get(r, "name", "Unknown")}">
            </div>
        """
        
        results_container.appendChild(item)


def search(query, rows=10):
    intent = parse_query_intent(query)

    fq = []

    if "weight" in intent["filters"]:
        v = intent["filters"]["weight"][0]
        fq.append(
            f"weight_kg_min:[* TO {v}] AND weight_kg_max:[{v} TO *]"
        )

    if "size" in intent["filters"]:
        v = intent["filters"]["size"][0]
        fq.append(
            f"length_cm_min:[* TO {v}] AND length_cm_max:[{v} TO *]"
        )

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
        "fl": ",".join([
            "id", "name", "scientific_name", "animal_type", "image_url", "url", "dirty_overview",
            "weight_kg_min", "weight_kg_max",
            "length_cm_min", "length_cm_max",
            "lifespan_year_min", "lifespan_year_max",
            "population_min", "population_max",
            "how_to_identify", "summary", "overview"
        ]),
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


    # filters
    weight_div = document.querySelector("#weight_kg")
    size_div = document.querySelector("#length_cm")
    population_div = document.querySelector("#population")
    min_class = ".min-input"
    max_class = ".max-input"
    animal_type_div = document.querySelector("#animal-type")

    weight_value_min = weight_div.querySelector(min_class).value
    weight_value_max = weight_div.querySelector(max_class).value
    weight_range = [float(weight_value_min), float(weight_value_max)]

    size_value_min = size_div.querySelector(min_class).value
    size_value_max = size_div.querySelector(max_class).value
    size_range = [float(size_value_min), float(size_value_max)]

    population_value_min = population_div.querySelector(min_class).value
    population_value_max = population_div.querySelector(max_class).value
    population_range = [float(population_value_min), float(population_value_max)]

    checkboxes = animal_type_div.querySelectorAll(
        ".animal-type-options input[type='checkbox']"
    )

    selected_types = [
        cb.value
        for cb in checkboxes
        if cb.checked
    ]
    
    query = searchbar.value
    #console.log(f"Searching for: {query}")

    results = search(query)
    results_container = document.querySelector(".top-results")
    results_container.innerHTML = '<h2 class="title">TOP RESULTS</h2>'

    
    results_to_display = 3
    clusters = cluster_by_animal_type(results=results[results_to_display:])

    for r in results[:results_to_display]:

        # TODO also add to user profile
       
        show_related(r);
            
        source = detect_source(r.get("url", ""))

        weight = [
            r.get("weight_kg_min"),
            r.get("weight_kg_max")
        ]

        size = [
            r.get("length_cm_min"),
            r.get("length_cm_max")
        ]

        population = [
            r.get("population_min"),
            r.get("population_max")
        ]

        animal_type = r.get("animal_type")
        
        if is_filter_enabled("weight_kg"):
            if None in weight:
                continue

            w_min = float(weight[0][0])
            w_max = float(weight[1][0])

            if max(w_min, weight_range[0]) > min(w_max, weight_range[1]):
                continue
        
        if is_filter_enabled("length_cm"):
            if None in size:
                continue

            s_min = float(size[0][0])
            s_max = float(size[1][0])

            if max(s_min, size_range[0]) > min(s_max, size_range[1]):
                continue
        
        if is_filter_enabled("population"):
            if None in population:
                continue

            p_min = float(population[0][0])
            p_max = float(population[1][0])

            if max(p_min, population_range[0]) > min(p_max, population_range[1]):
                continue

        if is_filter_enabled("animal-type"):
            if animal_type is None:
                continue

            type = animal_type[0]

            if type not in selected_types:
                continue

        format_weight = format_stat(weight, "kg")
        format_size = format_stat(size, "cm")
        format_population = format_stat(population)
        item = document.createElement("div")
        item.className = "item"

        item.innerHTML = f"""
            <div class="logo">
                <img class="logo-img" src="{source['logo']}" alt="{source['name']}">
                <p>{source['name']}</p>
            </div>

            <div class="result">
                <img class="animal-img"
                    src="{safe_get(r, "image_url", "../resources/images/anto19.png")}"
                    alt="{safe_get(r, "name", "Unknown")}">
                <div class="text">
                    <a href="{safe_get(r, "url", "Unknown")}" target="_blank">
                        {safe_get(r, "name", "Unknown")} - {safe_get(r, "scientific_name", "Unknown")}
                    </a>
                    <p class="overview">
                        {safe_get(r, "dirty_overview", "No overview available")}
                    </p>
                </div>
                <div class="animal-information">
                    <div class="animal-type-info">
                        <p>Animal Type</p>
                        <p>{animal_type[0]}</p>
                    </div>
                    <div class="animal-weight">
                        <p>Weight</p>
                        <p>{format_weight}</p>
                    </div>
                    <div class="animal-size">
                        <p>Lenght</p>
                        <p>{format_size}</p>
                    </div>
                    <div class="animal-population">
                        <p>Population</p>
                        <p>{format_population}</p>
                    </div>
                </div>
            </div>
        """

        results_container.appendChild(item)

    cluster_container = document.querySelector("#topics-container")
    cluster_container.innerHTML = ""
    for animal_type, data in clusters:
        toggle_btn = document.createElement("button")
        toggle_btn.className = "filter-toggle"
        toggle_btn.innerText = f"{animal_type} ▼"

        cluster_div = document.createElement("div")
        cluster_div.className = "cluster"

        cluster_container.appendChild(toggle_btn)
        cluster_container.appendChild(cluster_div)

        for doc in data["docs"]:
            source = detect_source(safe_get(doc, "url"))

            weight2 = [
                doc.get("weight_kg_min"),
                doc.get("weight_kg_max")
            ]

            size2 = [
                doc.get("length_cm_min"),
                doc.get("length_cm_max")
            ]

            population2 = [
                doc.get("population_min"),
                doc.get("population_max")
            ]

            animal_type2 = doc.get("animal_type")
            
            if is_filter_enabled("weight_kg"):
                if None in weight2:
                    continue

                w_min2 = float(weight2[0][0])
                w_max2 = float(weight2[1][0])

                if max(w_min2, weight_range[0]) > min(w_max2, weight_range[1]):
                    continue
            
            if is_filter_enabled("length_cm"):
                if None in size2:
                    continue

                s_min2 = float(size2[0][0])
                s_max2 = float(size2[1][0])

                if max(s_min2, size_range[0]) > min(s_max2, size_range[1]):
                    continue
            
            if is_filter_enabled("population"):
                if None in population2:
                    continue

                p_min2 = float(population2[0][0])
                p_max2 = float(population2[1][0])

                if max(p_min2, population_range[0]) > min(p_max2, population_range[1]):
                    continue

            if is_filter_enabled("animal-type"):
                if animal_type2 is None:
                    continue

                type2 = animal_type2[0]

                if type2 not in selected_types:
                    continue

            format_weight2 = format_stat(weight2, "kg")
            format_size2 = format_stat(size2, "cm")
            format_population2 = format_stat(population2)
            item = document.createElement("div")
            item.className = "item"

            item.innerHTML = f"""
                <div class="logo">
                    <img class="logo-img" src="{source['logo']}" alt="{source['name']}">
                    <p>{source['name']}</p>
                </div>

                <div class="result">
                    <img class="animal-img"
                        src="{safe_get(doc, "image_url", "../resources/images/anto19.png")}"
                        alt="{safe_get(doc, "name", "Unknown")}">
                    <div class="text">
                        <a href="{safe_get(doc, "url", "Unknown")}" target="_blank">
                            {safe_get(doc, "name", "Unknown")} - {safe_get(doc, "scientific_name", "Unknown")}
                        </a>
                        <p class="overview">{safe_get(doc, "dirty_overview", "No overview available.")}</p>
                    </div>
                    <div class="animal-information">
                        <div class="animal-type-info">
                            <p>Animal Type</p>
                            <p>{animal_type2[0]}</p>
                        </div>
                        <div class="animal-weight">
                            <p>Weight</p>
                            <p>{format_weight2}</p>
                        </div>
                        <div class="animal-size">
                            <p>Lenght</p>
                            <p>{format_size2}</p>
                        </div>
                        <div class="animal-population">
                            <p>Population</p>
                            <p>{format_population2}</p>
                        </div>
                    </div>
                </div>
            """

            cluster_div.appendChild(item)
