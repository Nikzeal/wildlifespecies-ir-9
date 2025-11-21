from pathlib import Path
import scrapy
import json

API_TOKEN = "PUT_YOUR_TOKEN_HERE"

# run command: scrapy crawl iucn -O iucn.json

class IucnSpider(scrapy.Spider):
    name = "iucn"
    # allowed_domains = ["apiv3.iucnredlist.org"]

    async def start(self):
        start_urls = [
            "https://www.iucnredlist.org/search?searchType=species"]
        
        for url in start_urls:
            yield scrapy.Request(url=url, callback=self.parse)


    def parse(self, response):
        page = response.url.split("/")[-2]
        filename = f"iucn-{page}.html"
        Path(filename).write_bytes(response.body)
        self.log(f"Saved file {filename}")

        
