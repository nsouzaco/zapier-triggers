"""AWS Lambda handler for SQS worker."""

import json
import asyncio
from typing import Any, Dict

from app.workers.event_processor import event_processor
from app.utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing SQS messages.
    
    Args:
        event: SQS event containing messages
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    logger.info(f"Received SQS event with {len(event.get('Records', []))} records")
    
    results = {
        "batchItemFailures": []
    }
    
    # Process each SQS record
    for record in event.get("Records", []):
        try:
            # Process message synchronously
            # Note: Lambda handler must be synchronous, but we can use asyncio.run
            success = asyncio.run(event_processor.process_message(record))
            
            if not success:
                # Add to batch failures for retry
                results["batchItemFailures"].append({
                    "itemIdentifier": record["messageId"]
                })
                logger.warning(f"Failed to process message: {record['messageId']}")
            else:
                logger.info(f"Successfully processed message: {record['messageId']}")
                
        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)
            # Add to batch failures for retry
            results["batchItemFailures"].append({
                "itemIdentifier": record.get("messageId", "unknown")
            })
    
    return results

