from enum import IntEnum


class SalesOrderItemType(IntEnum):
    SALE = 10
    MISC_SALE = 11
    DROP_SHIP = 12
    CREDIT_RETURN = 20
    MISC_CREDIT = 21
    DISCOUNT_PERCENTAGE = 30
    DISCOUNT_AMOUNT = 31
    SUBTOTAL = 40
    ASSOC_PRICE = 50
    SHIPPING = 60
    TAX = 70
    KIT = 80
    NOTE = 90
    BOM_CONFIGURATION_ITEM = 100
