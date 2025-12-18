# wildlifespecies-ir-9

**STEPS TO RUN THE PROJECT:**


**STEP 1:**
Install VS Studio Live Server Extension (https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer)

**STEP 2:**
Open solr-9.10.0 folder we provided (since there are all our settings inside) in terminal and start Solr (by running `bin/solr start`)

**STEP 3 (OPTIONAL, we already did it):**
Create a new Apache Solr collection named wild_life (by running `bin/solr create -c wild_life`). If you want to create it again, make sure to delete the previously existing one (by running `bin/solr delete -c wild_life`), if any

**STEP 4:**
Move to our project environment (go under `wildlifespecies-ir-9/wildlife`)

**STEP 5 (OPTIONAL, we already did it):**
Run all 3 spiders (by running `scrapy crawl wildlife_trusts`, `scrapy crawl wwf` and `scrapy crawl awf`)

**STEP 6:**
Index the data (by running the indexing script with the command `python3 index_to_solr.py`)

**STEP 7:**
Open the html with the VS Studio Live Server Extension (directly from VS Studio, should be running on port 5500 otherwise )