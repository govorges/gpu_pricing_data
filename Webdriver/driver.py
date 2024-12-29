"""Contains the WebDriver class"""

from playwright.sync_api import sync_playwright
from playwright.sync_api import BrowserContext, Page, ElementHandle

from Webdriver.config import load_configuration

import sys
from os import path

# I don't know how imports work
sys.path.append(path.join(path.dirname(path.realpath(__file__)), ".."))

from Logs.logs import Logger
from Errors.errors import ErrorHandler, error_handler_hook

class WebDriver:
    """A wrapper to manage sync_playwright browser instances with error handling & logging for Frogscraper."""
    def __init__(self, logger: Logger = None, errorhandler: ErrorHandler = None, _conf: dict = None, _playwright: sync_playwright = None, **kwargs):
        self._playwright = _playwright if _playwright else sync_playwright().start()
        self.Configuration = _conf if _conf else load_configuration() 

        self.Logger = logger
        self.ErrorHandler = errorhandler

        engine_type = self.Configuration["engine"]
        match engine_type:
            case "firefox":
                self.Browser = self._playwright.firefox
            case "chromium":
                self.Browser = self._playwright.chromium
            case "webkit":
                self.Browser = self._playwright.webkit
       
        # TODO: kwargs config parsing
        self.Browser = self.Browser.launch(
            headless = self.Configuration['headless'], **kwargs
        )
        # TODO: something something context handling.
        #   from docs: browser.new_context(proxy={"server": "http://myproxy.com:3128"})
        self._default_context = self.create_browser_context()
    
    # thought process is to wrap Page.goto() so I can perform some error handling & logging of my own
    #   maybe screenshot of page when there are issues? lot of options very neat.
    @error_handler_hook
    def restart_browser(self, **kwargs):
        self.Browser = self.Browser.launch(
            headless = self.Configuration['headless'], **kwargs
        )

    @error_handler_hook # todo: think of cooler name for this
    def create_page_in_context(self, context: BrowserContext = None) -> Page:
        '''
        Creates a new page in the provided `context` and navigates to the provided URL.
        If `context` is unset, uses WebDriver._default_context.
        '''
        if context is None:
            context = self._default_context
        
        if self.Logger is not None:
            self.Logger.Info(f"Webdriver: Creating page in {'_default_context' if context is self._default_context else str(context)}")
        
        page = context.new_page()

        return page
    
    @error_handler_hook
    def navigate_page_to_url(self, url: str, page: Page, **kwargs) -> None:
        '''
        Navigates an existing Page to the provided URL.
        Kwargs are passed to a Page.goto() call, additional configuration available using this.
        '''
        if self.Logger is not None:
            self.Logger.Info(f"Webdriver: Navigating a page to: {url}")

        page.goto(url, **kwargs)
        if kwargs.get('wait_until') is None:
            page.wait_for_load_state("domcontentloaded")

        return None

    @error_handler_hook
    def create_browser_context(self, **kwargs) -> BrowserContext:
        if self.Logger is not None:
            self.Logger.Info(f"Webdriver: Creating browser context with kwargs: {str(**kwargs) if len(kwargs) > 0 else 'None (defaults)'}")

        return self.Browser.new_context(**kwargs)
    
    @error_handler_hook
    def select_one(self, page: Page, selector: str, timeout: float = None, state: str = None, strict: bool = False) -> ElementHandle:
        if self.Logger is not None:
            self.Logger.Info(f"Webdriver: select_one ; Finding selector `{selector}` in page `{Page}` with args: [timeout: {timeout} ; state: {state} ; strict: {strict}]")
        
        element = page.wait_for_selector(
            selector = selector,
            timeout = timeout,
            state = state,
            strict = strict
        )
        return element
    
    @error_handler_hook
    def select_all(self, page: Page, selector: str) -> list[ElementHandle]:
        if self.Logger is not None:
            self.Logger.Info(f"Webdriver: select_all ; Finding selector `{selector} in page `{Page}`")
        elements = page.query_selector_all(selector)
        return elements
        
    
if __name__ == "__main__":
    logger = Logger()
    errorhandler = ErrorHandler(logger=logger)

    # driver configuration is taken from Config/driver.json
    #       but a _conf (dict) can be passed during init for more specific testing
    driver = WebDriver(
        logger = logger,
        errorhandler = errorhandler
    )

    # page_context = driver.create_browser_context()
    page = driver.create_page_in_context()
    driver.navigate_page_to_url("https://google.com", page, wait_until="domcontentloaded")
    #       Alternatively: page.wait_for_load_state("domcontentloaded")
    image_elements = driver.select_all(
        page=page, selector="img"
    )
    print([el.get_attribute('src') for el in image_elements])

