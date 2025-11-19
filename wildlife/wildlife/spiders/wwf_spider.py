import scrapy

# run command: scrapy crawl wwf -O wwf.json

class WwfSpider(scrapy.Spider):
    name = "wwf"
    allowed_domains = ["worldwildlife.org"]

    # DONT NECESSARILY WORK - NEED TO CHECK WEBSITE
    selectors = {
        "links": "a.card--link::attr(href)",
        "title": "h1::text",
        "scientific_name": "span.scientific-name::text",
        "main_info": "div.field--body p::text",
        "threats": "div.threats p::text",
        "habitat": "div.habitat p::text"
    }

    async def start(self):
        start_urls = ["https://www.worldwildlife.org/species/"]
        
        for url in start_urls:
            yield scrapy.Request(url=url, callback=self.parse)


    def parse(self, response):
        for link in response.css(self.selectors["links"]).getall():
            if "/species/" in link:
                yield response.follow(link, callback=self.parse_species)

    def parse_species(self, response):
        yield {
            "source": "WWF",
            "url": response.url,
            "title": response.css(self.selectors["title"]).get(),
            "scientific_name": response.css(self.selectors["scientific_name"]).get(),
            "main_info": " ".join(response.css(self.selectors["main_info"]).getall()).strip(),
            "threats": response.css(self.selectors["threats"]).getall(),
            "habitat": response.css(self.selectors["habitat"]).getall(),
        }
