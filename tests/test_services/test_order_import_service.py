from types import SimpleNamespace

import pytest

from src.services.order_import_service import OrderImportService


@pytest.fixture
def order_service_dependencies(mocker, tmp_path):
    magento = mocker.Mock()
    magento.get_pending_orders.return_value = ["100000001"]
    magento.get_order_details.return_value = {
        "items": [{
            "sku": "ALY12345A12",
            "qty_ordered": 1,
            "price": 100.0,
            "name": "ALY12345A12",
        }],
        "extension_attributes": {
            "shipping_assignments": [{
                "shipping": {
                    "address": {
                        "firstname": "Test",
                        "lastname": "Customer",
                        "street": ["123 Main"],
                        "city": "Austin",
                        "region_code": "TX",
                        "postcode": "73301",
                    }
                }
            }]
        }
    }
    magento.get_platform.return_value = "amazon"
    magento.isEbayOrder.return_value = False

    fishbowl = mocker.Mock()
    fishbowl.isSO.return_value = False
    fishbowl.isProduct.return_value = True
    fishbowl.getSONum.return_value = "SO-1"
    fishbowl.getPONum.return_value = "PO-1"

    ftp = mocker.Mock()
    outlook = mocker.Mock()
    vendor = SimpleNamespace(
        vendor_name="VendorA",
        address=SimpleNamespace(
            vendor_name="VendorA",
            street="123 Vendor",
            city="Austin",
            state="TX",
            zipcode="73301",
            country="USA",
        ),
        handling_time_config=SimpleNamespace(get=lambda ucode, status: 3),
    )
    vendor_config_dao = mocker.Mock()
    vendor_config_dao.get_all_items.return_value = [vendor]
    processed_order_dao = mocker.Mock()
    inventory = mocker.Mock()
    inventory.build.return_value = None
    inventory.get_cheapest_vendor.return_value = ("VendorA", 50.0, "FINISH")

    config = {
        "Main Settings": {
            "Customers": {
                "amazon": {
                    "Name": "Amazon",
                    "Address": "1 Amazon Way",
                    "City": "Seattle",
                    "State": "WA",
                    "Zipcode": "98101",
                    "Country": "USA",
                }
            }
        }
    }

    return {
        "magento": magento,
        "fishbowl": fishbowl,
        "ftp": ftp,
        "outlook": outlook,
        "vendor_config_dao": vendor_config_dao,
        "processed_order_dao": processed_order_dao,
        "inventory": inventory,
        "config": config,
    }


def create_service(deps):
    return OrderImportService(
        magento=deps["magento"],
        fishbowl=deps["fishbowl"],
        ftp=deps["ftp"],
        outlook=deps["outlook"],
        vendor_config_dao=deps["vendor_config_dao"],
        processed_order_dao=deps["processed_order_dao"],
        inventory=deps["inventory"],
        config=deps["config"],
    )


def test_prepare_and_import_orders(mocker, order_service_dependencies):
    service = create_service(order_service_dependencies)
    mocker.patch.object(service, "_persist_sales_order")

    service.prepare_orders()
    service.import_orders(test=False)

    assert "VendorA" in service.orders_by_vendor
    service._persist_sales_order.assert_called()
    order_service_dependencies["processed_order_dao"].batch_write_items.assert_called()


def test_vendor_and_exception_notifications(order_service_dependencies):
    service = create_service(order_service_dependencies)
    service.orders_by_vendor["VendorA"] = ["order"]
    service.exception_orders = ["Order #1"]

    service.send_vendor_notifications("orders@example.com")
    service.send_exception_notifications("orders@example.com")

    outlook = order_service_dependencies["outlook"]
    assert outlook.sendMail.call_count == 2
