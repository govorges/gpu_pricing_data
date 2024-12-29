# Frogscraper
A utility to scrape and aggregate pricing data from online retailers. Built using Playwright, mostly.

## Quick-Start Guide
This will get you going, but it won't teach you everything you need to know. I highly recommend you read through this documentation so you know how to operate Frogscraper to its fullest potential.

### 1. Configuration
Setting up Frogscraper is done through 90% JSON and 10% Python. First, check out frogscraper/Config for some low-level configuration options:

### Config/driver.json
```json
{
    "headless": bool | Default: true | Should the browser instance(s) be invisible while it runs searches.
    "engine": "firefox", "chromium", "webkit" | Default: "firefox"
}
```
### Config/errors.json
```json
{
    "purge": bool | Default: false | Should previous error dumps be deleted when Frogscraper launches?
    "screenshots": bool | Default: true | Should error dumps also provide screenshots of any relevant pages?
    "threaded": bool | Default: false | Should error dumps run multithreaded (not recommended in 99% of scenarios)
}
```
### Config/logs.json
```json
{
    "file": string | Default: f"{datetime.datetime.now().date()}.log" | This is not recommended to change as the string set here is not executed. If you really need to, set your own function in Logs/config.py as the default.
    "log_folder": string | Default: path.join(LOGS_DIR, "logfiles") | Same as above, this is not typically manually set, but can be if you must.
}
```
### Config/search.json
The `search.json` configuration file is a bit more complicated. This is where you set up vendor layouts and such.
```json
{
    "vendors": {
        "vendor_identifier": { // Can be set to anything. This is a key used to identify a vendor, such as "usa_ebay"
            "strip_phrases": [] | A list of phrases to be stripped from final listing string results. Typically used for alt text that isn't typically visible.
            "url": { // Your query's content will be sandwiched between the start and end.
                "start": string
                "end": string
            }
            "selectors": {
                "listings": string | REQUIRED | Should return a list of listing objects when running a "document.querySelectorAll()" on a search results page.
                Additional selectors can be added, but should be dictionaries.
                "example": { // Outputs as "example" in the data of a listing.
                    "css_selector": string | The selector of this data element when run on an individual listing object.
                    "type": "text", "link", "image", "price", "additive_price", "misc_price" | See below for more details.
                    "required": bool | If set to true, a listing will be dropped from results if this selector is missing. Typically used for prices.
                }
            }
        }
    }
}
```
#### Selector Types
##### 1. "text" - Returns the text content of a selected element.
##### 2. "link" - Returns the href of a selected element.
##### 3. "image" - Returns the src of a selected element.
##### 4. "price" - Parses a price value from the text content of a selected element then sets the Listing's price to it. 
##### 5. "additive_price" - Parses a price value from the text content of a selected element then adds it to the final price of the Listing.
##### 6. "misc_price" - Parses a price value from the text content of a selected element, but does not set the Listing's "main" price and doesn't add it to the final price.

Typically, you'll want to use at least one "`price`" selector in a vendor configuration. If there are 2 prices, a "default" price and a "discounted" price, you can set 2 selectors of type "`price`" and the one set latest will overwrite the first one (So put the discounted price last!)

### 2. Creating a Query List 
Now that you have a vendor set up and the project is configured, you can build a query list! There are some example ones included in the repository, but the basic structure is:
```json
{
    "settings": {
        "filtered_phrases": [] A list of phrases to exclude from ALL queries in this list. If a phrase is found in a listing's string data, the listing will be dropped.
    },
    "queries": [
        {
            "Content": "A product name",
            "Include": [] A list of phrases required in this query's listings.
            "IncludeSettings": {
                "operator": "and", "or", "xor" Include "___ OPERATOR ___"
                "case_sensitive": bool
                "require_content": bool | Places this query's content in the Include list. This is recommended over putting the query in the Include list manually, as it allows for additional functionality with stripping spaces and such, but there are times where this may not be helpful.
            }
            "Exclude": [] | A list of phrases required to not be in this query's listings
            "ExcludeSettings": {
                "operator": "and", "or", "xor" | Exclude "___ OPERATOR ___"
                "case_sensitive": bool
            }
            "MinimumValue": int | Drops any listings whose main price is less than this
            "MaximumValue": int | Drops any listings whose main price is greater than this
        }
    ]
}

```
### 3. Environment Setup
Now, make sure you have all the dependencies installed. Run `pip install -r requirements.txt` in the Frogscraper directory. Then, run `playwright install`. Some operating systems may have issues with certain browsers (So if you're on Linux you can't use Webkit and then everything else works fine)

### 4. Run Frogscraper
Okay, it's not *just* running Frogscraper. Now you have to build something to run. There's an example script to interface with all of this, `ExampleRun.py`. Rather than insultingly babysit you through it all, you can just take a peek at that and see how I do it myself and it should be rather self-explanatory at this point.
