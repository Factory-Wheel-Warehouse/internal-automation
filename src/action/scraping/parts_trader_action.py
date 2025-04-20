import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from flask import request

from src.action.selenium_action import SeleniumAction

from selenium.webdriver import Keys
from selenium.webdriver.common.by import By

from src.util.constants.scraping import A
from src.util.constants.scraping import DASHBOARD_ID
from src.util.constants.scraping import HREF
from src.util.constants.scraping import LOADING_ID
from src.util.constants.scraping import PARTS_SORT_XPATH
from src.util.constants.scraping import PARTS_TRADER_LOGIN_URL
from src.util.constants.scraping import PARTS_TRADER_QUOTES_URL
from src.util.constants.scraping import QUOTED_PARTS_CLASS
from src.util.constants.scraping import ROW_CLASS
from src.util.constants.scraping import PASSWORD_ENV_KEY
from src.util.constants.scraping import PASSWORD_INPUT_ID
from src.util.constants.scraping import SAVE_QUOTE_BUTTON_ID
from src.util.constants.scraping import USERNAME_ENV_KEY
from src.util.constants.scraping import USERNAME_INPUT_ID


@dataclass
class PartsTraderAction(SeleniumAction):

    def accept_quotes(self):
        self.login()
        self.accept_pending_quotes()

    def run(self, request_: request):
        self.setup()
        self.login()
        self.accept_pending_quotes()

    def login(self):
        self.explicit_wait_get(PARTS_TRADER_LOGIN_URL)
        user_input = [
            self.get_element(value=USERNAME_INPUT_ID),
            os.getenv(USERNAME_ENV_KEY)
        ]
        pass_input = [
            self.get_element(value=PASSWORD_INPUT_ID),
            os.getenv(PASSWORD_ENV_KEY)
        ]
        for input_field, input_value in [user_input, pass_input]:
            input_field.send_keys(input_value)
        input_field.send_keys(Keys.ENTER)
        _ = self.get_element(value=DASHBOARD_ID)

    def sort_quotes_by_parts(self):
        self.wait_for_load()
        sort = self.get_element(By.XPATH, PARTS_SORT_XPATH)
        sort.click()
        time.sleep(5)

    def accept_pending_quotes(self):
        try_next = True
        while try_next:
            self.explicit_wait_get(PARTS_TRADER_QUOTES_URL)
            self.sort_quotes_by_parts()
            pending_quotes = self.get_pending_quotes()
            print(len(pending_quotes))
            for pending_quote in pending_quotes:
                self.accept_pending_quote(pending_quote)
            if len(pending_quotes) < 1:
                try_next = False

    def get_pending_quotes(self) -> list[str]:
        row_elements = self.get_elements(By.CLASS_NAME, ROW_CLASS)
        filtered_hrefs = []
        for row_element in row_elements:
            quoted_parts = self.get_child(
                row_element, By.CLASS_NAME, QUOTED_PARTS_CLASS
            )
            quoted_parts_count = quoted_parts.text
            if int(quoted_parts_count) > 0:
                filtered_hrefs.append(
                    self.get_child(
                        row_element, By.TAG_NAME, A
                    ).get_property(HREF)
                )
        return filtered_hrefs

    def accept_pending_quote(self, href: str):
        self.explicit_wait_get(href)
        button = self.get_element(value=SAVE_QUOTE_BUTTON_ID)
        button.click()
        time.sleep(5)

    def wait_for_load(self):
        self.wait_for_element_to_hide(value=LOADING_ID)


if __name__ == "__main__":
    load_dotenv()
    PartsTraderAction().run(None)
