import pytest, pytz
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.core.scheduler import Scheduler
from app.common.constants import SCHEDULE_RULE_NAME_PREFIX
from freezegun import freeze_time

class TestScheduler:
    @pytest.fixture
    def scheduler(self):
        with patch('boto3.client') as mock_boto3_client:
            scheduler = Scheduler()
            scheduler.lambda_arn = "test_arn"
            scheduler.events_client = MagicMock()
            scheduler.lambda_client = MagicMock()
            return scheduler

    def test_is_in_cooldown_active(self, scheduler):
        future_time = datetime.now(pytz.utc) + timedelta(minutes=15)
        scheduler.lambda_client.get_function_configuration.return_value = {
            'Environment': {
                'Variables': {
                    'COOLDOWN_END_TIME': future_time.isoformat()
                }
            }
        }
        assert scheduler._is_in_cooldown() is True

    def test_is_in_cooldown_expired(self, scheduler):
        past_time = datetime.now(pytz.utc) - timedelta(minutes=15)
        scheduler.lambda_client.get_function_configuration.return_value = {
            'Environment': {
                'Variables': {
                    'COOLDOWN_END_TIME': past_time.isoformat()
                }
            }
        }
        assert scheduler._is_in_cooldown() is False

    def test_convert_datetime_to_cron_expression(self, scheduler):
        dt = datetime(2024, 3, 20, 14, 30, tzinfo=pytz.UTC)
        cron = scheduler._convert_datetime_to_cron_expression(dt)
        assert cron == "cron(30 14 20 3 ? 2024)"

    def test_list_scheduled_rules(self, scheduler):
        mock_rules = [{'Name': 'Rule1'}, {'Name': 'Rule2'}]
        scheduler.events_client.list_rules.return_value = {'Rules': mock_rules}
        rules = scheduler._list_scheduled_rules()
        assert rules == mock_rules
        scheduler.events_client.list_rules.assert_called_with(
            NamePrefix=SCHEDULE_RULE_NAME_PREFIX
        )

    def test_is_future_rule(self, scheduler):
        now = datetime.now(pytz.utc)
        future_time = now + timedelta(hours=1)
        rule_name = f"{SCHEDULE_RULE_NAME_PREFIX}{future_time.strftime('%Y%m%d%H%M')}"
        
        assert scheduler._is_future_rule({'Name': rule_name}, now) is True

    def test_delete_past_rule(self, scheduler):
        rule = {'Name': 'TestRule'}
        scheduler.events_client.list_targets_by_rule.return_value = {
            'Targets': [{'Id': 'Target1'}]
        }

        scheduler._delete_past_rule(rule)

        scheduler.events_client.remove_targets.assert_called_with(
            Rule='TestRule',
            Ids=['Target1']
        )
        scheduler.events_client.delete_rule.assert_called_with(Name='TestRule')

    @pytest.mark.parametrize("current_hour,expected_window", [
        (11, ((10, 12), (10, 20))),  # Morning window
        (15, ((12, 19), (2, 5))),    # Afternoon window
        (20, None),                   # Outside windows
    ])
    def test_get_time_window(self, scheduler, current_hour, expected_window):
        assert scheduler._get_time_window(current_hour) == expected_window

    def test_calculate_next_invocation_time_sunday(self, scheduler):
        sunday = datetime(2024, 3, 24, 12, 0, tzinfo=pytz.UTC)  # A Sunday
        with freeze_time(sunday):
            assert scheduler._calculate_next_invocation_time() is None

    def test_activate_cooldown(self, scheduler):
        current_vars = {'EXISTING_VAR': 'value'}
        scheduler.lambda_client.get_function_configuration.return_value = {
            'Environment': {'Variables': current_vars}
        }

        scheduler.activate_cooldown(cooldown_minutes=30)

        call_args = scheduler.lambda_client.update_function_configuration.call_args[1]
        new_vars = call_args['Environment']['Variables']
        assert 'COOLDOWN_END_TIME' in new_vars
        assert 'EXISTING_VAR' in new_vars

    def test_schedule_next_invocation_with_cooldown(self, scheduler):
        scheduler._is_in_cooldown = MagicMock(return_value=True)
        scheduler.schedule_next_invocation()
        scheduler.events_client.put_rule.assert_not_called()

    def test_schedule_next_invocation_with_existing_future_rule(self, scheduler):
        scheduler._is_in_cooldown = MagicMock(return_value=False)
        scheduler._has_future_invocation = MagicMock(return_value=True)
        
        scheduler.schedule_next_invocation()
        
        scheduler.events_client.put_rule.assert_not_called() 