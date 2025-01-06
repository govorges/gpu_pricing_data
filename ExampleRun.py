from Webdriver import driver
from Search import search
from Search.vendor import Vendor
from Query import query

from Logs import logs
from Errors import errors

import time
import datetime

import json
from statistics import mean

from os import mkdir, path

LOCAL_DIR = path.dirname(path.realpath(__file__))

Logger = logs.Logger()
error_handler = errors.ErrorHandler(logger=Logger)

webdriver = driver.WebDriver(logger = Logger, _playwright = None)
search_context = webdriver.create_browser_context()
search_page = webdriver.create_page_in_context(search_context)

query_list = query.QueryList("GPUs.json")

search_handler = search.SearchHandler(
    webdriver = webdriver,
    errorhandler = error_handler,
    logger = Logger
)

def RunSearchForVendor(vendor: Vendor):
    vendor_output_data = {
        "date": str(datetime.datetime.now().date())
    }
    if vendor.preload is not None:
        webdriver.navigate_page_to_url(vendor.preload, search_page)

    for item in query_list.Queries:
        if vendor.preload is None: search_context.clear_cookies()

        time.sleep(3) # This can be removed, but may yield unreliable results depending on a site's traffic limits.

        retrieved_listings = search_handler.retrieve_search_listings(page=search_page, vendor=vendor, query=item)
        print(f"{vendor.identifier} ; {item.Content} ; {len(retrieved_listings)} listings found!")

        if len(retrieved_listings) == 0:
            continue
        retrieved_listings = sorted(retrieved_listings, key=lambda x: x.Data.get("price")) # O(36,000,000,000,000)

        item_prices = [x.Data.get("price") for x in retrieved_listings]
        for listing in retrieved_listings:
            strip_phrases = vendor.strip_phrases
            for key in listing.Data.keys():
                if isinstance(listing.Data[key], str):
                    for x in strip_phrases: listing.Data[key] = listing.Data[key].replace(x, "") 

        vendor_output_data[item.Content] = {
            "price (low)": retrieved_listings[0].Data.get("price"),
            "price (mean)": round(mean(item_prices), 2),
            "listings": [x.Data for x in retrieved_listings]
        }
    
    OUTPUT_DIR = path.join(LOCAL_DIR, "output")
    if not path.isdir(OUTPUT_DIR): mkdir(OUTPUT_DIR)

    with open(path.join(OUTPUT_DIR, f"{vendor.identifier}.json"), "w+") as vendor_output_file:
        vendor_output_file.write(json.dumps(vendor_output_data, indent=4))

if __name__ == "__main__":
    vendor = search_handler.find_vendor_by_identifier("usa_newegg")
    RunSearchForVendor(vendor=vendor)

    webdriver.Browser.close()
