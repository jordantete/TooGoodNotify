import os
from typing import Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALIZATIONS_FILE_PATH = os.path.join(BASE_DIR, "localizable.json")
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
SCHEDULE_RULE_NAME_PREFIX = "TooGoodToGo_monitoring_invocation_rule_"

WEEKDAY_MAP: Dict[int, str] = {
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday',
    6: 'Sunday'
}