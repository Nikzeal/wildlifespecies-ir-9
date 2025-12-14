import io
from pathlib import Path
from bs4 import BeautifulSoup
import scrapy
import json
from warcio.archiveiterator import ArchiveIterator
import re
from wildlife.utils.text_cleaner import clean_text
from wildlife.utils.type_detector import detect_type

# def safe_filename(url: str) -> str:
#     name = re.sub(r'^https?://', '', url)
 
#     name = re.sub(r'[^a-zA-Z0-9_-]+', '_', name)
#     return name[:200] 


# def html_to_json(html_file):
#     with open(html_file, 'r', encoding='utf-8') as file:
#         soup = BeautifulSoup(file, 'html.parser')
#         json_data = json.dumps(soup, indent=2, ensure_ascii=False)

#     return json_data

def extract_numbers(text):
    if not text:
        return []
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]


def pounds_to_kg(lb):
    return lb * 0.453592


def tons_to_kg(tons):
    return tons * 1000.0


def feet_to_cm(ft):
    return ft * 30.48


def inches_to_cm(inch):
    return inch * 2.54

def meters_to_cm(m):
    return m * 100

def parse_weight_kg(raw):
    nums = extract_numbers(raw.lower())
    if not nums:
        return None

    if "ton" in raw.lower():
        nums = [tons_to_kg(n) for n in nums]
    elif "pound" in raw.lower() or "lb" in raw.lower():
        nums = [pounds_to_kg(n) for n in nums]
    elif "kg" in raw.lower():
        pass  # already kg

    return nums if len(nums) > 1 else nums[0]

def parse_population(raw):
    if not raw:
        return None

    text = raw.lower().replace(",", "")
    nums = extract_numbers(text)

    if not nums:
        return None

    if "million" in text:
        nums = [int(n * 1_000_000) for n in nums]
    elif "thousand" in text:
        nums = [int(n * 1_000) for n in nums]
    else:
        nums = [int(n) for n in nums]

    if "less than" in text or "<" in text:
        return [0, nums[0]]

    if len(nums) > 1:
        return [min(nums), max(nums)]

    return nums[0]

def split_clauses(text):
    return re.split(r"[;,]", text)

def parse_length_clause(clause):
    clause = clause.lower()
    nums = extract_numbers(clause)

    if not nums:
        return None, None

    if len(nums) >= 2:
        values = [min(nums), max(nums)]
    else:
        values = nums[0]

    if "meter" in clause:
        values = [v * 100 for v in values] if isinstance(values, list) else values * 100
    elif "foot" in clause or "ft" in clause:
        values = [v * 30.48 for v in values] if isinstance(values, list) else values * 30.48
    elif "inch" in clause:
        values = [v * 2.54 for v in values] if isinstance(values, list) else values * 2.54

    if "tail" in clause:
        return "tail_length_cm", values
    if "wing" in clause or "wingspan" in clause:
        return "wingspan_cm", values
    if "shoulder" in clause or "tall" in clause or "height" in clause:
        return "shoulder_height_cm", values

    return "length_cm", values


def parse_lengths(raw):
    if not raw:
        return {}

    result = {}

    for clause in split_clauses(raw):
        key, value = parse_length_clause(clause)
        if key and value is not None:
            if key not in result:
                result[key] = value

    return result


