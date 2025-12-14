import io
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import scrapy
from warcio.archiveiterator import ArchiveIterator
from wildlife.utils.text_cleaner import clean_text
from wildlife.utils.type_detector import detect_type

# run command: python3 -m scrapy crawl wildlife_trusts

NUMBER = r"([\d\.]+)"
RANGE = rf"{NUMBER}(?:\s*-\s*{NUMBER})?"
UNIT = r"(mm|cm|m)"

def safe_filename(url: str) -> str:
    name = re.sub(r'^https?://', '', url)
    name = re.sub(r'[^a-zA-Z0-9_-]+', '_', name)
    return name[:200]

def to_cm(value: float, unit: str) -> float:
    if unit == "mm":
        return value / 10
    if unit == "cm":
        return value
    if unit == "m":
        return value * 100


def parse_statistics(stats_text: str) -> dict:
    stats = {}

    text = stats_text.lower()

    patterns = {
        "length_cm": rf"length\s+(?:around\s+|approx\s+|up\s+to\s+)?{RANGE}\s*{UNIT}",
    "height_cm": rf"height\s+{RANGE}\s*{UNIT}",
    "wingspan_cm": rf"wingspan\s+{RANGE}\s*{UNIT}",
    "tail_cm": rf"tail\s+{RANGE}\s*{UNIT}",
    "bell_diameter_cm": rf"bell\s+{RANGE}\s*{UNIT}",
    "max_size_cm": rf"(?:maximum\s+size|max\s+size)\s+{RANGE}\s*{UNIT}",
    "weight_kg": r"weight\s+(?:around\s+|approx\s+)?([\d\.]+)(?:\s*-\s*([\d\.]+))?\s*(kg|g)",
    "lifespan_year": r"(?:average\s+)?life\s*span\s+([\d\.]+)(?:\s*-\s*([\d\.]+))?\s*year",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            continue

        groups = match.groups()

        # ---------- LINEAR MEASUREMENTS ----------
        if field.endswith("_cm"):
            min_val = float(groups[0])
            max_val = groups[1]
            unit = groups[2]

            min_cm = to_cm(min_val, unit)
            if max_val:
                stats[field] = [round(min_cm, 2), round(to_cm(float(max_val), unit), 2)]
            else:
                stats[field] = round(min_cm, 2)

        # ---------- WEIGHT ----------
        elif field == "weight_kg":
            min_val = float(groups[0])
            max_val = groups[1]
            unit = groups[2]

            if unit == "g":
                min_val /= 1000
                if max_val:
                    max_val = float(max_val) / 1000

            stats[field] = (
                [round(min_val, 3), round(float(max_val), 3)]
                if max_val else round(min_val, 3)
            )

        # ---------- LIFESPAN ----------
        elif field == "lifespan_year":
            min_val = float(groups[0])
            max_val = groups[1]

            stats[field] = (
                [min_val, float(max_val)]
                if max_val else min_val
            )

    return stats

def extract_wt_species_data(html_text, source_url):
    soup = BeautifulSoup(html_text, "html.parser")
    data = {"url": source_url}

    # ---------- NAME ----------
    name = soup.find("title").get_text(strip=True).split("|")[0].strip()
    data["name"] = name

    # ---------- SUMMARY ----------
    summary_div = soup.find("div", class_="species-summary")
    if summary_div:
        summary = summary_div.get_text(strip=True)
        data["summary"] = clean_text(summary)

    # ---------- SCIENTIFIC NAME ----------
    sci_div = soup.find("div", class_=lambda c: c and "species-scientific-name" in c)
    if sci_div:
        label = sci_div.find("h3")
        if label:
            label.extract()

        scientific_name = sci_div.get_text(strip=True)
        data["scientific_name"] = scientific_name

    # ---------- CONSERVATION STATUS ----------
    cons_div = soup.find("div", class_=lambda c: c and "species-conservation" in c)
    if cons_div:
        label = cons_div.find("h3")
        if label:
            label.extract()

        status = cons_div.get_text(strip=True)
        data["conservation_status"] = clean_text(status)

    # ---------- STATISTICS ----------
    stats_div = soup.find("div", class_=lambda c: c and "species-statistics" in c)
    if stats_div:
        label = stats_div.find("h3")
        if label:
            label.extract()

        raw_stats = clean_text(stats_div.get_text(" ", strip=True))
        data["raw_statistics"] = raw_stats
        data["statistics"] = parse_statistics(raw_stats)
        

    # ---------- ABOUT ----------
    about_div = soup.find("div", class_=lambda c: c and "species-about" in c)
    if about_div:
        label = about_div.find("h2")
        if label:
            label.extract()

        about_text = about_div.get_text(strip=True)
        detected_type = detect_type(about_text)
        data["animal_type"] = detected_type
        data["dirty_overview"] = about_text
        data["overview"] = clean_text(about_text)

    # ---------- HOW TO IDENTIFY ----------
    id_div = soup.find("div", class_=lambda c: c and "species-identify" in c)
    if id_div:
        label = id_div.find("h2")
        if label:
            label.extract()

        id_text = id_div.get_text(strip=True)
        data["how_to_identify"] = clean_text(id_text)

    # ---------- DISTRIBUTION ----------
    dis_div = soup.find("div", class_=lambda c: c and "species-distribution" in c)
    if dis_div:
        label = dis_div.find("h2")
        if label:
            label.extract()

        dis_text = dis_div.get_text(strip=True)
        data["distribution"] = clean_text(dis_text)

    # ---------- DID YOU KNOW ----------
    dyk_div = soup.find("div", class_=lambda c: c and "species-did-you-know" in c)
    if dyk_div:
        label = dyk_div.find("h2")
        if label:
            label.extract()

        dyk_text = dyk_div.get_text(strip=True)
        data["did_you_know"] = clean_text(dyk_text)

    # ---------- IMAGE URL ----------
    img_url = None

    header = soup.find("div", class_="node__header--species")
    if header:
        picture = header.find("picture")
        if picture:
            first_source = picture.find("source")
            if first_source and first_source.get("srcset"):
                raw_src = first_source["srcset"].split(" ")[0]
                img_url = "https://www.wildlifetrusts.org" + raw_src

            # fallback to <img>
            if not img_url:
                img_tag = picture.find("img")
                if img_tag and img_tag.get("src"):
                    img_url = "https://www.wildlifetrusts.org" + img_tag["src"]

    data["image_url"] = img_url

    return data


class WildlifeTrustsSpider(scrapy.Spider):
    name = "wildlife_trusts"

    def __init__(self):
        self.collected = []
   
    async def start(self):

        index_url = "http://index.commoncrawl.org/CC-MAIN-2025-43-index?url=www.wildlifetrusts.org/wildlife-explorer/*&output=json"

        yield scrapy.Request(index_url, callback=self.parse_index)

    def close(self, reason):
        json_filename = "wildlifetrusts.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(self.collected, f, indent=2, ensure_ascii=False)

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
            f"Retrieved WARC segment for {response.meta['original_url']} "
            f"({len(response.body)} bytes)"
        )

        for record in ArchiveIterator(io.BytesIO(response.body)):
            if record.rec_type != "response":
                continue

            html_bytes = record.content_stream().read()
            html_text = html_bytes.decode("utf-8", errors="ignore")

            extracted = extract_wt_species_data(html_text, response.meta["original_url"])
            self.collected.append(extracted)

            # JSON FILE OUTPUT x each species
            #json_filename = f"wt-{safe_filename(response.meta['original_url'])}.json"
            #with open(json_filename, "w", encoding="utf-8") as f:
            #    json.dump(extracted, f, indent=2, ensure_ascii=False)

            # HTML FILE OUTPUT
            #filename = f"wwf-{safe_filename(response.meta['original_url'])}.html"
            #Path(filename).write_text(html_text, encoding="utf-8")
            #self.log(f"Saved {filename}")
