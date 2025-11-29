import io
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import scrapy
from warcio.archiveiterator import ArchiveIterator

# run command: python3 -m scrapy crawl wildlife_trusts

def safe_filename(url: str) -> str:
    name = re.sub(r'^https?://', '', url)
    name = re.sub(r'[^a-zA-Z0-9_-]+', '_', name)
    return name[:200]

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
        data["summary"] = summary

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
        data["conservation_status"] = status

    # ---------- STATISTICS ----------
    stats_div = soup.find("div", class_=lambda c: c and "species-statistics" in c)
    if stats_div:
        label = stats_div.find("h3")
        if label:
            label.extract()

        stats_text = stats_div.get_text(separator="\n", strip=True)
        data["statistics"] = stats_text

    # ---------- ABOUT ----------
    about_div = soup.find("div", class_=lambda c: c and "species-about" in c)
    if about_div:
        label = about_div.find("h2")
        if label:
            label.extract()

        about_text = about_div.get_text(strip=True)
        data["about"] = about_text

    # ---------- HOW TO IDENTIFY ----------
    id_div = soup.find("div", class_=lambda c: c and "species-identify" in c)
    if id_div:
        label = id_div.find("h2")
        if label:
            label.extract()

        id_text = id_div.get_text(strip=True)
        data["how_to_identify"] = id_text

    # ---------- DISTRIBUTION ----------
    dis_div = soup.find("div", class_=lambda c: c and "species-distribution" in c)
    if dis_div:
        label = dis_div.find("h2")
        if label:
            label.extract()

        dis_text = dis_div.get_text(strip=True)
        data["distribution"] = dis_text

    # ---------- DID YOU KNOW ----------
    dyk_div = soup.find("div", class_=lambda c: c and "species-did-you-know" in c)
    if dyk_div:
        label = dyk_div.find("h2")
        if label:
            label.extract()

        dyk_text = dyk_div.get_text(strip=True)
        data["did_you_know"] = dyk_text

    return data


class WildlifeTrustsSpider(scrapy.Spider):
    name = "wildlife_trusts"
   
    async def start(self):

        index_url = "http://index.commoncrawl.org/CC-MAIN-2025-43-index?url=www.wildlifetrusts.org/wildlife-explorer/*&output=json"

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
            f"Retrieved WARC segment for {response.meta['original_url']} "
            f"({len(response.body)} bytes)"
        )

        for record in ArchiveIterator(io.BytesIO(response.body)):
            if record.rec_type != "response":
                continue

            html_bytes = record.content_stream().read()
            html_text = html_bytes.decode("utf-8", errors="ignore")

            extracted = extract_wt_species_data(html_text, response.meta["original_url"])

            # JSON FILE OUTPUT
            json_filename = f"wt-{safe_filename(response.meta['original_url'])}.json"
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(extracted, f, indent=2, ensure_ascii=False)

            # HTML FILE OUTPUT
            #filename = f"wwf-{safe_filename(response.meta['original_url'])}.html"
            #Path(filename).write_text(html_text, encoding="utf-8")
            #self.log(f"Saved {filename}")
