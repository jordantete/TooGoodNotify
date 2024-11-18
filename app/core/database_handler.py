import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from typing import Any, Dict, List, Optional
from app.common.logger import LOGGER
from app.common.utils import Utils
from app.core.exceptions import DatabaseConnectionError, DatabaseQueryError

class DatabaseHandler:
    def __init__(
        self, 
        table_name: str
    ):
        self.table_name = table_name
        self.region_name = "eu-west-3"
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name) 
        try:
            self.table = self.dynamodb.Table(self.table_name)
    
        except ClientError as e:
            LOGGER.error(f"Failed to connect to DynamoDB table: {self.table_name}")
            raise DatabaseConnectionError("Could not connect to the database") from e
    
    def get_items(
        self, 
        attribute_name: str, 
        attribute_value: Any
    ) -> List[Dict[str, Any]]:
        """Retrieve items by filtering based on an attribute value."""
        items = []
        try:
            response = self.table.scan(FilterExpression=Attr(attribute_name).eq(attribute_value))
            items.extend(response.get('Items', []))

            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression=Attr(attribute_name).eq(attribute_value),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                items.extend(response.get('Items', []))
            LOGGER.info(f"Retrieved {len(items)} items from {self.table_name} where {attribute_name}={attribute_value}")
            return items

        except ClientError as e:
            error_message = f"Error retrieving items from DynamoDB table {self.table_name} where {attribute_name}={attribute_value}"
            LOGGER.error(error_message)
            raise DatabaseQueryError(message=error_message, query=f"{attribute_name}={attribute_value}") from e

    def put_item(
        self, 
        item_data: Dict[str, Any]
    ) -> None:
        """Insert a new item into the DynamoDB table."""
        try:
            self.table.put_item(Item=item_data)
            LOGGER.info(f"Item added to {self.table_name}: {item_data}")

        except ClientError as e:
            error_message = f"Error putting item into DynamoDB table {self.table_name} with data: {item_data}"
            LOGGER.error(error_message)
            raise DatabaseQueryError(message=error_message) from e
        
    def delete_item(
        self, 
        key_name: str, 
        key_value: Any
    ) -> None:
        """Delete an item based on its primary key."""
        try:
            self.table.delete_item(Key={key_name: key_value})
            LOGGER.info(f"Deleted item from {self.table_name} where {key_name}={key_value}")

        except ClientError as e:
            error_message = f"Error deleting item from DynamoDB table {self.table_name} where {key_name}={key_value}"
            LOGGER.error(error_message)
            raise DatabaseQueryError(message=error_message) from e
