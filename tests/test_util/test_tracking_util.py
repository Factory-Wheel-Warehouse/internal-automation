from types import SimpleNamespace

import pytest

from src.util.constants.tracking import EMAIL_BODY_CONTENT_KEY
from src.util.constants.tracking import EMAIL_BODY_KEY
from src.util.constants.tracking import EMAIL_ID_KEY
from src.util.tracking import util as tracking_util


def test_get_valid_tracking_numbers_filters_via_validator(mocker):
    mock_validate = mocker.patch(
        "src.util.tracking.util.tracking_is_valid",
        side_effect=lambda number, _: number.endswith("0"),
    )

    valid = tracking_util.get_valid_tracking_numbers(
        {"111", "120", "130"}, carrier="UPS"
    )

    assert sorted(valid) == ["120", "130"]
    assert mock_validate.call_count == 3


def test_get_tracking_candidates_prefers_body_over_attachments(mocker):
    emails = [{
        EMAIL_ID_KEY: "1",
        EMAIL_BODY_KEY: {EMAIL_BODY_CONTENT_KEY: "tracking 12345"},
    }]
    mock_pdf = mocker.patch("src.util.tracking.util.get_pdf_attachments")
    mock_search = mocker.patch("src.util.tracking.util.search_email_pdfs")

    candidates = tracking_util.get_tracking_candidates(
        emails,
        outlook=SimpleNamespace(),
        pattern=r"\d+",
    )

    assert candidates == {"12345"}
    mock_pdf.assert_not_called()
    mock_search.assert_not_called()


def test_get_tracking_candidates_falls_back_to_attachments(mocker):
    emails = [{
        EMAIL_ID_KEY: "2",
        EMAIL_BODY_KEY: {EMAIL_BODY_CONTENT_KEY: "no candidates here"},
    }]
    mock_pdf = mocker.patch(
        "src.util.tracking.util.get_pdf_attachments",
        return_value=[b"fake"],
    )
    mock_search = mocker.patch(
        "src.util.tracking.util.search_email_pdfs",
        return_value=["99999"],
    )

    candidates = tracking_util.get_tracking_candidates(
        emails,
        outlook=SimpleNamespace(),
        pattern=r"\d+",
    )

    assert candidates == {"99999"}
    mock_pdf.assert_called_once()
    mock_search.assert_called_once()
