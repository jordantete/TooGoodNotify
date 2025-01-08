import pytest
from unittest.mock import patch
from botocore.exceptions import ClientError
from app.core.database_handler import DatabaseHandler
from app.core.exceptions import DatabaseQueryError

class TestDatabaseHandler:
    @pytest.fixture
    def db_handler(self, mock_boto3_resource):
        with patch('boto3.resource', return_value=mock_boto3_resource):
            return DatabaseHandler(table_name="test_table")

    def test_init_success(self, db_handler):
        assert db_handler.table_name == "test_table"
        assert db_handler.region_name == "eu-west-3"
        assert db_handler.table is not None

    def test_get_items_success(self, db_handler, mock_dynamodb_table):
        test_items = [{'id': '1', 'name': 'test'}]
        mock_dynamodb_table.scan.return_value = {'Items': test_items}
        
        result = db_handler.get_items('name', 'test')
        assert result == test_items
        mock_dynamodb_table.scan.assert_called_once()
    
    def test_get_items_failure(self, db_handler, mock_dynamodb_table):
        mock_dynamodb_table.scan.side_effect = ClientError(
            error_response={'Error': {'Code': 'TestException', 'Message': 'Scan failed'}},
            operation_name='Scan'
        )
        with pytest.raises(DatabaseQueryError):
            db_handler.get_items('name', 'test')

    def test_get_items_with_pagination(self, db_handler, mock_dynamodb_table):
        test_items1 = [{'id': '1', 'name': 'test'}]
        test_items2 = [{'id': '2', 'name': 'test'}]
        
        mock_dynamodb_table.scan.side_effect = [
            {'Items': test_items1, 'LastEvaluatedKey': {'id': '1'}},
            {'Items': test_items2}
        ]
        
        result = db_handler.get_items('name', 'test')
        assert result == test_items1 + test_items2
        assert mock_dynamodb_table.scan.call_count == 2

    def test_put_item_success(self, db_handler, mock_dynamodb_table):
        test_item = {'id': '1', 'name': 'test'}
        db_handler.put_item(test_item)
        mock_dynamodb_table.put_item.assert_called_once_with(Item=test_item)

    def test_put_item_failure(self, db_handler, mock_dynamodb_table):
        mock_dynamodb_table.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'TestException', 'Message': 'Test error'}},
            operation_name='PutItem'
        )
        with pytest.raises(DatabaseQueryError):
            db_handler.put_item({'id': '1', 'name': 'test'}) 
    
    def test_delete_item_success(self, db_handler, mock_dynamodb_table):
        test_key = {'id': '1'}
        db_handler.delete_item('id', '1')
        mock_dynamodb_table.delete_item.assert_called_once_with(Key=test_key)

    def test_delete_item_failure(self, db_handler, mock_dynamodb_table):
        mock_dynamodb_table.delete_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'TestException', 'Message': 'Test error'}},
            operation_name='DeleteItem'
        )
        with pytest.raises(DatabaseQueryError):
            db_handler.delete_item('id', '1')