import scrapy

# run command: scrapy crawl wildlife_trusts -O trusts.json

class WildlifeTrustsSpider(scrapy.Spider):
    name = "wildlife_trusts"
    allowed_domains = ["wildlifetrusts.org"]
   

    # DONT NECESSARILY WORK - NEED TO CHECK WEBSITE
    selectors = {
        "links": "a.card--link::attr(href)",
        "title": "h1::text",
        "main_info": "div.field--body p::text",
        "taxonomy": ".taxonomy-term--name::text",
        "status": "div.field--tag::text",
        "next_page": "a.pager__link--next::attr(href)"
    }

    async def start(self):
        start_urls = ["https://www.wildlifetrusts.org/wildlife-explorer"]
        
        for url in start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        for link in response.css(self.selectors["links"]).getall():
            yield response.follow(link, callback=self.parse_species)

        next_page = response.css(self.selectors["next_page"]).get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_species(self, response):
        yield {
            "source": "Wildlife Trusts",
            "url": response.url,
            "title": response.css(self.selectors["title"]).get(),
            "main_info": " ".join(response.css(self.selectors["main_info"]).getall()).strip(),
            "taxonomy": response.css(self.selectors["taxonomy"]).getall(),
            "attributes": {
                "status": response.css(self.selectors["status"]).get()
            }
        }
