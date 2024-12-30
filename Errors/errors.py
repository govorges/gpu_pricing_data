from playwright.sync_api import BrowserContext, Page

from os import path, listdir
from os import remove as remove_file

from threading import Thread

import traceback
import datetime
import json

from Logs.logs import Logger

from .config import load_configuration

ERRORS_DIR = path.dirname(path.realpath(__file__))

def error_handler_hook(func):
    """
    Function decorator, dumps any exceptions in the wrapped function to save_error_information. 
    This requires the wrapped function to be in the context of a class with an ErrorHandler set.
    """
    def wrapper(*args, **kwargs):
        super = args[0] # self
        super_error_handler: ErrorHandler = None
        for item in super.__dict__.keys():
            dict_item = super.__dict__[item]
            if isinstance(dict_item, ErrorHandler):
                super_error_handler = dict_item
        try:
            return func(*args, **kwargs)
        except Exception as E:
            if super_error_handler is not None:
                # Setting a wrapped function's name as the "real" call if we're using ErrorHandler.wrap_function()
                if func.__name__ == "wrap_function" and isinstance(super, ErrorHandler): # in case something else has a "wrap_function" function
                    function_name = args[1].__name__ if isinstance(args[1], func.__class__) else func.__name__
                else:
                    function_name = func.__name__
                
                if super_error_handler.Configuration['threaded']:
                    t = Thread(
                        target=super_error_handler.save_error_information,
                        args=(E, super, function_name, *args),
                        kwargs=kwargs
                    ).start()
                else:
                    super_error_handler.save_error_information(E, super, function_name, *args, **kwargs)
            else:
                raise E
    return wrapper

class ErrorHandler:
    def __init__(self, logger: Logger):
        self.Logger = logger
        self.Configuration = load_configuration()
        self._eh = self

        # Clearing out old files in Errors/errors based on our "purge" config setting
        if self.Configuration['purge']:
            errors_path = path.join(ERRORS_DIR, "errors")
            existing_error_files = listdir(errors_path)
            
            if self.Logger is not None:
                self.Logger.Info(f"ErrorHandler: Clearing out old error reports (purge: True in Config/errors.json). Removing: {existing_error_files}")

            for filename in existing_error_files:
                remove_file(path = path.join(errors_path, filename))
    
    @error_handler_hook
    def wrap_function(self, func, *args, **kwargs):
        '''Wraps a target function to handle errors outside of the context of an existing class.'''
        if self.Logger is not None:
            self.Logger.Info(f"ErrorHandler: wrap_function ; {func.__name__} args: {args} | kwargs: {kwargs}")
        return func(*args, **kwargs)

    def save_error_information(self, exception: Exception, super, func, *args, **kwargs):
        """Creates a dump of exception details in frogscraper/Errors/errors, files are output as a .JSON file with a UNIX timestamp as the filename."""
        error_output_path = ""
        while path.isfile(error_output_path) or error_output_path == "":
            timestamp = datetime.datetime.now().timestamp()
            error_output_path = path.join(ERRORS_DIR, "errors", f"{timestamp}.json")

        # I thought json.dumps tried to str() objects itself. it does not.
        data = {
            "type": str(exception.__class__),
            "exception": [x for x in exception.args],
            "traceback": "".join(traceback.TracebackException.from_exception(exception).format()),
            "call": func,
            "timestamp": datetime.datetime.now().timestamp(),
            "environment": {
                "super": {x: str(super.__dict__[x]) for x in super.__dict__.keys()},
                "args": str([arg for arg in args]),
                "kwargs": { kw: str(kwargs[kw]) for kw in kwargs.keys() }
            }
        }
        if self.Configuration['screenshots']:
            screenshots = []
            for item in args:
                if not isinstance(item, BrowserContext):
                    continue
                for page in item.pages:
                    index = item.pages.index(page)
                    screenshot_file = f"{timestamp}-{index}.png"

                    screenshots.append(screenshot_file)
                    page.screenshot(
                        path = path.join(ERRORS_DIR, screenshot_file)
                    )

            default_context: BrowserContext = super.__dict__.get('_default_context')
            if default_context is not None:
                for page in default_context.pages:
                    index = default_context.pages.index(page)
                    screenshot_file = f"{timestamp}-default-{index}.png"

                    screenshots.append(screenshot_file)
                    page.screenshot(
                        path = path.join(ERRORS_DIR, "errors", screenshot_file)
                    )
            data['screenshots'] = screenshots

        
        if self.Logger is not None:
            self.Logger.Error(f"ErrorHandler: {str(exception.__class__)} in {func} | Detailed report in {error_output_path.rsplit(path.sep, 1)[-1]}")

        with open(error_output_path, "w+") as error_output_file:
            error_output_file.write(json.dumps(data, indent=4))

