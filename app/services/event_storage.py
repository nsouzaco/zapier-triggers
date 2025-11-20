"""Service for storing events in DynamoDB."""

import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from app.config import get_settings
from app.utils.aws import get_dynamodb_resource
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class EventStorageService:
    """Service for managing event storage in DynamoDB."""

    def __init__(self):
        """Initialize event storage service (lazy initialization)."""
        # Don't initialize DynamoDB at import time
        # It will be initialized on first use via the table property
        self._dynamodb = None
        self._table = None
        self._initialized = False

    def _initialize_dynamodb(self, force_refresh: bool = False):
        """Initialize DynamoDB resource and table (lazy)."""
        if not self._initialized or force_refresh:
            try:
                self._dynamodb = get_dynamodb_resource(force_refresh=force_refresh)
                self._table = self._dynamodb.Table(settings.dynamodb_table)
                logger.info(f"DynamoDB table initialized: {settings.dynamodb_table}")
                self._initialized = True
            except Exception as e:
                logger.warning(f"DynamoDB not available: {e}. Event storage disabled.")
                self._dynamodb = None
                self._table = None
                self._initialized = True  # Mark as initialized even if failed

    @property
    def dynamodb(self):
        """Get DynamoDB resource (lazy-initialized)."""
        force_refresh = hasattr(self, '_needs_refresh') and getattr(self, '_needs_refresh', False)
        if force_refresh:
            self._needs_refresh = False  # Reset flag after using it
        self._initialize_dynamodb(force_refresh=force_refresh)
        return self._dynamodb

    @property
    def table(self):
        """Get DynamoDB table (lazy-initialized)."""
        force_refresh = hasattr(self, '_needs_refresh') and getattr(self, '_needs_refresh', False)
        if force_refresh:
            self._needs_refresh = False  # Reset flag after using it
        self._initialize_dynamodb(force_refresh=force_refresh)
        return self._table

    async def store_event(
        self,
        customer_id: str,
        event_id: str,
        payload: dict,
        status: str = "pending",
    ) -> bool:
        """
        Store event in DynamoDB with retry logic for credential issues.

        Args:
            customer_id: Customer identifier
            event_id: Unique event identifier
            payload: Event payload
            status: Event status (pending, delivered, failed)

        Returns:
            True if successfully stored, False otherwise
        """
        from botocore.exceptions import ClientError
        from time import sleep
        
        timestamp = datetime.utcnow().isoformat()
        item = {
            "customer_id": customer_id,
            "event_id": event_id,
            "payload": json.dumps(payload) if isinstance(payload, dict) else payload,
            "status": status,
            "timestamp": timestamp,
            "created_at": timestamp,
            "delivery_attempts": 0,
        }

        # Add TTL if configured (default 90 days)
        ttl_days = 90  # TODO: Make configurable
        ttl_timestamp = int((datetime.utcnow().timestamp() + (ttl_days * 24 * 60 * 60)))
        item["ttl"] = ttl_timestamp

        max_retries = 3
        for attempt in range(max_retries):
            try:
                table = self.table
                if not table:
                    logger.debug("DynamoDB table not available, using local storage")
                    return False

                table.put_item(Item=item)
                logger.info(f"Event stored in DynamoDB: {event_id} for customer {customer_id}")
                return True

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code in ['InvalidClientTokenId', 'UnrecognizedClientException']:
                    if attempt < max_retries - 1:
                        wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Credential error (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {wait_time}s with credential refresh..."
                        )
                        sleep(wait_time)
                        # Clear all cached clients and force credential refresh
                        from app.utils.aws import clear_aws_clients
                        clear_aws_clients()
                        # Mark that we need to force refresh on next access
                        self._needs_refresh = True
                        self._initialized = False
                        continue
                logger.error(f"Error storing event in DynamoDB: {e}")
                return False
            except Exception as e:
                logger.error(f"Error storing event in DynamoDB: {e}")
                return False
        
        return False

    async def get_event(self, customer_id: str, event_id: str) -> Optional[dict]:
        """
        Retrieve event from DynamoDB.

        Args:
            customer_id: Customer identifier
            event_id: Unique event identifier

        Returns:
            Event data if found, None otherwise
        """
        if not self.table:
            return None

        try:
            response = self.table.get_item(
                Key={
                    "customer_id": customer_id,
                    "event_id": event_id,
                }
            )

            if "Item" in response:
                item = response["Item"]
                # Parse JSON payload if stored as string
                if isinstance(item.get("payload"), str):
                    item["payload"] = json.loads(item["payload"])
                return item

            return None

        except Exception as e:
            logger.error(f"Error retrieving event from DynamoDB: {e}")
            return None

    async def query_events(
        self,
        customer_id: str,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Query events for a customer with filters.

        Args:
            customer_id: Customer identifier
            event_type: Optional filter by event type
            status: Optional filter by status
            start_time: Optional start timestamp
            end_time: Optional end timestamp
            limit: Maximum number of events to return

        Returns:
            List of events matching the criteria
        """
        if not self.table:
            return []

        try:
            # Use query since customer_id is the partition key (HASH)
            query_params = {
                "KeyConditionExpression": "customer_id = :customer_id",
                "ExpressionAttributeValues": {":customer_id": customer_id},
                "Limit": limit * 2,  # Query more items to account for filtering
            }

            # Add status filter if specified
            if status:
                query_params["FilterExpression"] = "status = :status"
                query_params["ExpressionAttributeValues"][":status"] = status

            response = self.table.query(**query_params)
            
            # Handle pagination - continue querying if there are more results
            all_items = response.get("Items", [])
            while "LastEvaluatedKey" in response and len(all_items) < limit * 2:
                query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self.table.query(**query_params)
                all_items.extend(response.get("Items", []))

            events = []
            for item in all_items:
                # Parse JSON payload if stored as string
                if isinstance(item.get("payload"), str):
                    item["payload"] = json.loads(item["payload"])

                # Apply client-side filters (event_type, timestamp)
                if event_type:
                    payload = item.get("payload", {})
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    if payload.get("event_type") != event_type:
                        continue

                if start_time:
                    item_timestamp = datetime.fromisoformat(item.get("timestamp", ""))
                    if item_timestamp < start_time:
                        continue

                if end_time:
                    item_timestamp = datetime.fromisoformat(item.get("timestamp", ""))
                    if item_timestamp > end_time:
                        continue

                events.append(item)

            # Sort by timestamp descending (most recent first)
            events.sort(
                key=lambda x: datetime.fromisoformat(x.get("timestamp", x.get("created_at", "1970-01-01T00:00:00"))),
                reverse=True
            )

            return events[:limit]

        except Exception as e:
            logger.error(f"Error querying events from DynamoDB: {e}")
            return []

    async def update_event_status(
        self,
        customer_id: str,
        event_id: str,
        status: str,
        delivery_attempts: Optional[int] = None,
        last_delivery_timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Update event status in DynamoDB.

        Args:
            customer_id: Customer identifier
            event_id: Unique event identifier
            status: New status
            delivery_attempts: Number of delivery attempts
            last_delivery_timestamp: Last delivery attempt timestamp

        Returns:
            True if successfully updated, False otherwise
        """
        if not self.table:
            return False

        try:
            update_expression = "SET #status = :status"
            expression_attribute_names = {"#status": "status"}
            expression_attribute_values = {":status": status}

            if delivery_attempts is not None:
                update_expression += ", delivery_attempts = :delivery_attempts"
                expression_attribute_values[":delivery_attempts"] = delivery_attempts

            if last_delivery_timestamp:
                update_expression += ", last_delivery_timestamp = :last_delivery_timestamp"
                expression_attribute_values[":last_delivery_timestamp"] = last_delivery_timestamp.isoformat()

            self.table.update_item(
                Key={
                    "customer_id": customer_id,
                    "event_id": event_id,
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
            )

            logger.debug(f"Event status updated: {event_id} -> {status}")
            return True

        except Exception as e:
            logger.error(f"Error updating event status in DynamoDB: {e}")
            return False

    async def delete_event(
        self,
        customer_id: str,
        event_id: str,
    ) -> bool:
        """
        Delete an event from DynamoDB.

        Args:
            customer_id: Customer identifier (for security verification)
            event_id: Unique event identifier

        Returns:
            True if successfully deleted, False otherwise
        """
        if not self.table:
            return False

        try:
            # Verify event belongs to customer before deletion
            event = await self.get_event(customer_id, event_id)
            if not event:
                logger.warning(
                    f"Event not found or doesn't belong to customer: {event_id} "
                    f"for customer {customer_id}"
                )
                return False

            # Delete the event
            self.table.delete_item(
                Key={
                    "customer_id": customer_id,
                    "event_id": event_id,
                }
            )

            logger.info(f"Event deleted: {event_id} for customer {customer_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting event from DynamoDB: {e}", exc_info=True)
            return False

    async def query_all_events(
        self,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Query events across all customers (for operator dashboard).
        Uses DynamoDB scan operation.

        Args:
            event_type: Optional filter by event type
            status: Optional filter by status
            start_time: Optional start timestamp
            end_time: Optional end timestamp
            limit: Maximum number of events to return

        Returns:
            List of events matching the criteria
        """
        if not self.table:
            return []

        try:
            # Use scan to get all events (expensive but necessary for operator view)
            scan_params: dict = {
                "Limit": limit * 2,  # Scan more items to account for filtering
            }

            # Add filters
            filter_expressions = []
            expression_attribute_values: dict = {}

            if status:
                filter_expressions.append("status = :status")
                expression_attribute_values[":status"] = status

            if start_time:
                filter_expressions.append("timestamp >= :start_time")
                expression_attribute_values[":start_time"] = start_time.isoformat()

            if end_time:
                filter_expressions.append("timestamp <= :end_time")
                expression_attribute_values[":end_time"] = end_time.isoformat()

            if filter_expressions:
                scan_params["FilterExpression"] = " AND ".join(filter_expressions)
                scan_params["ExpressionAttributeValues"] = expression_attribute_values

            response = self.table.scan(**scan_params)
            
            # Handle pagination
            all_items = response.get("Items", [])
            while "LastEvaluatedKey" in response and len(all_items) < limit * 2:
                scan_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self.table.scan(**scan_params)
                all_items.extend(response.get("Items", []))

            events = []
            for item in all_items:
                # Parse JSON payload if stored as string
                if isinstance(item.get("payload"), str):
                    item["payload"] = json.loads(item["payload"])

                # Apply client-side filters (event_type)
                if event_type:
                    payload = item.get("payload", {})
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    if payload.get("event_type") != event_type:
                        continue

                events.append(item)

            # Sort by timestamp descending (most recent first)
            events.sort(
                key=lambda x: datetime.fromisoformat(x.get("timestamp", x.get("created_at", "1970-01-01T00:00:00"))),
                reverse=True
            )

            return events[:limit]

        except Exception as e:
            logger.error(f"Error scanning events from DynamoDB: {e}")
            return []

    async def count_all_events(self) -> int:
        """
        Count all events across all customers (approximate).
        Uses DynamoDB scan with Select=COUNT.

        Returns:
            Approximate count of all events
        """
        if not self.table:
            return 0

        try:
            # Use scan with Select=COUNT for efficiency
            response = self.table.scan(Select="COUNT")
            count = response.get("Count", 0)
            
            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self.table.scan(
                    Select="COUNT",
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                count += response.get("Count", 0)
            
            return count
        except Exception as e:
            logger.error(f"Error counting events from DynamoDB: {e}")
            return 0


# Global event storage service instance
event_storage = EventStorageService()

