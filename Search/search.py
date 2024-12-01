# vendors
#    query selectors for search information
#    url building
#    configuration of behavior such as clearing session storage, breaking captchas, etc
#   

# run_search(vendor, query, **kwargs)
# 
import sys
from os import path

from flask import Flask

api = Flask(__name__)
api.config

from urllib.parse import urlparse, ParseResult
# I don't know how imports work
sys.path.append(path.join(path.dirname(path.realpath(__file__)), ".."))

from Logs.logs import Logger
from Errors.errors import ErrorHandler, error_handler_hook
from Webdriver.driver import WebDriver

from vendor import Vendor
from listing import Listing
from Search.config import load_configuration

from bs4 import BeautifulSoup
import chardet # yeah, I read docs. how'd you know?
import lxml # for clarity of imports. this is required for the bs4 implementation

from price_parser import Price

from playwright.sync_api import Page

def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme and parsed.netloc

def build_url_from_relative_href(url: ParseResult, href: str) -> str:
    return f"{url.scheme}://{url.netloc}{href}"

class SearchHandler:
    def __init__(self, webdriver: WebDriver, errorhandler: ErrorHandler, logger: Logger = None, _conf: dict = None) -> None:
        self.WebDriver = webdriver
        self.ErrorHandler = errorhandler
        self.Logger = logger

        self._default_context = self.WebDriver._default_context

        self.Configuration = _conf if _conf else load_configuration()

        vendor_data = self.Configuration.get('vendors', {})

        assert len(vendor_data.keys()) > 0, \
            f"No vendors configured in SearchHandler."
        
        self.Vendors = []
        for key in vendor_data.keys():
            vendor = Vendor(
                identifier = key,
                metadata = vendor_data[key]['metadata'],
                url = vendor_data[key]['url'],
                selectors = vendor_data[key]['selectors']
            )
            self.Vendors.append(vendor)

        if self.Logger is not None:
            self.Logger.Info(f"SearchHandler: Loaded {len(self.Vendors)} vendors ; [{', '.join([x.identifier for x in self.Vendors])}]")
    
    @error_handler_hook
    def defer_environment_error(self, exception_type: Exception, *args):
        raise exception_type(*args)

    @error_handler_hook
    def find_vendor_by_identifier(self, identifier: str) -> Vendor:
        for vendor in self.Vendors:
            if vendor.identifier == identifier:
                return vendor
        return None

    @error_handler_hook
    def retrieve_search_listings(self, page: Page, vendor: str | Vendor, query: str) -> list:
        search_page = page
        if isinstance(vendor, str):
            _vendor = self.find_vendor_by_identifier(vendor)
            if _vendor is None:
                raise ValueError(f"No vendor with the given identifier, `{vendor}` was found.")
            vendor: Vendor = _vendor
        
        if self.Logger is not None:
            self.Logger.Info(f"SearchHandler: Retrieving search listings ; vendor: {vendor.identifier} ; query: {query}")
        
        target_search_url = f"{vendor.url['start']}{query}{vendor.url['end']}"
        assert is_valid_url(target_search_url), \
            f"Constructed URL, {target_search_url} is not valid. Check vendor: {vendor.identifier} configuration."

        start = time.time()
        self.WebDriver.navigate_page_to_url(target_search_url, search_page, wait_until='commit')
        search_page.wait_for_selector("body")
        end = time.time()
        print(f"navigate_page_to_url: {round(end - start, 4)}s")

        start = time.time()        
        soup = BeautifulSoup(search_page.content(), 'lxml')
        end = time.time()
        print(f"page.content() -> BeautifulSoup: {round(end - start, 4)}s")

        #listings = self.WebDriver.select_all(search_page, vendor.selectors['listings'])
        start = time.time()
        listings = soup.select(vendor.selectors['listings'])
        end = time.time()
        print(f"BeautifulSoup.select(listings): {round(end - start, 4)}")
        assert len(listings) > 0, \
            f"No listings were found." # simple messages as its best to defer to errorhandler at this point

        selectors = vendor.selectors.copy()
        selectors.pop('listings')

        output_listings = []

        listing_time_start = time.time()
        for item in listings: # mega-nester 451
            item_data = {}
            for key in selectors.keys():
                selector_data = selectors[key]
                selected_element = item.select_one(selector_data['css_selector'])
                if selected_element is None:
                    continue

                match selector_data['type']:
                    case 'text':
                        value = selected_element.text
                    case 'link':
                        value = selected_element.attrs.get('href')
                        if not is_valid_url(value) and value is not None:
                            value = build_url_from_relative_href(
                                urlparse(target_search_url), value
                            )
                    case 'image':
                        value = selected_element.attrs.get('src')
                        if not is_valid_url(value) and value is not None:
                            value = build_url_from_relative_href(
                                urlparse(target_search_url), value
                            )
                    case 'price':
                        value = Price.fromstring(selected_element.text)
                        value = value.amount_float
                item_data[key] = value

            missing_keys = []
            for key in item_data.keys():
                if item_data[key] is None and selectors[key].get('required', False):
                    missing_keys.append(key)
            if len(missing_keys) > 0:
                self.defer_environment_error(
                    ValueError,
                    f"Required keys, [{', '.join([x for x in missing_keys])}] not found in listing.",
                    f"{str(item)}"
                )
                continue
                
            listing = Listing(item_data)
            output_listings.append(listing)

        listing_time_end = time.time()
        print(f'listings parse time: {round(listing_time_end - listing_time_start, 8)}')
        return output_listings
        