def extract_wwf_species_data(html_text, source_url):


    # object:
    # {
    #     "url": source_url,
     #    "img_url": url_of_image,
    #     "name": "...",
    #     "status": "...",
    #     "population": "...",
    #     "habitats": "...",
    #     "places": "...",
    #     "scientific_name": "...",
    #     "weight": "...",
    #     "length": "...",
    #     "overview": "...",
    #     "why_they_matter": "...",
    #     "threats": [ "...", "...", "..."] || "...",
    #     "related_species": [ "...", "...", "..."] || "...",
    # }

  

    soup = BeautifulSoup(html_text, "html.parser")

    

    data = {"url": source_url}

    name = soup.find("title")
    if name:
        data["name"] = name.get_text(strip=True).split("|")[0].strip()


    content = soup.find("div", id="content")

    if content:
        img = soup.find("div", id="content").find("img")
        if img and img.has_attr("src"):
            data["image_url"] = img["src"]


    for li in soup.select("ul.list-data li, ul.list-spaced li"):
        strong = li.find("strong", class_="hdr")
        if not strong:
            continue
        
        key = strong.get_text(strip=True).lower()

      
        div = strong.find_next_sibling("div")
        if not div:
            continue
        
        value = div.get_text(strip=True)

        if "status" in key:
            data["status"] = value
        elif "population" in key:
            data["raw_population"] = value
        elif "scientific name" in key:
            data["scientific_name"] = value
        elif "habitats" in key:
            data["habitats"] = value
        elif "places" in key:
            data["places"] = value
        elif "length" in key:
            data["raw_length"] = value
        elif "weight" in key:
            data["raw_weight"] = value


   
    overview = soup.select_one("#overview p")
    if overview:
        detected_type = detect_type(overview.get_text(strip=True))
        data["animal_type"] = detected_type
        data["dirty_overview"] = overview.get_text(strip=True)
        data["overview"] = clean_text(overview.get_text(strip=True))

    threats = []
    threat_div = soup.select_one("#threats .lead.wysiwyg")

    if threat_div:
        for p in threat_div.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                threats.append(clean_text(text))

    if threats:
        data["threats"] = threats


    why = soup.select_one("#why-they-matter p")
    if why:
        data["why_they_matter"] = clean_text(why.get_text(strip=True))

    related = []
    for a in soup.select("div.carousel a strong.name"):
        related.append(a.get_text(strip=True))

    if related:
        data["related_species"] = related

    statistics = {}

    if "raw_weight" in data:
        parsed_weight = parse_weight_kg(data["raw_weight"])
        if parsed_weight:
            statistics["weight_kg"] = parsed_weight

    if "raw_length" in data:
        length_fields = parse_lengths(data["raw_length"])
        statistics.update(length_fields)

        
    if "raw_population" in data:
        parsed_population = parse_population(data["raw_population"])
        if parsed_population is not None:
            statistics["population"] = parsed_population

    if statistics:
        data["statistics"] = statistics

    return data

class WwfSpider(scrapy.Spider):
    name = "wwf"

    def __init__(self):
        self.collected = []
        self.names_seen = []
   

    async def start(self):
        index_url = "http://index.commoncrawl.org/CC-MAIN-2025-43-index?url=www.worldwildlife.org/species/*&output=json"
        yield scrapy.Request(index_url, callback=self.parse_index)



    def parse_index(self, response):

        pattern = re.compile(r"^https?://www\.worldwildlife\.org/species/[^/]+/?$")


        for line in response.text.splitlines():
            data = json.loads(line)

            if not pattern.match(data["url"]):
                continue

            warc_url = f"https://data.commoncrawl.org/{data['filename']}"
            meta = {
                "offset": int(data["offset"]),
                "length": int(data["length"]),
                "original_url": data["url"],
            }

            yield scrapy.Request(
                warc_url,
                callback=self.parse_warc,
                headers={
                    "Range": f"bytes={meta['offset']}-{meta['offset'] + meta['length'] - 1}"
                },
                meta=meta
            )




    def parse_warc(self, response):

        self.logger.info(
            f"Retrieved response for {response.meta['original_url']} "
            f"({response} bytes)"
        )
        
        for record in ArchiveIterator(io.BytesIO(response.body)):
            
            if record.rec_type == "response":
                html_bytes = record.content_stream().read()
                html_text = html_bytes.decode("utf-8", errors="ignore")

               
                extracted = extract_wwf_species_data(html_text, response.meta["original_url"])

                if not extracted.get("name") or "Page Not Found" in extracted.get("name") or "Sorry" in extracted.get("name"):
                    return
                
                
                # remove duplicates
                if extracted["name"].lower() in self.names_seen:
                    return
                
                self.names_seen.append(extracted.get("name").lower())

                self.collected.append(extracted)


                yield extracted
                json_filename = "wwf.json"
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(self.collected, f, indent=2, ensure_ascii=False)

                

