import logging
import os

import requests

from src.domain.generic.http_methods import HTTPMethods


logger = logging.getLogger(__name__)


class TrackingChecker:

    def __init__(self):
        self._headers = {
            "Content-Type": "application/json",
            "Tracktry-Api-Key": os.getenv("TRACKTRY-KEY")
        }
        self._baseURL = "https://api.tracktry.com/v1/trackings"
        self.status_code = 0

    def _request(self,
                 relative_url,
                 json=None,
                 method: HTTPMethods = HTTPMethods.GET
                 ) -> dict | None:
        """
        Request helper function that updates the status code attribute and
        returns the JSON response

        :param relative_url: relative request url
        :param json: request JSON body
        :param method: HTTP method
        :return: JSON response from API
        """
        http_response = requests.request(
            method=method.value,
            url=self._baseURL + relative_url,
            headers=self._headers,
            json=json
        )
        self.status_code = http_response.status_code

        try:
            response = http_response.json()
            print(response)
        except ValueError:
            print(http_response)
            if self.status_code == 200:
                self.status_code = 500
            logger.warning(
                "Tracktry response for %s returned invalid JSON (status %s)",
                relative_url,
                http_response.status_code,
            )
            logger.debug("Tracktry raw response: %s", http_response.text)
            return None

        self.status_code = response.get("meta", {}).get("code", self.status_code)
        return response

    def add_single_tracking(self,
                            tracking_number: str,
                            carrier: str,
                            order_id: str
                            ) -> dict | None:
        """
        Adds a single tracking number and returns the JSON response

        :param tracking_number: tracking number to add
        :param carrier: associated carrier
        :param order_id: associated order id
        :return: JSON response
        """
        url = '/post'
        json = {
            "tracking_number": tracking_number,
            "carrier_code": carrier,
            "order_id": order_id
        }
        return self._request(url, json=json, method=HTTPMethods.POST)

    def batch_add_tracking(self,
                           tracking_numbers: list[tuple[str, str, str]]
                           ) -> list[dict]:
        """
        Batch adds tracking number tuples in chunks of 40 if the input
        exceeds 40. Returns a list of responses for each chunk

        :param tracking_numbers: tuple(tracking_number, carrier_code, order_id)
        :return: list of JSON responses
        """
        url = '/batch'
        chunked_tracking_numbers = []
        chunk = []

        for i in range(len(tracking_numbers)):
            chunk.append(tracking_numbers[i])
            if i % 40 == 0:
                chunked_tracking_numbers.append(chunk)
                chunk = []

        responses = []
        for chunk in chunked_tracking_numbers:
            json = [{
                "tracking_number": tracking_number[0],
                "carrier_code": tracking_number[1],
                "orderID": tracking_number[2]
            } for tracking_number in chunk]
            responses.append(
                self._request(url, json=json, method=HTTPMethods.POST)
            )
        return responses

    def get_tracking_details(self, tracking_number: str, carrier: str) -> dict:
        """
        Returns the JSON response describing the tracking number

        :param tracking_number: tracking number to check
        :param carrier: tracking number carrier
        :return: JSON response (see
        https://www.tracktry.com/api-track-get-a-single-tracking-results)
        """
        url = f'/{carrier}/{tracking_number}'
        return self._request(url)

    def delete_tracking(self, tracking_number: str, carrier: str) -> dict:
        """ Request not working, receiving 500 error """

        url = f'{carrier}/{tracking_number}'
        return self._request(url, method=HTTPMethods.DELETE)
