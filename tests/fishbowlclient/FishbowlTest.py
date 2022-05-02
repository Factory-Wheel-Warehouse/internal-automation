import os
from internalprocesses.fishbowlclient.fishbowl import FBConnection

fbPassword = os.getenv("FISHBOWL-PW")
fishbowl = FBConnection("danny", fbPassword, "factorywheelwarehouse.myfishbowl.com")

poData = ['PO', '27117', '20', 'Coast To Coast', 'Coast To Coast', 'Coast To Coast', 'Coast To Coast\n15733 Collections Center Drive', 'Chicago', 'IL', '60693', 'UNITED STATES', 'Factory Wheel Warehouse', '', '57 Mall Drive\nCommack, NY 11725', 'T: (516)', 'NY', '605-2131', 'UNITED STATES', 'UPS']
itemData = ['Item', '10', 'test', 'test', '1', 'ea', '1000']