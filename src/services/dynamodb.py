"""
DynamoDB Service Module

Provides a clean interface for DynamoDB operations with proper error handling.
"""

import os
from typing import Any, Optional

import boto3  # type: ignore
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError  # type: ignore

logger = Logger(child=True)

# Module-level storage for table connections (singleton pattern)
_table_connections: dict[str, "DynamoDBService"] = {}


class DynamoDBService:
    """Service class for DynamoDB operations.

    Manages connections to DynamoDB tables. Automatically caches connections
    per table name to optimize Lambda cold starts and resource usage.

    Usage:
        # Automatically returns singleton per table
        db = DynamoDBService("users-table")
        same_db = DynamoDBService("users-table")  # Returns same instance
        assert db is same_db

        # Different table = different instance
        orders_db = DynamoDBService("orders-table")
        assert db is not orders_db
    """

    def __new__(cls, table_name: Optional[str] = None):
        """
        Control instance creation to implement singleton pattern per table.

        Returns existing instance if table connection already exists.
        """
        # Resolve table name
        resolved_name = table_name or os.getenv("DYNAMODB_TABLE")
        if not resolved_name:
            raise ValueError("Table name must be provided or DYNAMODB_TABLE env var must be set")

        # Return existing connection if it exists
        if resolved_name in _table_connections:
            return _table_connections[resolved_name]

        # Create new instance and cache it
        instance = super().__new__(cls)
        _table_connections[resolved_name] = instance
        return instance

    def __init__(self, table_name: Optional[str] = None):
        """
        Initialize the DynamoDB service for a specific table.

        Note: Due to singleton pattern, __init__ may be called multiple times
        on the same instance. We guard against re-initialization.

        Args:
            table_name: DynamoDB table name. If not provided, reads from
                       DYNAMODB_TABLE environment variable.
        """
        # Only initialize once (singleton may call __init__ multiple times)
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.table_name = table_name or os.getenv("DYNAMODB_TABLE")
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)
        logger.info(f"DynamoDBService initialized with table: {self.table_name}")

    @classmethod
    def clear_connections(cls) -> None:
        """
        Clear all cached table connections.

        Useful for testing or when you need to force reconnection.

        Example:
            # In test teardown
            DynamoDBService.clear_connections()
        """
        _table_connections.clear()
        logger.info("Cleared all DynamoDB table connections")

    @classmethod
    def clear_connection(cls, table_name: str) -> None:
        """
        Clear a specific table connection.

        Args:
            table_name: Name of the table connection to clear

        Example:
            DynamoDBService.clear_connection("users-table")
        """
        if table_name in _table_connections:
            # Remove the _initialized flag before deleting so it can be recreated fresh
            if hasattr(_table_connections[table_name], "_initialized"):
                delattr(_table_connections[table_name], "_initialized")
            del _table_connections[table_name]
            logger.info(f"Cleared DynamoDB connection for table: {table_name}")

    def put_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Put an item into the DynamoDB table.

        Args:
            item: Dictionary containing the item data

        Returns:
            The item that was put

        Raises:
            ClientError: If put operation fails
        """
        try:
            self.table.put_item(Item=item)
            logger.info(f"Successfully put item into {self.table_name}")
            return item
        except ClientError as e:
            logger.error(f"Failed to put item into DynamoDB: {e}")
            raise

    def get_item(self, key: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Get an item from the DynamoDB table.

        Args:
            key: Dictionary containing the primary key(s)

        Returns:
            The item if found, None otherwise

        Raises:
            ClientError: If get operation fails
        """
        try:
            response = self.table.get_item(Key=key)
            item = response.get("Item")
            if item:
                logger.info(f"Successfully retrieved item from {self.table_name}")
            else:
                logger.info(f"Item not found in {self.table_name}")
            return item
        except ClientError as e:
            logger.error(f"Failed to get item from DynamoDB: {e}")
            raise

    def delete_item(self, key: dict[str, Any]) -> None:
        """
        Delete an item from the DynamoDB table.

        Args:
            key: Dictionary containing the primary key(s)

        Raises:
            ClientError: If delete operation fails
        """
        try:
            self.table.delete_item(Key=key)
            logger.info(f"Successfully deleted item from {self.table_name}")
        except ClientError as e:
            logger.error(f"Failed to delete item from DynamoDB: {e}")
            raise

    def update_item(
        self,
        key: dict[str, Any],
        update_expression: str,
        expression_attribute_values: dict[str, Any],
        expression_attribute_names: Optional[dict[str, str]] = None,
        return_values: str = "ALL_NEW",
    ) -> dict[str, Any]:
        """
        Update an item in the DynamoDB table.

        Args:
            key: Dictionary containing the primary key(s)
            update_expression: Update expression (e.g., "SET #name = :val")
            expression_attribute_values: Values for the update expression
            expression_attribute_names: Optional attribute name mappings
            return_values: What to return after update (default: ALL_NEW)

        Returns:
            The updated item attributes

        Raises:
            ClientError: If update operation fails
        """
        try:
            kwargs: dict[str, Any] = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_attribute_values,
                "ReturnValues": return_values,
            }
            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names

            response = self.table.update_item(**kwargs)
            logger.info(f"Successfully updated item in {self.table_name}")
            return response.get("Attributes", {})
        except ClientError as e:
            logger.error(f"Failed to update item in DynamoDB: {e}")
            raise

    def _build_query_kwargs(
        self,
        key_condition_expression: str,
        expression_attribute_values: dict[str, Any],
        expression_attribute_names: Optional[dict[str, str]],
        index_name: Optional[str],
        limit: Optional[int],
        scan_index_forward: bool,
    ) -> dict[str, Any]:
        """Build kwargs dictionary for query operation."""
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": key_condition_expression,
            "ExpressionAttributeValues": expression_attribute_values,
            "ScanIndexForward": scan_index_forward,
        }
        if expression_attribute_names:
            kwargs["ExpressionAttributeNames"] = expression_attribute_names
        if index_name:
            kwargs["IndexName"] = index_name
        if limit:
            kwargs["Limit"] = limit
        return kwargs

    def query(
        self,
        key_condition_expression: str,
        expression_attribute_values: dict[str, Any],
        expression_attribute_names: Optional[dict[str, str]] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Query items from the DynamoDB table.

        Args:
            key_condition_expression: Key condition expression
            expression_attribute_values: Values for the condition expression
            expression_attribute_names: Optional attribute name mappings
            index_name: Optional index name to query
            limit: Optional maximum number of items to return
            scan_index_forward: Sort order (True=ascending, False=descending)

        Returns:
            List of items matching the query

        Raises:
            ClientError: If query operation fails
        """
        try:
            kwargs = self._build_query_kwargs(
                key_condition_expression,
                expression_attribute_values,
                expression_attribute_names,
                index_name,
                limit,
                scan_index_forward,
            )
            response = self.table.query(**kwargs)
            items = response.get("Items", [])
            logger.info(f"Successfully queried {len(items)} items from {self.table_name}")
            return items
        except ClientError as e:
            logger.error(f"Failed to query items from DynamoDB: {e}")
            raise

    def _build_scan_kwargs(
        self,
        filter_expression: Optional[str],
        expression_attribute_values: Optional[dict[str, Any]],
        expression_attribute_names: Optional[dict[str, str]],
        limit: Optional[int],
    ) -> dict[str, Any]:
        """Build kwargs dictionary for scan operation."""
        kwargs: dict[str, Any] = {}
        if filter_expression:
            kwargs["FilterExpression"] = filter_expression
        if expression_attribute_values:
            kwargs["ExpressionAttributeValues"] = expression_attribute_values
        if expression_attribute_names:
            kwargs["ExpressionAttributeNames"] = expression_attribute_names
        if limit:
            kwargs["Limit"] = limit
        return kwargs

    def scan(
        self,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[dict[str, Any]] = None,
        expression_attribute_names: Optional[dict[str, str]] = None,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Scan items from the DynamoDB table.

        Note: Scan operations can be expensive. Use query when possible.

        Args:
            filter_expression: Optional filter expression
            expression_attribute_values: Values for the filter expression
            expression_attribute_names: Optional attribute name mappings
            limit: Optional maximum number of items to return

        Returns:
            List of items from the scan

        Raises:
            ClientError: If scan operation fails
        """
        try:
            kwargs = self._build_scan_kwargs(
                filter_expression,
                expression_attribute_values,
                expression_attribute_names,
                limit,
            )
            response = self.table.scan(**kwargs)
            items = response.get("Items", [])
            logger.info(f"Successfully scanned {len(items)} items from {self.table_name}")
            return items
        except ClientError as e:
            logger.error(f"Failed to scan items from DynamoDB: {e}")
            raise

    def _validate_batch_size(
        self, items: list[dict[str, Any]], max_size: int, operation: str = "operation"
    ) -> None:
        """Validate batch size."""
        if len(items) > max_size:
            raise ValueError(f"Batch {operation} supports maximum {max_size} items")

    def _perform_batch_write(self, items: list[dict[str, Any]]) -> None:
        """Perform the actual batch write operation."""
        with self.table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)

    def batch_write(self, items: list[dict[str, Any]]) -> None:
        """
        Batch write items to the DynamoDB table.

        Args:
            items: List of items to write (max 25 items)

        Raises:
            ValueError: If more than 25 items provided
            ClientError: If batch write operation fails
        """
        self._validate_batch_size(items, 25, "write")
        try:
            self._perform_batch_write(items)
            logger.info(f"Successfully batch wrote {len(items)} items to {self.table_name}")
        except ClientError as e:
            logger.error(f"Failed to batch write items to DynamoDB: {e}")
            raise

    def batch_get(self, keys: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Batch get items from the DynamoDB table.

        Args:
            keys: List of key dictionaries (max 100 items)

        Returns:
            List of items retrieved

        Raises:
            ValueError: If more than 100 keys provided
            ClientError: If batch get operation fails
        """
        self._validate_batch_size(keys, 100, "get")
        try:
            response = self.dynamodb.batch_get_item(RequestItems={self.table_name: {"Keys": keys}})
            items = response.get("Responses", {}).get(self.table_name, [])
            logger.info(f"Successfully batch retrieved {len(items)} items from {self.table_name}")
            return items
        except ClientError as e:
            logger.error(f"Failed to batch get items from DynamoDB: {e}")
            raise

    def item_exists(self, key: dict[str, Any]) -> bool:
        """
        Check if an item exists in the DynamoDB table.

        Args:
            key: Dictionary containing the primary key(s)

        Returns:
            True if item exists, False otherwise
        """
        try:
            response = self.table.get_item(Key=key)
            return "Item" in response
        except ClientError as e:
            logger.error(f"Failed to check item existence in DynamoDB: {e}")
            raise
