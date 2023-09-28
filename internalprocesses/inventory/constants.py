FINISH_PATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}$"
REPLICA_PATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}N{1}$"
CORE_PATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}$"
ROAD_READY_REPLICA_PATTERN = r"(ALY|STL|FWC)0[0-9]{5}[A-Z]{1}[0-9]{2}N{1}$"
FWW_CORE_PATTERN = r"(ALY|STL|FWC)[0-9]{5}[A-Z]{1}[0-9]{2}\*CORE$"

MINIMUM_MARGIN = 0.18

CORE_MIN_QTY = 1
FINISHED_MIN_QTY = 1
REPLICA_MIN_QTY = 1

ALLOY_MATERIAL_CODE = "ALY"
STEEL_MATERIAL_CODE = "STL"
MATERIAL_CODE_END = 3

ROAD_READY_EXTRA_CHAR_END = 4

PAINT_CODE_START = 9
PAINT_CODE_END = 11
POLISHED_PAINT_CODE_START = 80

FINISH_INVENTORY_KEY = "Finish"
CORE_INVENTORY_KEY = "Core"

INHOUSE_VENDOR_KEY = "Warehouse"

QUANTITY_INDEX = 0
COST_INDEX = 1

SKU_MAP_CONFIG_ATTRIBUTE = "sku_map_config"
COST_MAP_CONFIG_ATTRIBUTE = "cost_map_config"

EVAL_CONDITION_VARIABLE_NAME = "condition"

COST_ROUND_DIGITS = 2
DEFAULT_AVG_COST = 0.0

NO_VENDOR = "No Vendor"

FTP_PRICING_FILE = "/Magento_upload/lkq_based_sku_pricing.csv"
