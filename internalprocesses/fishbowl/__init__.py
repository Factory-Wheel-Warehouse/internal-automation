import sys
from .fishbowl_client import FishbowlClient


def quantity_sold_by_sku_report(fishbowl):
    output = []
    query = """SELECT SOITEM.productNum as SKU, SUM(SOITEM.qtyFulfilled) as SoldQTY
FROM SOITEM
WHERE SOITEM.dateScheduledFulfillment >= NOW() - INTERVAL 1 YEAR AND
    SOITEM.qtyFulfilled > 0
GROUP BY SOITEM.productNum
ORDER BY SoldQTY;"""
    response = fishbowl.sendQueryRequest(query)
    try:
        data = response["FbiJson"]["FbiMsgsRs"]["ExecuteQueryRs"]["Rows"][
            "Row"]
    except Exception as e:
        try:
            raise Exception from e
        except:
            raise Exception("Invalid fishbowl response")
    for row in data[1:]:
        stripped_row = [value.strip('"') for value in row.split(",")]
        stripped_row[1] = int(float(stripped_row[1]))
        output.append(stripped_row)
    return output
