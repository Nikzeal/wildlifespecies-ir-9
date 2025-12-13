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
            data["population"] = value
        elif "scientific name" in key:
            data["scientific_name"] = value
        elif "habitats" in key:
            data["habitats"] = value
        elif "places" in key:
            data["places"] = value
        elif "length" in key:
            data["length"] = value
        elif "weight" in key:
            data["weight"] = value


   
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
                json_filename = "ww-all_wwf_species.json"
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(self.collected, f, indent=2, ensure_ascii=False)

                

