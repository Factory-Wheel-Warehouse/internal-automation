import json
import pprint
from io import StringIO

import requests

res = requests.get(
    "https://www.airbnb.com/s/Washington--United-States/homes?tab_id"
    "=home_tab&refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D"
    "=one_week&monthly_start_date=2024-04-01&monthly_length=3"
    "&monthly_end_date=2024-07-01&price_filter_input_type=2&channel=EXPLORE"
    "&query=Washington%2C%20United%20States&place_id=ChIJ"
    "-bDD5__lhVQRuvNfbGh4QpQ&date_picker_type=flexible_dates"
    "&flexible_trip_dates%5B%5D=april&flexible_trip_dates%5B%5D=may&adults=2"
    "&pets=2&source=structured_search_input_header&search_type=user_map_move"
    "&price_filter_num_nights=5&price_max=1200&room_types%5B%5D=Entire"
    "%20home%2Fapt&min_bathrooms=1&l2_property_type_ids%5B%5D=1&amenities%5B"
    "%5D=4&amenities%5B%5D=5&amenities%5B%5D=8&amenities%5B%5D=9&amenities"
    "%5B%5D=30&amenities%5B%5D=33&amenities%5B%5D=34&ne_lat=50"
    ".286097176913316&ne_lng=-117.51777222059224&sw_lat=44.20729241796401"
    "&sw_lng=-124.51857848966614&zoom=6.958127611570586&zoom_level=6"
    ".958127611570586&search_by_map=true").text

# pprint.pprint(json.loads(json_string))
