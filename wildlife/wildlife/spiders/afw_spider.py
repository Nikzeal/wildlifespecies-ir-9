import io
from pathlib import Path
import re
from bs4 import BeautifulSoup
import scrapy
import json
from warcio.archiveiterator import ArchiveIterator
from wildlife.utils.text_cleaner import clean_text
from wildlife.utils.type_detector import detect_type

# run command: scrapy crawl awf -O awf.json

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

def extract_numbers(text):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]


def parse_weight_kg(text):
    mins, maxs = [], []

    for part in text.split(";"):
        nums = extract_numbers(part)

        if not nums:
            continue

        if re.search(r"ton", part, re.I):
            nums = [n * 1000 for n in nums]
        elif re.search(r"pound|lb", part, re.I):
            nums = [n * 0.453592 for n in nums]
        # else assume kg

        mins.append(min(nums))
        maxs.append(max(nums))

    if mins:
        return [min(mins), max(maxs)]
    return None


def parse_length_cm(text):
    mins, maxs = [], []

    for part in text.split(";"):
        nums = extract_numbers(part)

        if not nums:
            continue

        if re.search(r"meter|meters|\bm\b", part):
            nums = [n * 100 for n in nums]
        elif re.search(r"centimeter|cm", part):
            nums = nums
        else:
            continue

        mins.append(min(nums))
        maxs.append(max(nums))

    if mins:
        return [min(mins), max(maxs)]
    return None


def parse_lifespan_year(text):
    nums = extract_numbers(text)
    if not nums:
        return None
    return [min(nums), max(nums)] if len(nums) > 1 else [nums[0]]


def parse_gestation_days(text):
    nums = extract_numbers(text)
    if not nums:
        return None

    if re.search(r"month", text, re.I):
        nums = [n * 30 for n in nums]

    return [min(nums), max(nums)] if len(nums) > 1 else [nums[0]]


def extract_awf_species_data(html_text, source_url):
    soup = BeautifulSoup(html_text, "html.parser")
    data = {"url": source_url}
    data["statistics"] = {}

    # ---------- NAME ----------
    name_title = soup.find("h1", class_="views-field-title")
    if name_title:
        name = name_title.find("span", class_="field-content")
        if name:
            data["name"] = name.get_text(strip=True)
    
    # ---------- OVERVIEW ----------
    overview_section = soup.find("div", id="overview")
    if overview_section:
        first_p = overview_section.find("p")
        if first_p:
            detected_type = detect_type(first_p.get_text(strip=True))
            data["animal_type"] = detected_type
            data["dirty_overview"] = first_p.get_text(strip=True)
            data["overview"] = clean_text(first_p.get_text(strip=True))

        facts = overview_section.find_all("div", class_="paragraph--type--facts")
        for fact in facts:
            label = fact.find("div", class_="field--name-field-facts-label")
            value = fact.find("div", class_="field--name-field-facts-description")

            if label and value:
                key = label.get_text(strip=True).lower()
                val = value.get_text(strip=True)

    # ---------- LOCATION ----------
                if key == "habitat":
                    data["location"] = val

    # ---------- WEIGHT ----------
                elif key == "weight":
                    data["raw_weight"] = val
                    parsed = parse_weight_kg(val)
                    if parsed:
                        data["statistics"]["weight_kg"] = parsed
    
    # ---------- HEIGHT ----------
                elif key == "size":
                    data["raw_size"] = val
                    parsed = parse_length_cm(val)
                    if parsed:
                        data["statistics"]["length_cm"] = parsed

    # ---------- LIFE SPAN ---------- 
                elif key == "life span":
                    data["raw_lifespan"] = val
                    parsed = parse_lifespan_year(val)
                    if parsed:
                        data["statistics"]["lifespan_year"] = parsed

    # ---------- DIET ----------
                elif key == "diet":
                    data["diet"] = val

    # ---------- GESTATION ----------
                elif key == "gestation":
                    data["raw_gestation"] = val
                    parsed = parse_gestation_days(val)
                    if parsed:
                        data["statistics"]["gestation_days"] = parsed

    # ---------- PREDATORS ----------
                elif key == "predators":
                    data["predators"] = val

    # ---------- SCIENTIFIC NAME ----------
                elif key == "scientific name":
                    data["scientific_name"] = val

    # ---------- THREATS ----------
    threats_section = soup.find("div", class_="field--name-field-challenges")
    threats_list = []
    if threats_section:
         for item in threats_section.find_all("p"):
             text = item.get_text(strip=True)
             if text:
                 threats_list.append(clean_text(text))
    data["threats"] = threats_list

    # ---------- FACTS LIST ----------
    facts = []

    fact_blocks = soup.find_all("div", class_="paragraph--type--overview-facts")

    for block in fact_blocks:
        top = block.find("div", class_="field--name-field-overview-facts-top")
        number = block.find("div", class_="field--name-field-overview-fact-number")
        bottom = block.find("div", class_="field--name-field-overview-fact-bottom")

        top_text = top.get_text(strip=True) if top else ""
        number_text = number.get_text(strip=True) if number else ""
        bottom_text = bottom.get_text(strip=True) if bottom else ""

        combined = f"{top_text} {number_text} {bottom_text}".strip()
        facts.append(combined)

    data["facts"] = facts

    # ---------- IMAGE URL ----------
    picture = soup.find("picture")
    if picture:
        first_source = picture.find("source")
        if first_source and first_source.get("srcset"):
            # take only the first URL from the srcset
            raw_srcset = first_source["srcset"].strip()
            first_url = raw_srcset.split()[0]

            # prepend base URL
            data["image_url"] = "https://www.awf.org" + first_url

    return data

class AwfSpider(scrapy.Spider):
    name = "awf"

    def __init__(self):
        self.collected = []

    async def start(self):

        index_url = "http://index.commoncrawl.org/CC-MAIN-2024-10-index?url=https://www.awf.org/wildlife-conservation/*&output=json"

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
            f"({len(response.body)} bytes)"
        )

        for record in ArchiveIterator(io.BytesIO(response.body)):
            if record.rec_type == "response":
                html_bytes = record.content_stream().read()
                html_text = html_bytes.decode("utf-8", errors="ignore")

                extracted = extract_awf_species_data(
                    html_text,
                    response.meta["original_url"]
                )

                 # skip missing names
                if not extracted.get("name"):
                    return

                # force https
                if extracted["url"].startswith("http://"):
                    extracted["url"] = "https://" + extracted["url"][len("http://"):]

                # remove URLs starting with https://www. (to remove duplicates)
                if extracted["url"].startswith("https://www."):
                    continue

                self.collected.append(extracted)

                yield extracted
                json_filename = "awf.json"
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(self.collected, f, indent=2, ensure_ascii=False)
        