if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    from Webdriver.config import load_configuration as driver_conf

    import time
    from statistics import mean

    _playwright = sync_playwright().start()
    conf = driver_conf()

    logger = Logger()
    errorhandler = ErrorHandler(logger=logger)

    conf['engine'] = 'chromium'
    webdriver = WebDriver(logger=logger, errorhandler=errorhandler, _conf=conf, _playwright=_playwright)
    sh = SearchHandler(webdriver, errorhandler = errorhandler, logger = logger)
    usa_newegg: Vendor = sh.find_vendor_by_identifier("usa_newegg")

    page = webdriver.create_page_in_context()
    page.route("**/*.{png,jpg,jpeg,css,gif,js}", lambda route: route.abort())
    webdriver.navigate_page_to_url(usa_newegg.metadata.get("homepage"), page, wait_until='commit')

    print("usa_newegg search load times\n")

    print("CHROMIUM RESULTS:")
    start = time.time()
    listings: list[Listing] = sh.retrieve_search_listings(page=page, vendor=usa_newegg, query="\"RTX 4090\"")
    end = time.time()
    print(f"retrieve_search_listings time elapsed: {end-start}s")

    prices = [x.Data['price'] for x in listings]
    prices = sorted(prices)
    avg_price = round(mean(prices), 2)
    print("query: `\"RTX 4090\"`")
    print(f"listings found: {len(prices)} | avg: {avg_price} | low: {prices[0]}\n\n")

    sh._default_context.close()
    webdriver.Browser.close()

    conf['engine'] = 'firefox'
    webdriver = WebDriver(logger = logger, errorhandler = errorhandler, _conf=conf, _playwright=_playwright)
    sh = SearchHandler(webdriver, errorhandler = errorhandler, logger = logger)
    
    page = webdriver.create_page_in_context()
    page.route("**/*.{png,jpg,jpeg,css,gif,js}", lambda route: route.abort())
    webdriver.navigate_page_to_url(usa_newegg.metadata.get("homepage"), page, wait_until='commit')

    print("GECKODRIVER / FIREFOX RESULTS:")
    start = time.time()
    listings: list[Listing] = sh.retrieve_search_listings(page=page, vendor=usa_newegg, query="\"RTX 4090\"")
    end = time.time()
    print(f"retrieve_search_listings time elapsed: {end-start}s")

    prices = [x.Data['price'] for x in listings]
    prices = sorted(prices)
    avg_price = round(mean(prices), 2)
    print("query: `\"RTX 4090\"`")
    print(f"listings found: {len(prices)} | avg: {avg_price} | low: {prices[0]}\n\n")

    sh._default_context.close()
    webdriver.Browser.close()
