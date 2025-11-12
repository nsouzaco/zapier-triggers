"""AWS Lambda handler for SQS worker using zip deployment."""

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
    logger.info(f"Lambda context: RequestId={context.aws_request_id}, RemainingTime={context.get_remaining_time_in_millis()}ms")
    
    results = {
        "batchItemFailures": []
    }
    
    # Process each SQS record
    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")
        try:
            logger.info(f"Processing message: {message_id}")
            # Debug logging to verify message format
            logger.info(f"Record body type: {type(record.get('body'))}")
            logger.info(f"Record body content: {str(record.get('body', 'N/A'))[:200]}")
            
            # Process message synchronously
            # Note: Lambda handler must be synchronous, but we can use asyncio.run
            success = asyncio.run(event_processor.process_message(record))
            
            if not success:
                # Add to batch failures for retry
                results["batchItemFailures"].append({
                    "itemIdentifier": message_id
                })
                logger.warning(f"Failed to process message: {message_id}")
            else:
                logger.info(f"Successfully processed message: {message_id}")
                
        except Exception as e:
            logger.error(f"Error processing record {message_id}: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Add to batch failures for retry
            results["batchItemFailures"].append({
                "itemIdentifier": message_id
            })
    
    logger.info(f"Processing complete. Batch failures: {len(results['batchItemFailures'])}")
    return results

