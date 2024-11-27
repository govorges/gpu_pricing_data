from playwright.sync_api import sync_playwright

from config import load_driver_configuration

class WebDriver:
    def __init__(self):
        self._playwright = sync_playwright().start()
        self.Configuration = load_driver_configuration()

        engine_type = self.Configuration["engine"]
        match engine_type:
            case "firefox":
                self.Browser = self._playwright.firefox
            case "chromium":
                self.Browser = self._playwright.chromium
            case "webkit":
                self.Browser = self._playwright.webkit
        
        self.Browser = self.Browser.launch(
            headless = self.Configuration['headless']
        )
        self.Page = self.Browser.new_page()
    
    def retrieve_page(self, url: str):
        self.Page.goto(url)

if __name__ == "__main__":
    driver = WebDriver()
    driver.retrieve_page("https://google.com/")
    driver.Page.screenshot(path="test.png")