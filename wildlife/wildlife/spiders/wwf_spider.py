import io
from pathlib import Path
import scrapy
import json
from warcio.archiveiterator import ArchiveIterator

class WwfSpider(scrapy.Spider):
    name = "wwf"
    #allowed_domains = ["worldwildlife.org"]

    async def start(self):
        # start_urls = [
        #     "https://www.worldwildlife.org/species/?page=1",
        #     # "https://www.worldwildlife.org/species/?page=2",
        #     # "https://www.worldwildlife.org/species/?page=3",
        #     # "https://www.worldwildlife.org/species/?page=4",
        #     # "https://www.worldwildlife.org/species/?page=5"] 
        # ]

        index_url = "http://index.commoncrawl.org/CC-MAIN-2024-10-index?url=www.worldwildlife.org/species*&output=json"

        yield scrapy.Request(index_url, callback=self.parse_index)
        # for url in start_urls:
        #     yield scrapy.Request(
        #         url=url, 
        #         callback=self.parse, 
        #         )


    def parse_index(self, response):
        for line in response.text.splitlines():
            data = json.loads(line)
            page_number = data["url"].split("page=")[-1] if "page=" in data["url"] else "1"

        warc_url = f"https://data.commoncrawl.org/{data['filename']}"
        meta = {
            "offset": int(data["offset"]),
            "length": int(data["length"]),
            "original_url": data["url"],
            "page_number": page_number
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
                filename = f"wwf-{page_number}.html"
                Path(filename).write_text(html_text, encoding="utf-8")
                self.log(f"Saved {filename}")
                
                # yield {
                #     "url": response.meta["original_url"],
                #     "page_number": page_number,
                #     "html": html_text
                # }
