import json
import struct

import pytest

from src.facade.fishbowl.fishbowl_facade import FishbowlFacade
from src.facade.fishbowl.fishbowl_status import status_codes


def _build_response(general=1000, specific=900):
    return {
        "FbiJson": {
            "FbiMsgsRs": {
                "statusCode": general,
                "TestRs": {"statusCode": specific, "statusMessage": "OK"},
            }
        }
    }


def test_prep_message_prefixes_length():
    facade = FishbowlFacade()
    payload = {"hello": "world"}

    message = facade.prepMessage(payload)

    length = struct.unpack(">L", message[:4])[0]
    assert length == len(json.dumps(payload).encode())
    assert message[4:].decode() == json.dumps(payload)


def test_parse_response_returns_json():
    facade = FishbowlFacade()
    response = facade.parseResponse('{"foo": "bar"}')
    assert response["foo"] == "bar"


def test_set_status_success_sets_attributes():
    facade = FishbowlFacade()
    facade.setStatus(_build_response())
    assert facade.general_status == 1000
    assert facade.request_specific_status == 900


def test_set_status_raises_on_general_error():
    facade = FishbowlFacade()
    with pytest.raises(Exception) as exc:
        facade.setStatus(_build_response(general=1004))
    assert "1004" in str(exc.value)


def test_set_status_raises_on_request_error():
    facade = FishbowlFacade()
    with pytest.raises(Exception):
        facade.setStatus(_build_response(specific=1003))


def test_parse_query_response_handles_list_and_string():
    facade = FishbowlFacade()
    list_response = {
        "FbiJson": {
            "FbiMsgsRs": {
                "ExecuteQueryRs": {
                    "Rows": {
                        "Row": ['"A,B"', '"C,D"']
                    }
                }
            }
        }
    }
    rows = facade._parse_query_request_response(list_response)
    assert rows == [["A", "B"], ["C", "D"]]

    single_response = {
        "FbiJson": {
            "FbiMsgsRs": {
                "ExecuteQueryRs": {
                    "Rows": {
                        "Row": '"E,F"'
                    }
                }
            }
        }
    }
    rows = facade._parse_query_request_response(single_response)
    assert rows == [["E", "F"]]


def test_send_import_request_delegates_to_send_request(mocker):
    facade = FishbowlFacade()
    facade.key = "abc"
    mock_request = mocker.patch.object(facade, "sendRequest", return_value="ok")

    result = facade.sendImportRequest(["row"], "ImportPart")

    mock_request.assert_called_once()
    payload = mock_request.call_args.args[0]
    assert payload["FbiJson"]["FbiMsgsRq"]["ImportRq"]["Type"] == "ImportPart"
    assert result == "ok"
