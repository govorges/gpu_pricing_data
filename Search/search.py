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

from urllib.parse import urlparse, ParseResult, urljoin
# I don't know how imports work
sys.path.append(path.join(path.dirname(path.realpath(__file__)), ".."))

from Logs.logs import Logger
from Errors.errors import ErrorHandler, error_handler_hook
from Webdriver.driver import WebDriver

from Search.vendor import Vendor
from Search.listing import Listing
from Search.config import load_configuration

from Query.query import Query

from bs4 import BeautifulSoup
import chardet # yeah, I read docs. how'd you know?
import lxml # for clarity of imports. this is required for the bs4 implementation

from price_parser import Price

from playwright.sync_api import Page

def is_valid_url(url: str) -> bool:
    """Check if a provided URL is valid and can be parsed by urlparse."""
    parsed = urlparse(url)
    return parsed.scheme != "" and parsed.netloc != ""

def build_url_from_relative_href(url: ParseResult, href: str) -> str:
    return f"{url.scheme}://{url.netloc}{href}"

class SearchHandler:
    def __init__(self, webdriver: WebDriver = None, errorhandler: ErrorHandler = None, logger: Logger = None, _conf: dict = None) -> None:
        self.WebDriver = webdriver
        self.ErrorHandler = errorhandler
        self.Logger = logger

        self._default_context = self.WebDriver._default_context if self.WebDriver is not None else None

        self.Configuration = _conf if _conf else load_configuration()

        vendor_data = self.Configuration.get('vendors', {})

        assert len(vendor_data.keys()) > 0, \
            f"No vendors configured in SearchHandler."
        
        self.Vendors: list[Vendor] = []
        for key in vendor_data.keys():
            vendor = Vendor(
                identifier = key,
                metadata = vendor_data[key]['metadata'],
                url = vendor_data[key]['url'],
                selectors = vendor_data[key]['selectors'],
                strip_phrases = vendor_data[key].get('strip_phrases', []),
                preload =  vendor_data[key].get("preload")
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
    def retrieve_search_listings(self, page: Page, vendor: str | Vendor, query: Query) -> list:
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

        self.WebDriver.navigate_page_to_url(target_search_url, search_page, wait_until='domcontentloaded')
        
        search_page.wait_for_selector("body")
        search_page.wait_for_selector(vendor.selectors["listings"])

        soup = BeautifulSoup(search_page.content().encode("utf-8"), 'lxml')

        #listings = self.WebDriver.select_all(search_page, vendor.selectors['listings'])
        listings = soup.select(vendor.selectors['listings'])
        if len(listings) == 0 or listings is None:
            return []
        
        selectors = vendor.selectors.copy()
        selectors.pop('listings')

        output_listings = []

        # This is used when checking if a listing's price is within the Query's MinimumValue & MaximumValue. 
        # Populated by any items with the 'price' value type in vendor CSS selectors
        # Overwritten by subsequent items with this type set. 
        # Ideal use case for this : grabbing a "default" price before grabbing a "discounted" price will have the default price overwritten by the discounted.
        price = None
        # Additive price is used for other misc costs that should be added on top of the total listing price. 
        #       This value(s) are not pushed to the listing.Data object, and solely exist behind the scenes of your queries.
        #               Additive prices add to eachother, so if there are multiple elements you need for this, no worries.
        additive_price = 0.00


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
                        value = urljoin(value, urlparse(value).path)
                    case 'image':
                        value = selected_element.attrs.get('src')
                        if not is_valid_url(value) and value is not None:
                            value = build_url_from_relative_href(
                                urlparse(target_search_url), value
                            )
                    case 'price':
                        value = Price.fromstring(selected_element.text)
                        value = value.amount_float

                        price = value
                    case 'misc_price': # A value treated as a price, but does not overwrite the main 'price' value.
                        value = Price.fromstring(selected_element.text)
                        value = value.amount_float
                    case 'additive_price':
                        value = Price.fromstring(selected_element.text)
                        value = value.amount_float

                        additive_price += value
                item_data[key] = value

            missing_keys = []
            for key in item_data.keys():
                if item_data[key] is None and selectors[key].get('required', False):
                    missing_keys.append(key)
            if len(missing_keys) > 0:
                self.Logger.Warn(f"SearchHandler: Dropped Listing for {query} ; Required keys, [{', '.join([x for x in missing_keys])}] not found in listing. (check deferred environment error for more details)")
                self.defer_environment_error(
                    ValueError,
                    f"Required keys, [{', '.join([x for x in missing_keys])}] not found in listing.",
                    f"{str(item)}"
                )
                continue
                
            listing = Listing(item_data)

            check_strings = []
            for key in listing.Data.keys():
                key_data = listing.Data[key]
                if not isinstance(key_data, str):
                    continue
                elif selectors[key]["type"] in ["link", "image"]:
                    continue
                check_strings.append(key_data)

            if price is None:
                continue

            price += additive_price

            check_result = query.IsValidListing(check_strings, price)
            if isinstance(check_result, bool) and check_result:
                output_listings.append(listing)
            else:
                self.Logger.Info(f"SearchHandler: Dropped Listing for {query} ; check_result: {check_result} ; {str(listing.Data).encode()}")
                
        return output_listings
        

if __name__ == "__main__":
    assert is_valid_url("https://google.com"), \
        "https://google.com - Should have been a valid URL."
    assert not is_valid_url("google.com"), \
        "google.com - Should have not been a valid URL"
    assert not is_valid_url("/example-url-path?a=123&b=456"), \
        "/example-url-path?a=123&b=456 - Should have not been a valid URL"
    print("All assertions OK")