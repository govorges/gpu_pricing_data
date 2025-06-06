from os import system, path, chdir, mkdir, rmdir, remove, walk, chmod
import stat
import json
import sys
import shutil

# Setting wdir to bin/
BIN_DIR = path.dirname(path.realpath(__file__))
chdir(BIN_DIR)

# Fixing permissions of the git repo & then destroying it violently.
if not path.isdir("./frogscraper"):
    for root, dirs, files in walk("./frogscraper"):
        for item in [*dirs, *files]:
            if "frogscraper" not in root: # failsafe
                continue
            chmod(path.join(root, item), stat.S_IRWXU)
    shutil.rmtree("./frogscraper")

# system("git clone https://github.com/govorges/frogscraper")
assert path.isdir('./frogscraper'), "govorges/frogscraper was not successfully cloned."

# Vendors.json contains a list of vendor identifiers that we will scrape using frogscraper.
with open("./vendors.json", "r") as vendorsFile:
    vendors = json.loads(vendorsFile.read())
assert len(vendors) > 1, "vendors.json is empty, no vendors will be scraped."

# Fixing the imports
frogscraper_path = path.join(BIN_DIR, "frogscraper")
if frogscraper_path not in sys.path:
    sys.path.insert(0, frogscraper_path)

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

webdriver.navigate_page_to_url("https://google.com", search_page)

gpuQueryList = query.QueryList("GPUs.json")

for vendor in vendors:
    vendor: Vendor = search_handler.find_vendor_by_identifier(vendor)
    vendor_output_data = {
        "generated_at": datetime.datetime.now().timestamp()
    }
    if vendor.preload is not None:
        webdriver.navigate_page_to_url(vendor.preload, search_page)
    
    for queryItem in gpuQueryList.Queries:
        if "5090" not in queryItem.Content:
            continue
        if vendor.preload is None:
            search_context.clear_cookies()

        time.sleep(3)

        retrieved_listings = search_handler.retrieve_search_listings(
            page = search_page,
            vendor = vendor,
            query = queryItem
        )

        if len(retrieved_listings) == 0:
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
    
    OUTPUT_DIR = path.join(BIN_DIR, "..")
    assert path.isdir(OUTPUT_DIR), "Output directory does not exist somehow."

    with open(path.join(OUTPUT_DIR, f"{vendor.identifier}.json"), "w+") as vendorOutputFile:
        vendorOutputFile.write(json.dumps(vendor_output_data, indent=4))

webdriver.Browser.close()

chdir(path.join(BIN_DIR, ".."))
for vendor in vendors:
    system(f"git add {vendor}.json") 
system("git commit -a -m \"Update pricing data\"")
system("git push")