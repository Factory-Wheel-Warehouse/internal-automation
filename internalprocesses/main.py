import pprint

from internalprocesses import FishbowlClient
from internalprocesses.automation import FISHBOWL_CREDENTIALS
from internalprocesses.automation import FTP_CREDENTIALS
from internalprocesses.automation import build_total_inventory
from internalprocesses.automation import get_initial_dataframe
from internalprocesses.automation import populate_dataframe
from internalprocesses.aws.dynamodb import VendorConfigDAO
from internalprocesses.ftpconnection.ftpConnection import FTPConnection
from internalprocesses.inventory import Inventory
from internalprocesses.vendor import VendorConfig

vendor_configs: list[VendorConfig] = VendorConfigDAO().get_all_items()
ftp = FTPConnection(**FTP_CREDENTIALS)
fishbowl = FishbowlClient(**FISHBOWL_CREDENTIALS)
inventory = Inventory(vendor_configs, ftp, fishbowl)
total_inv = build_total_inventory(inventory, ftp)
df = populate_dataframe(total_inv, get_initial_dataframe(vendor_configs),
                        ftp, {v.vendor_name: v for v in vendor_configs})
