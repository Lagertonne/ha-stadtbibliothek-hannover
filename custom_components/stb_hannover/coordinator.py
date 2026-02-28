from datetime import timedelta
import logging
import re
import asyncio

from aiohttp import ClientResponse, ClientSession, ClientTimeout
from bs4 import BeautifulSoup
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from datetime import datetime

from .const import LOGGER


class StbApi:
    def __init__(self, session: ClientSession, username: str, password: str) -> None:
        self.session = session
        self._username = username
        self._password = password
        self._obj_id = ""

    async def _method_request(self, method) -> ClientResponse:
        login_test_response = await self.session.get(
            "https://bibliothek.hannover-stadt.de/alswww3.dll/APS_ZONES?fn=MyZone&Style=Portal3&SubStyle=&Lang=GER&ResponseEncoding=utf-8"
        )

        # Set Obj_id
        self._obj_id = re.search(
            "Obj_[a-zA-Z0-9]+", await login_test_response.text()
        ).group()

        if 'title="Logout"' in await login_test_response.text():
            LOGGER.debug("Already logged in")
        else:
            LOGGER.debug("Need to login again!")
            await self._login()

        url = f"https://bibliothek.hannover-stadt.de/alswww3.dll/{self._obj_id}?Style=Portal3&SubStyle=&Lang=GER&ResponseEncoding=utf-8?Method={method}"
        LOGGER.debug(f"Doing request to {url}")

        response = await self.session.get(url)
        self._obj_id = re.search("Obj_[a-zA-Z0-9]+", await response.text()).group()

        return await self.session.get(url)

    async def _login(self) -> None:
        params = {
            "fn": "MyZone",
            "Style": "Portal3",
            "SubStyle": "",
            "Lang": "GER",
            "ResponseEncoding": "utf-8",
        }

        LOGGER.debug("Logging in!")

        # Get initial session
        r = await self.session.get(
            "https://bibliothek.hannover-stadt.de/alswww3.dll/APS_ZONES", params=params
        )

        # It seems that we get a new obj_id on every request... Parse it, and save it into the class-variable
        self._obj_id = re.search("Obj_[a-zA-Z0-9]+", await r.text()).group()

        LOGGER.debug(f"Current obj_id {self._obj_id}")

        login_params = {
            "Method": "CheckID",
            "ZonesLogin": 1,
            "Interlock": self._obj_id,
            "BrowseAsHloc": "",
            "Style": "Portal3",
            "SubStyle": "",
            "Lang": "GER",
            "ResponseEncoding": "utf-8",
            "BRWR": self._username,
            "PIN": self._password,
        }

        # Do the actual Login-Request
        # TODO Error handling
        resp = await self.session.post(
            f"https://bibliothek.hannover-stadt.de/alswww3.dll/{self._obj_id}",
            data=login_params,
        )

        # Save the next obj_id
        LOGGER.debug("Setting the new obj_id...")
        resp_text = await resp.text()

        self._obj_id = re.search("Obj_[a-zA-Z0-9]+", resp_text).group()

    async def get_books(self) -> list[dict]:
        response = await self._method_request(
            f"https://bibliothek.hannover-stadt.de/alswww3.dll/{self._obj_id}?Style=Portal3&SubStyle=&Lang=GER&ResponseEncoding=utf-8?Method=ShowLoans"
        )

        response = await self._method_request("ShowLoans")
        resp_text = await response.text()
        soup = BeautifulSoup(resp_text, "html.parser")

        browse_list = soup.find(id="BrowseList").find_all("tr", recursive=False)

        books = []
        for book_raw in browse_list:
            book = {}
            for cell in book_raw.find_all("td", {"class": "LoanBrowseFieldNameCell"}):
                key = cell.contents[0]
                data = cell.parent.find("td", {"class": "LoanBrowseFieldDataCell"})

                if key == "Titel":
                    book["title"] = data.find("a").contents[0].strip()
                elif key == "Verfasser":
                    book["author"] = data.contents[0].strip()
                elif key == "Verbuchungsnummer":
                    book["id"] = data.contents[0].strip()
                elif key == "ausgeliehen in":
                    book["rental_place"] = data.contents[0].strip()
                elif key == "Ausleihdatum":
                    book["loan_date"] = datetime.strptime(data.contents[0].strip(), "%d.%m.%Y")
                elif key == "Rückgabedatum":
                    book["return_date"] = datetime.strptime(data.find("b").contents[0].strip(), "%d.%m.%Y")

            books.append(book)

        return books


class StbUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: StbApi) -> None:
        super().__init__(
            hass,
            LOGGER,
            name="STB Hannover",
            update_interval=timedelta(hours=1),
        )

        self.api = api

    async def _async_update_data(self) -> dict[str, any]:
        async with asyncio.timeout(30):
            LOGGER.debug("Start async_update_data()")
            books = await self.api.get_books()

            result = {
                "books": books,
            }

            return result
