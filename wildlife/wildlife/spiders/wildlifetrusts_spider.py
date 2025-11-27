from pathlib import Path
import scrapy



class WildlifeTrustsSpider(scrapy.Spider):
    name = "wildlife_trusts"
    # allowed_domains = ["wildlifetrusts.org"]
   

  

    async def start(self):
        start_urls = ["https://www.wildlifetrusts.org/wildlife-explorer"]
        
        for url in start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        page = response.url.split("/")[-2]
        filename = f"wildlife_trusts-{page}.html"
        Path(filename).write_bytes(response.body)
        self.log(f"Saved file {filename}")
      
