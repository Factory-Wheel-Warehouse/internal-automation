from src.domain.order.address import Address


def test_street_combines_two_lines():
    address = Address(
        name="Warehouse",
        street1="123 Elm St",
        street2="Suite 200",
        city="Somewhere",
        state="TX",
        zipcode="78901",
    )

    assert address.street == "123 Elm St\nSuite 200"


def test_street_omits_second_line():
    address = Address(
        name="Warehouse",
        street1="123 Elm St",
        city="Somewhere",
        state="TX",
        zipcode="78901",
    )
    assert address.street == "123 Elm St"


def test_string_representation():
    address = Address(
        name="Warehouse",
        street1="123 Elm St",
        street2="Suite 200",
        city="Somewhere",
        state="TX",
        zipcode="78901",
    )
    assert str(address) == "Warehouse\n123 Elm St\nSuite 200\nSomewhere TX 78901"
