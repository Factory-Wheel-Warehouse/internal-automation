import time
from abc import ABC

import chromedriver_autoinstaller

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.action.action import Action
from src.util.constants.scraping import SELENIUM_HEADLESS_ARGUMENT


class SeleniumAction(Action, ABC):
    chrome_driver: WebDriver = None
    wait_timeout = 5

    def setup(self):
        chromedriver_autoinstaller.install()
        self.chrome_driver = webdriver.Chrome(**{
            "options": SeleniumAction._get_webdriver_options()
        })

    @staticmethod
    def _get_webdriver_options():
        webdriver_options = Options()
        webdriver_options.add_argument(SELENIUM_HEADLESS_ARGUMENT)

    def get_element(self, by=By.ID,
                    value: str | None = None) -> WebElement | None:
        return WebDriverWait(self.chrome_driver, self.wait_timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def get_elements(self, by=By.ID,
                     value: str | None = None) -> list[WebElement]:
        return WebDriverWait(self.chrome_driver, self.wait_timeout).until(
            EC.presence_of_all_elements_located((by, value))
        )

    def get_child(self, parent: WebElement, by=By.ID,
                  value: str | None = None) -> WebElement | None:
        return WebDriverWait(parent, self.wait_timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def get_children(self, parent: WebElement, by=By.ID,
                     value: str | None = None) -> list[WebElement]:
        return WebDriverWait(parent, self.wait_timeout).until(
            EC.presence_of_all_elements_located((by, value))
        )

    def explicit_wait_get(self, url: str):
        self.chrome_driver.get(url)
        time.sleep(self.wait_timeout)

    def wait_for_element_to_hide(
            self, by=By.ID, value: str | None = None
    ) -> WebElement | None:
        return WebDriverWait(self.chrome_driver, self.wait_timeout).until(
            EC.invisibility_of_element_located((by, value))
        )
