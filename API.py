"""An API worker for the Frogscraper project to serve data over HTTP."""
from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright
from statistics import mean
import datetime

from Webdriver import driver
from Search import search
from Query.query import Query

from Logs import logs
from Errors import errors


api = Flask(__name__)
api_Logger = logs.Logger()
api_ErrorHandler = errors.ErrorHandler(api_Logger)

with api.app_context():
    print("API Running!")

@api.route("/vendors", methods=["GET"])
def retrieve_vendors():
    request_search_handler = search.SearchHandler(
        webdriver = None,
        errorhandler = api_ErrorHandler,
        logger = api_Logger
    )

    vendors = {}
    for vendor in request_search_handler.Vendors:
        vendors[vendor.identifier] = {
            "metadata": vendor.metadata,
            "selectors": vendor.selectors,
            "url": vendor.url
        }
    return jsonify(vendors)

@api.route("/search/<string:vendor_identifier>")
def run_search_for_vendor(vendor_identifier):
    webdriver = driver.WebDriver(
        logger = api_Logger,
        _playwright = sync_playwright().start()
    )
    request_search_handler = search.SearchHandler(
        webdriver = webdriver,
        errorhandler = api_ErrorHandler,
        logger = api_Logger
    )


    search_vendor = request_search_handler.find_vendor_by_identifier(vendor_identifier)
    if search_vendor is None:
        return jsonify({
            "message": "No vendor with the provided identifier was found!",
            "code": 400
        })
    
    query = request.json.get("query")
    if query is None:
         return jsonify({
            "message": "No query was provided!",
            "code": 400
        })
    query = Query(
        Content = query['Content'],
        Include = query.get("Include", []),
        IncludeSettings = query.get("IncludeSettings", {}),
        Exclude = query.get("Exclude", []),
        ExcludeSettings = query.get("ExcludeSettings", {}),
        ValueRange = (query.get("MinimumValue", 0), query.get("MaximumValue", 9999999))
    )
    
    search_context = webdriver.create_browser_context()
    page = webdriver.create_page_in_context(search_context)

    output_data = {
        "time_start": str(datetime.datetime.now().timestamp())
    }
    

    if search_vendor.preload is not None:
        webdriver.navigate_page_to_url(
            url = search_vendor.preload,
            page = page
        )
    else:
        search_context.clear_cookies()

    retrieved_listings = request_search_handler.retrieve_search_listings(
        page = page,
        vendor = search_vendor,
        query = query
    )
    if retrieved_listings is None or len(retrieved_listings) == 0:
        output_data[query.Content] = {
            "price (low)": None,
            "price (mean)": None,
            "listings": []
        }
        output_data['time_end'] = str(datetime.datetime.now().timestamp())
        return jsonify(output_data)
    
    retrieved_listings = sorted(retrieved_listings, key=lambda x: x.Data.get("price"))
    item_prices = [x.Data.get("price") for x in retrieved_listings]

    for listing in retrieved_listings:
        strip_phrases = search_vendor.strip_phrases
        for key in listing.Data.keys():
            if isinstance(listing.Data[key], str):
                for x in strip_phrases: listing.Data[key] = listing.Data[key].replace(x, "") 
    
    output_data[query.Content] = {
        "price (low)": retrieved_listings[0].Data.get("price"),
        "price (mean)": round(mean(item_prices), 2),
        "listings": [x.Data for x in retrieved_listings],
    }
    output_data['time_end'] = str(datetime.datetime.now().timestamp())

    search_context.close()
    webdriver.Browser.close()

    return jsonify(output_data)


if __name__ == "__main__":
    api.run("127.0.0.1", port=8080, debug=True)