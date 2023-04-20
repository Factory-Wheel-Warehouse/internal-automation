import os
import unittest

from internalprocesses import FishbowlClient


class FishbowlClientTest(unittest.TestCase):
    VALID_CREDENTIALS = {
        "username": "danny",
        "password": os.getenv("FISHBOWL-PW"),
        "host": "factorywheelwarehouse.myfishbowl.com",
        "port": 28192
    }

    INVALID_CREDENTIALS = {
        "username": "USER",
        "password": "PASSWORD",
        "host": "factorywheelwarehouse.myfishbowl.com",
        "port": 28192
    }

    def test_login_logout_with_valid_credentials(self):
        fishbowl = FishbowlClient(**self.VALID_CREDENTIALS)
        self.assertEqual(1000, fishbowl.general_status)
        fishbowl.close()
        self.assertEqual(1164, fishbowl.general_status)

    def test_login_with_invalid_credentials(self):
        self.assertRaises(Exception, FishbowlClient,
                          **self.INVALID_CREDENTIALS)


fishbowl = FishbowlClient(**{
    "username": "danny",
    "password": os.getenv("FISHBOWL-PW"),
    "host": "factorywheelwarehouse.myfishbowl.com",
    "port": 28192
})
products = ["DAS.6-207", "DAS.6-221B", "SUN.80100", "AW.96102", "MAXS.MT-ALUM",
            "AW.96104", "MAXS.MT-RBR", "DAS.TR413", "DAS.95012B", "AW.98100",
            "DAS.6-208", "DAS.1-1400", "DAS.4043-1/8", "AW.96103", "AW.96105",
            "DAS.2-128", "DAS.184432", "DAS.74", "DAS.RP11811400327",
            "DAS.6-228S", "DAS.75N", "DAS.STICKERS", "SECO.57023020",
            "MAXS.MT-TOOL", "DAS.2-158", "DAS.6-231C", "DAS.73", "DAS.00102",
            "AW.98101", "AW.96100", "SECO.18580", "AW.96101", "DAS.221-675-2",
            "DAS.484-10100", "DAS.484-10101", "DAS.75", "AW.98103",
            "DAS.RP6-710014120", "AW.98104", "SECO.18930", "AW.98102",
            "DAS.6-228Z", "DAS.183061", "DAS.5407", "DAS.5411B", "DAS.6-110",
            "DAS.412D"]
product_exists_map = {}
for product in products:
    product_exists_map[product] = fishbowl.isProduct(product)
for key, value in product_exists_map.items():
    print(f"{key}: {value}")

# print(fishbowl.importPurchaseOrder(
#     [
#         'PO, test, 20, Blackburns, null, BlaCKBURNS, BlaCKBURNS, null, null, '
#         'null, null, test, test, null, null, null, null, null, UPS, , test-order-number',
#         'Item, 10, ., ., 1, ea, 10']
# ))
# print(fishbowl._parse_query_request_response(
#     fishbowl.sendQueryRequest(f"""
#         SELECT b.vendorPartNum, b.qtyToFulfill
#         FROM po a
#         LEFT JOIN poitem b
#         ON a.id = b.poId
#         WHERE a.num = "askdfha";
#         """)))
#
# print(fishbowl._parse_query_request_response(fishbowl.sendQueryRequest(f"""
#         SELECT num
#         FROM po
#         WHERE customFields LIKE "%asldkfjasdf%";
#         """)))
# fishbowl.close()
