import scrapy
import json

API_TOKEN = "PUT_YOUR_TOKEN_HERE"

# run command: scrapy crawl iucn -O iucn.json

class IucnSpider(scrapy.Spider):
    name = "iucn"
    # allowed_domains = ["apiv3.iucnredlist.org"]

    # DONT NECESSARILY WORK - NEED TO CHECK WEBSITE
    # species_list = ["panthera_tigris", "elephas_maximus", "gorilla_gorilla"]

    async def start(self):
        for sp in self.species_list:
            url = f"https://apiv3.iucnredlist.org/api/v3/species/{sp}?token={API_TOKEN}"
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        data = json.loads(response.text)
        result = data.get("result", [{}])[0]

        yield {
            "source": "IUCN",
            "scientific_name": result.get("scientific_name"),
            "category": result.get("category"),
            "population_trend": result.get("population_trend"),
            "habitat": result.get("habitat"),
            "threats": result.get("threats"),
            "meta": result,
        }
