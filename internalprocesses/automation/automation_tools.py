import json
import os

from dotenv import load_dotenv


class AutomationTools:
    def __init__(self) -> None:
        load_dotenv()
        self.config = self._read_config()

    @staticmethod
    def _read_config() -> dict:
        """Returns the loaded config.json file."""

        cd = os.path.dirname(__file__)
        config_file = os.path.join(cd, "..", "..", "data/config.json")
        return json.load(open(config_file))
