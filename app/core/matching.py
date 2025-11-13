"""Event matching logic for subscriptions."""

import json
from typing import Any, Dict, List

from app.database.models import Subscription
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EventMatcher:
    """Service for matching events against subscriptions."""

    @staticmethod
    def match_event_to_subscriptions(
        event_payload: Dict[str, Any],
        subscriptions: List[Subscription],
    ) -> List[Subscription]:
        """
        Match an event against a list of subscriptions.

        Args:
            event_payload: Event payload to match
            subscriptions: List of subscriptions to check

        Returns:
            List of matching subscriptions
        """
        matching_subscriptions = []

        for subscription in subscriptions:
            if EventMatcher._matches_subscription(event_payload, subscription):
                matching_subscriptions.append(subscription)

        return matching_subscriptions

    @staticmethod
    def _matches_subscription(
        event_payload: Dict[str, Any],
        subscription: Subscription,
    ) -> bool:
        """
        Check if an event matches a subscription.

        Args:
            event_payload: Event payload to check
            subscription: Subscription to match against

        Returns:
            True if event matches subscription, False otherwise
        """
        event_selector = subscription.event_selector

        if not event_selector:
            # No selector means match all events
            return True

        # Handle different selector types
        selector_type = event_selector.get("type", "event_type")

        if selector_type == "event_type":
            # Simple event_type matching
            required_event_type = event_selector.get("value")
            event_type = event_payload.get("event_type")

            if required_event_type and event_type:
                return event_type == required_event_type

        elif selector_type == "jsonpath":
            # JSONPath matching (simplified implementation)
            jsonpath_expr = event_selector.get("expression")
            if jsonpath_expr:
                try:
                    return EventMatcher._evaluate_jsonpath(event_payload, jsonpath_expr)
                except Exception as e:
                    logger.warning(f"Error evaluating JSONPath expression: {e}")
                    return False

        elif selector_type == "custom":
            # Custom matching function (for future extensibility)
            custom_function = event_selector.get("function")
            if custom_function:
                try:
                    # In production, this would use a safe evaluation mechanism
                    # For now, we'll support simple field matching
                    return EventMatcher._evaluate_custom(event_payload, custom_function)
                except Exception as e:
                    logger.warning(f"Error evaluating custom function: {e}")
                    return False

        return False

    @staticmethod
    def _evaluate_jsonpath(payload: Dict[str, Any], expression: str) -> bool:
        """
        Evaluate a JSONPath expression against payload.

        Args:
            payload: Event payload
            expression: JSONPath expression (simplified)

        Returns:
            True if expression matches, False otherwise
        """
        # Simplified JSONPath evaluation
        # For production, use a proper JSONPath library like jsonpath-ng

        # Handle simple path expressions like "$.event_type == 'order.created'"
        if "==" in expression:
            parts = expression.split("==")
            if len(parts) == 2:
                path = parts[0].strip().replace("$.", "").replace("$", "")
                value = parts[1].strip().strip("'\"")
                
                # Navigate path
                current = payload
                for key in path.split("."):
                    if isinstance(current, dict):
                        current = current.get(key)
                    else:
                        return False
                
                return str(current) == value

        # Handle simple field existence checks
        if expression.startswith("$."):
            path = expression.replace("$.", "").replace("$", "")
            current = payload
            for key in path.split("."):
                if isinstance(current, dict):
                    current = current.get(key)
                else:
                    return False
            return current is not None

        return False

    @staticmethod
    def _evaluate_custom(payload: Dict[str, Any], function: Dict[str, Any]) -> bool:
        """
        Evaluate a custom matching function.

        Args:
            payload: Event payload
            function: Custom function definition

        Returns:
            True if function matches, False otherwise
        """
        # For now, support simple field matching
        # In production, this would support more complex logic

        field = function.get("field")
        operator = function.get("operator", "equals")
        value = function.get("value")

        if not field:
            return False

        field_value = payload.get(field)

        if operator == "equals":
            return field_value == value
        elif operator == "not_equals":
            return field_value != value
        elif operator == "contains":
            return value in str(field_value) if field_value else False
        elif operator == "exists":
            return field_value is not None

        return False

