import asyncio, re
from typing import Any, Dict, Union
from app.common.logger import LOGGER
from app.core.scheduler import Scheduler
from app.services.monitoring_tgtg_service import MonitoringTgtgService
from app.services.telegram_service import TelegramService
from app.common.utils import Utils

MONITORING_EVENT_PATTERN = r"TooGoodToGo_monitoring_invocation_rule_"

def tgtg_monitoring_handler(
    event: Dict[str, Any], 
    context: Any
):
    """Handle monitoring of the TGTG API based on event scheduling rules."""
    LOGGER.info(f"Launching monitoring of TGTG API - event: {event} - context: {context}")

    if _is_monitoring_event(event):
        scheduler = Scheduler()
        monitoring_tgtg_service = MonitoringTgtgService(scheduler=scheduler)
        monitoring_tgtg_service.start_monitoring()
    else:
        LOGGER.info("Monitoring TGTG not launched - wrong scheduling event")

def _is_monitoring_event(
    event: Dict[str, Any]
) -> bool:
    """Check if an event matches the monitoring invocation rule."""
    resources = event.get('resources', [])
    return any(re.search(MONITORING_EVENT_PATTERN, resource) for resource in resources)

def lambda_scheduler(
    event: Dict[str, Any], 
    context: Any
) -> None:
    """Invoke the scheduler to set up the next monitoring event."""
    LOGGER.info("lambda_scheduler - Scheduling next invocation")
    scheduler = Scheduler()
    scheduler.schedule_next_invocation()

def telegram_webhook_handler(
    event: Dict[str, Any], 
    context: Any
) -> Dict[str, Union[int, Dict[str, str]]]:
    """Handle the Telegram webhook in a synchronous Lambda-compatible way."""
    return asyncio.get_event_loop().run_until_complete(run_telegram_webhook(event, context))

async def run_telegram_webhook(
    event: Dict[str, Any], 
    context: Any
) -> Dict[str, Union[int, Dict[str, str]]]:
    """Process the Telegram webhook event asynchronously."""
    LOGGER.info(f"Telegram Webhook triggered - event: {event}")
    try:
        telegram_service = TelegramService()
        await telegram_service.process_webhook(event)
        return Utils.ok_response()
    except Exception as e:
        LOGGER.error(f"Error in Telegram webhook: {str(e)}")
        return Utils.error_response("Oops, something went wrong with Telegram Notifier!")