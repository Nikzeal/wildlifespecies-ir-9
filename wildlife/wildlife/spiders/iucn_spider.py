import io
from pathlib import Path
import scrapy
import json
from warcio.archiveiterator import ArchiveIterator

API_TOKEN = "PUT_YOUR_TOKEN_HERE"

# run command: scrapy crawl iucn -O iucn.json

class IucnSpider(scrapy.Spider):
    name = "iucn"
    # allowed_domains = ["apiv3.iucnredlist.org"]

    async def start(self):
        # start_urls = [
        #     "rhttps://www.iucnredlist.org/search?seachType=species"]

        index_url = "http://index.commoncrawl.org/CC-MAIN-2024-10-index?url=www.iucnredlist.org/species/*&output=json"

        yield scrapy.Request(index_url, callback=self.parse_index)

        # for url in start_urls:
        #     yield scrapy.Request(url=url, callback=self.parse)


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
          
          for record in ArchiveIterator(io.BytesIO(response.body)):
            if record.rec_type == "response":
                html_bytes = record.content_stream().read()
                html_text = html_bytes.decode("utf-8", errors="ignore")

                page_number = response.meta["page_number"]
                filename = f"iucn-{page_number}.html"
                Path(filename).write_text(html_text, encoding="utf-8")
                self.log(f"Saved {filename}")
                
                # yield {
                #     "url": response.meta["original_url"],
                #     "page_number": page_number,
                #     "html": html_text
                # }

        
