import datetime
from os import path

from Logs.config import load_configuration

LOGS_DIR = path.dirname(path.realpath(__file__))

class Logger:
    """Homebrew Logger implementation. Outputs to frogscraper/Logs/logfiles in a YYYY-MM-DD.log format."""
    def __init__(self):
        self.Configuration = load_configuration()
        self.log_file_path = path.join(self.Configuration['log_folder'], self.Configuration['file'])

        if not path.isfile(self.log_file_path):
            open(self.log_file_path, "w+")
        self.Log = open(self.log_file_path, "a+")
    def write_to_log(self, type: str, content: str):
        self.Log.write(f"[{type}] | {content}\n")
        self.Log.flush()
    def Info(self, content: str): self.write_to_log("INFO", content)
    def Warn(self, content: str): self.write_to_log("WARN", content)
    def Error(self, content: str): self.write_to_log("ERROR", content)
    def Fatal(self, content: str): self.write_to_log("FATAL", content)



     



