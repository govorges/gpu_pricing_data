from os import system, path, chdir, mkdir
import json

# Setting wdir to bin/
BIN_DIR = path.dirname(path.realpath(__file__))
chdir(BIN_DIR)

# Cloning frogscraper repo into bin/frogscraper
if path.isdir("./frogscraper"):
    system("git pull https://github.com/govorges/frogscraper")
else:
    system("git clone https://github.com/govorges/frogscraper")
assert path.isdir('./frogscraper'), "govorges/frogscraper was not successfully cloned."

# Vendors.json contains a list of vendor identifiers that we will scrape using frogscraper.
with open("./vendors.json", "r") as vendorsFile:
    vendors = json.loads(vendorsFile.read())
assert len(vendors) > 1, "vendors.json is empty, no vendors will be scraped."

from frogscraper.Webdriver import driver
from frogscraper.Search import search
from frogscraper.Search.vendor import Vendor
from frogscraper.Query import query

from frogscraper.Logs import logs
from frogscraper.Errors import errors

import time
import datetime
import json

Logger = logs.Logger()
ErrorHandler = errors.ErrorHandler(logger=Logger)

webdriver = driver.WebDriver(logger = Logger, _playwright = None)

search_context = webdriver.create_browser_context()
search_page = webdriver.create_page_in_context(search_context)

search_handler = search.SearchHandler(
    webdriver = webdriver,
    errorhandler = ErrorHandler,
    logger = Logger
)

gpuQueryList = query.QueryList("GPUs.json")

for vendor in vendors:
    vendor: Vendor = search_handler.find_vendor_by_identifier(vendor)
    vendor_output_data = {
        "date": str(datetime.datetime.now().timestamp())
    }
    if vendor.preload is not None:
        webdriver.navigate_page_to_url(vendor.preload, search_page)
    
    for queryItem in gpuQueryList.Queries:
        if vendor.preload is None:
            search_context.clear_cookies()
        
        time.sleep(3)

        retrieved_listings = search_handler.retrieve_search_listings(
            page = search_page,
            vendor = vendor,
            query = queryItem
        )

        if len(retrieved_listings == 0):
            continue
        retrieved_listings = sorted(retrieved_listings, key=lambda x: x.Data.get("price"))
        
        for listing in retrieved_listings:
            strip_phrases = vendor.strip_phrases
            for key in listing.Data.keys():
                if isinstance(listing.Data[key], str):
                    for x in strip_phrases: listing.Data[key] = listing.Data[key].replace(x, "")

        vendor_output_data[queryItem.Content] = {
            "listings": [x.Data for x in retrieved_listings]
        }
    





