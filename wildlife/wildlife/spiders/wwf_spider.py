import io
from pathlib import Path
from bs4 import BeautifulSoup
import scrapy
import json
from warcio.archiveiterator import ArchiveIterator
import re

def safe_filename(url: str) -> str:
    name = re.sub(r'^https?://', '', url)
    # Replace any non-alphanumeric character with underscore
    name = re.sub(r'[^a-zA-Z0-9_-]+', '_', name)
    return name[:200] 


def html_to_json(html_file):
    with open(html_file, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
        json_data = json.dumps(soup, indent=2, ensure_ascii=False)

    return json_data


def extract_wwf_species_data(html_text, source_url):
    soup = BeautifulSoup(html_text, "html.parser")
    data = {"url": source_url}

    # ---------- OVERVIEW ----------
    overview_section = soup.find("div", id="overview")
    if overview_section:
        first_p = overview_section.find("p")
        if first_p:
            data["overview"] = first_p.get_text(strip=True)
    
    # ---------- WHY THEY MATTER ----------
    why_section = soup.find("div", id="why-they-matter")
    if why_section:
        p = why_section.find("p")
        if p:
            data["why_they_matter"] = p.get_text(strip=True)

    # ---------- THREATS ----------
    threats_section = soup.find("div", id="threats")
    threats_list = []
    if threats_section:
        # threats are usually inside <h3> or <p>
        for item in threats_section.find_all(["h3", "p"]):
            text = item.get_text(strip=True)
            if text:
                threats_list.append(text)
    data["threats"] = threats_list

    # ---------- FACTS LIST ----------
    facts_section = soup.find("div", id="content")
    facts = {}

    if facts_section:
        ul = facts_section.find("ul", class_="listing") or facts_section.find("ul")
        if ul:
            for li in ul.find_all("li"):
                key_tag = li.find("strong")
                if key_tag:
                    key = key_tag.get_text(strip=True).rstrip(":")
                    value = key_tag.next_sibling.strip() if key_tag.next_sibling else ""
                    facts[key] = value

    data["facts"] = facts

    return data

class WwfSpider(scrapy.Spider):
    name = "wwf"

    def __init__(self):
        self.collected = []
   

    async def start(self):
        index_url = "http://index.commoncrawl.org/CC-MAIN-2025-43-index?url=www.worldwildlife.org/species/*&output=json"
        yield scrapy.Request(index_url, callback=self.parse_index)



    def parse_index(self, response):
        for line in response.text.splitlines():
            data = json.loads(line)
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

                self.collected.append(extracted)

                json_filename = "ww-all_wwf_species.json"
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(self.collected, f, indent=2, ensure_ascii=False)

                

