"""Tests for DynamoDB Service module.

These tests use moto to mock DynamoDB, allowing fast, isolated unit tests
without requiring real AWS resources.
"""

import pytest

from services.dynamodb import DynamoDBService


class TestDynamoDBService:
    """Tests for the DynamoDBService class."""

    def test_init_with_table_name(self, mock_dynamodb_table):
        """Test DynamoDBService initialization with explicit table name."""
        service = DynamoDBService(table_name=mock_dynamodb_table)
        assert service.table_name == mock_dynamodb_table

    def test_init_from_env_var(self, mock_dynamodb_table):
        """Test DynamoDBService initialization from DYNAMODB_TABLE env var."""
        service = DynamoDBService()
        assert service.table_name == mock_dynamodb_table

    def test_init_without_table_raises_error(self, aws_credentials):
        """Test that initialization fails without table name or env var."""
        import os

        # Clear the env var
        os.environ.pop("DYNAMODB_TABLE", None)

        with pytest.raises(ValueError, match="Table name must be provided"):
            DynamoDBService()

    def test_put_item(self, mock_dynamodb_table):
        """Test putting an item into DynamoDB."""
        service = DynamoDBService(table_name=mock_dynamodb_table)
        item = {"id": "test-id", "name": "Test Item", "value": 42}

        result = service.put_item(item)

        assert result == item

        # Verify item was actually put
        retrieved = service.get_item({"id": "test-id"})
        assert retrieved == item

    def test_get_item_exists(self, mock_dynamodb_table):
        """Test getting an existing item from DynamoDB."""
        service = DynamoDBService(table_name=mock_dynamodb_table)
        item = {"id": "get-test", "data": "test-data"}

        # Put item first
        service.put_item(item)

        # Get and verify
        retrieved = service.get_item({"id": "get-test"})
        assert retrieved == item

    def test_get_item_not_exists(self, mock_dynamodb_table):
        """Test getting a non-existent item returns None."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        retrieved = service.get_item({"id": "does-not-exist"})
        assert retrieved is None

    def test_delete_item(self, mock_dynamodb_table):
        """Test deleting an item from DynamoDB."""
        service = DynamoDBService(table_name=mock_dynamodb_table)
        item = {"id": "delete-test", "value": "to-delete"}

        # Put item first
        service.put_item(item)
        assert service.get_item({"id": "delete-test"}) == item

        # Delete it
        service.delete_item({"id": "delete-test"})

        # Verify it's gone
        assert service.get_item({"id": "delete-test"}) is None

    def test_update_item(self, mock_dynamodb_table):
        """Test updating an item in DynamoDB."""
        service = DynamoDBService(table_name=mock_dynamodb_table)
        item = {"id": "update-test", "counter": 0, "status": "pending"}

        # Put initial item
        service.put_item(item)

        # Update it
        updated = service.update_item(
            key={"id": "update-test"},
            update_expression="SET #status = :status, #counter = :counter",
            expression_attribute_names={"#status": "status", "#counter": "counter"},
            expression_attribute_values={":status": "completed", ":counter": 1},
        )

        assert updated["status"] == "completed"
        assert updated["counter"] == 1

        # Verify the update persisted
        retrieved = service.get_item({"id": "update-test"})
        assert retrieved["status"] == "completed"
        assert retrieved["counter"] == 1

    def test_scan_empty_table(self, mock_dynamodb_table):
        """Test scanning an empty table."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        items = service.scan()
        assert items == []

    def test_scan_with_items(self, mock_dynamodb_table):
        """Test scanning a table with items."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        # Put some items
        test_items = [
            {"id": "scan-1", "type": "A", "value": 10},
            {"id": "scan-2", "type": "B", "value": 20},
            {"id": "scan-3", "type": "A", "value": 30},
        ]
        for item in test_items:
            service.put_item(item)

        # Scan all items
        items = service.scan()
        assert len(items) == 3

        # Verify all items were returned
        item_ids = {item["id"] for item in items}
        assert item_ids == {"scan-1", "scan-2", "scan-3"}

    def test_scan_with_filter(self, mock_dynamodb_table):
        """Test scanning with a filter expression."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        # Put items with different types
        test_items = [
            {"id": "filter-1", "type": "A", "value": 10},
            {"id": "filter-2", "type": "B", "value": 20},
            {"id": "filter-3", "type": "A", "value": 30},
        ]
        for item in test_items:
            service.put_item(item)

        # Scan with filter
        items = service.scan(
            filter_expression="#type = :type",
            expression_attribute_names={"#type": "type"},
            expression_attribute_values={":type": "A"},
        )

        assert len(items) == 2
        assert all(item["type"] == "A" for item in items)

    def test_scan_with_limit(self, mock_dynamodb_table):
        """Test scanning with a limit."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        # Put multiple items
        for i in range(5):
            service.put_item({"id": f"limit-{i}", "value": i})

        # Scan with limit
        items = service.scan(limit=3)
        assert len(items) <= 3

    def test_query(self, mock_dynamodb_table):
        """Test querying items by partition key."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        # Put test item
        item = {"id": "query-test", "data": "test-data"}
        service.put_item(item)

        # Query by partition key
        items = service.query(
            key_condition_expression="id = :id",
            expression_attribute_values={":id": "query-test"},
        )

        assert len(items) == 1
        assert items[0] == item

    def test_query_with_limit(self, mock_dynamodb_table):
        """Test querying with a limit."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        # Put test item
        item = {"id": "query-limit", "data": "test"}
        service.put_item(item)

        # Query with limit
        items = service.query(
            key_condition_expression="id = :id",
            expression_attribute_values={":id": "query-limit"},
            limit=1,
        )

        assert len(items) == 1

    def test_batch_write(self, mock_dynamodb_table):
        """Test batch writing items."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        items = [{"id": f"batch-{i}", "value": i, "type": "batch"} for i in range(10)]

        service.batch_write(items)

        # Verify all items were written
        for i in range(10):
            retrieved = service.get_item({"id": f"batch-{i}"})
            assert retrieved is not None
            assert retrieved["value"] == i
            assert retrieved["type"] == "batch"

    def test_batch_write_too_many_items(self, mock_dynamodb_table):
        """Test batch write fails with more than 25 items."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        items = [{"id": f"batch-{i}"} for i in range(26)]

        with pytest.raises(ValueError, match="Batch write supports maximum 25 items"):
            service.batch_write(items)

    def test_batch_get(self, mock_dynamodb_table):
        """Test batch getting items."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        # Put items first
        test_items = [
            {"id": "batch-get-1", "value": 1},
            {"id": "batch-get-2", "value": 2},
            {"id": "batch-get-3", "value": 3},
        ]
        for item in test_items:
            service.put_item(item)

        # Batch get
        keys = [{"id": "batch-get-1"}, {"id": "batch-get-2"}, {"id": "batch-get-3"}]
        items = service.batch_get(keys)

        assert len(items) == 3
        item_ids = {item["id"] for item in items}
        assert item_ids == {"batch-get-1", "batch-get-2", "batch-get-3"}

    def test_batch_get_partial_results(self, mock_dynamodb_table):
        """Test batch get with some non-existent items."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        # Put only one item
        service.put_item({"id": "exists", "value": 1})

        # Try to get two items (one exists, one doesn't)
        keys = [{"id": "exists"}, {"id": "does-not-exist"}]
        items = service.batch_get(keys)

        # Should only return the one that exists
        assert len(items) == 1
        assert items[0]["id"] == "exists"

    def test_batch_get_too_many_items(self, mock_dynamodb_table):
        """Test batch get fails with more than 100 items."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        keys = [{"id": f"key-{i}"} for i in range(101)]

        with pytest.raises(ValueError, match="Batch get supports maximum 100 items"):
            service.batch_get(keys)

    def test_item_exists_true(self, mock_dynamodb_table):
        """Test item_exists returns True for existing item."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        item = {"id": "exists-test", "data": "test"}
        service.put_item(item)

        assert service.item_exists({"id": "exists-test"}) is True

    def test_item_exists_false(self, mock_dynamodb_table):
        """Test item_exists returns False for non-existent item."""
        service = DynamoDBService(table_name=mock_dynamodb_table)

        assert service.item_exists({"id": "does-not-exist"}) is False


class TestDynamoDBServiceSingleton:
    """Tests for the DynamoDB service singleton pattern."""

    def test_direct_instantiation_returns_instance(self, mock_dynamodb_table):
        """Test that direct instantiation returns a DynamoDBService instance."""
        service = DynamoDBService()
        assert isinstance(service, DynamoDBService)
        assert service.table_name == mock_dynamodb_table

    def test_direct_instantiation_singleton(self, mock_dynamodb_table):
        """Test that direct instantiation returns the same instance."""
        service1 = DynamoDBService()
        service2 = DynamoDBService()

        # Should be the same instance (singleton)
        assert service1 is service2

    def test_fresh_instance_after_clear(self, mock_dynamodb_table):
        """Test creating a fresh instance after clearing singleton."""
        # Clear the singleton using class method
        DynamoDBService.clear_connections()

        service = DynamoDBService()
        assert isinstance(service, DynamoDBService)

    def test_clear_specific_table_connection(self, mock_dynamodb_table):
        """Test clearing a specific table connection."""
        # Get connection
        service1 = DynamoDBService(mock_dynamodb_table)

        # Clear specific connection
        DynamoDBService.clear_connection(mock_dynamodb_table)

        # Getting again should create new instance
        service2 = DynamoDBService(mock_dynamodb_table)

        # Should be different instances
        assert service1 is not service2

    def test_multiple_table_connections(self, mock_dynamodb_table, dynamodb_client):
        """Test managing connections to multiple tables."""
        # Create a second table
        second_table = "test-table-2"
        dynamodb_client.create_table(
            TableName=second_table,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Get connections to both tables - just instantiate directly!
        service1 = DynamoDBService(mock_dynamodb_table)
        service2 = DynamoDBService(second_table)

        # Should be different instances
        assert service1 is not service2
        assert service1.table_name == mock_dynamodb_table
        assert service2.table_name == second_table

        # Test operations on both
        service1.put_item({"id": "item-1", "table": "first"})
        service2.put_item({"id": "item-2", "table": "second"})

        item1 = service1.get_item({"id": "item-1"})
        item2 = service2.get_item({"id": "item-2"})

        assert item1["table"] == "first"
        assert item2["table"] == "second"

    def test_singleton_behavior(self, mock_dynamodb_table):
        """Test that instantiating with same table returns same instance."""
        service1 = DynamoDBService(mock_dynamodb_table)
        service2 = DynamoDBService(mock_dynamodb_table)

        # Should be the same instance
        assert service1 is service2
