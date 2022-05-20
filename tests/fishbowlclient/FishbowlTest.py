import os
from traceback import print_exc

from dotenv import load_dotenv
from internalprocesses import fishbowlclient as fb
from internalprocesses.outlookapi.outlook import sendMail

load_dotenv()

fbPassword = os.getenv("FISHBOWL-PW")
fishbowl = fb.FBConnection("danny", fbPassword, "factorywheelwarehouse.myfishbowl.com")
try:
    print(fb.quantitySoldBySKUReport(fishbowl))
except:
    print_exc()
    fishbowl.close()