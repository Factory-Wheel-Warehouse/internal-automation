# FTP file paths
MASTER_INVENTORY_PATH = "/Magento_upload/source-file-2.csv"
MASTER_PRICING_PATH = "/Magento_upload/lkq_based_sku_pricing.csv"
COAST_PRICING_PATH = "/lkq/monthly_pricing.xlsx"
LISTABLE_SKUS_PATH = "/Magento_upload/production_sku.csv"
MISSING_SKUS_PATH = "/Magento_upload/missing_skus.csv"

# Margins as multipliers
MINIMUM_MARGIN = 1.40
LOW_COST_MARGIN = MINIMUM_MARGIN + 0.1
HIGH_COST_MARGIN = MINIMUM_MARGIN + 0.05
HIGH_COST_THRESHOLD = 350.0
PRICE_BUFFER = 4.0

# Part number regex patterns
FINISH_PATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}$"
REPLICA_PATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}N{1}$"
CORE_PATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}$"
ROAD_READY_FINISH_PATTERN = r"(ALY|STL|FWC)0[0-9]{5}[A-Z]{1}[0-9]{2}N?$"
FWW_CORE_PATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}\*CORE$"

CORE_MIN_QTY = 1
FINISHED_MIN_QTY = 1
REPLICA_MIN_QTY = 1
MAX_SKU_LISTING_QTY = 4

ALLOY_MATERIAL_CODE = "ALY"
STEEL_MATERIAL_CODE = "STL"
MATERIAL_CODE_END = 3

ROAD_READY_EXTRA_CHAR_END = 4

PAINT_CODE_START = 9
PAINT_CODE_END = 11
POLISHED_PAINT_CODE_START = 80

FINISH_INVENTORY_KEY = "Core"
CORE_INVENTORY_KEY = "Finish"

INHOUSE_VENDOR_KEY = "Warehouse"

QUANTITY_INDEX = 0
COST_INDEX = 1

SKU_MAP_CONFIG_ATTRIBUTE = "sku_map_config"
COST_MAP_CONFIG_ATTRIBUTE = "cost_map_config"

EVAL_CONDITION_VARIABLE_NAME = "condition"

DOLLAR_ROUND_DIGITS = 2
DEFAULT_AVG_COST = 0.0

NO_VENDOR = "No Vendor"

HEADERS = ["sku", "total_qty", "final_magento_qty", "avg_ht",
           "walmart_ht", "list_price"]
VENDOR_SPECIFIC_HEADERS = ["cost", "fin_qty", "core_qty",
                           "combined_qty", "ht"]

EBAY_HANDLING_TIMES = [1, 2, 3, 4, 5, 6, 7, 10, 15]
WALMART_HANDLING_TIMES = [5, 10]
