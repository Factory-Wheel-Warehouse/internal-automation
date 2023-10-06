import pprint

from internalprocesses.aws.dynamodb import VendorConfigDAO

pprint.pprint(VendorConfigDAO().get_all_items())
