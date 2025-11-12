#!/usr/bin/env python3
"""SQS worker script for processing events from queue."""

import asyncio
import json
import signal
import sys
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings
from app.workers.event_processor import event_processor
from app.utils.logging import setup_logging, get_logger

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


class SQSWorker:
    """Worker for consuming events from SQS queue."""

    def __init__(self):
        """Initialize SQS worker."""
        self.sqs_client = None
        self.queue_url = None
        self.running = True
        self._initialize_sqs()

    def _initialize_sqs(self):
        """Initialize SQS client."""
        try:
            self.sqs_client = boto3.client(
                "sqs",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            self.queue_url = settings.sqs_event_queue_url
            logger.info(f"SQS worker initialized for queue: {self.queue_url}")
        except Exception as e:
            logger.error(f"Failed to initialize SQS client: {e}")
            sys.exit(1)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal, stopping worker...")
        self.running = False

    async def process_messages(self):
        """Process messages from SQS queue."""
        if not self.sqs_client or not self.queue_url:
            logger.error("SQS client or queue URL not configured")
            return

        logger.info("Starting SQS worker...")

        while self.running:
            try:
                # Receive messages from queue
                response = self.sqs_client.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=10,  # Process up to 10 messages at a time
                    WaitTimeSeconds=20,  # Long polling
                    VisibilityTimeout=300,  # 5 minutes visibility timeout
                )

                messages = response.get("Messages", [])

                if not messages:
                    continue

                logger.info(f"Received {len(messages)} messages from queue")

                # Process each message
                for message in messages:
                    try:
                        # Process event
                        success = await event_processor.process_message(message)

                        if success:
                            # Delete message from queue on success
                            try:
                                self.sqs_client.delete_message(
                                    QueueUrl=self.queue_url,
                                    ReceiptHandle=message["ReceiptHandle"],
                                )
                                logger.debug(f"Message deleted from queue: {message['MessageId']}")
                            except ClientError as e:
                                logger.error(f"Error deleting message from queue: {e}")
                        else:
                            # On failure, message will become visible again after visibility timeout
                            logger.warning(
                                f"Message processing failed, will retry: {message['MessageId']}"
                            )

                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)
                        # Message will become visible again after visibility timeout

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "AWS.SimpleQueueService.NonExistentQueue":
                    logger.error(f"Queue does not exist: {self.queue_url}")
                    break
                else:
                    logger.error(f"SQS error: {e}")
                    await asyncio.sleep(5)  # Wait before retrying

            except Exception as e:
                logger.error(f"Unexpected error in worker: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

        logger.info("SQS worker stopped")

    async def run(self):
        """Run the worker."""
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            await self.process_messages()
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        finally:
            logger.info("Worker shutdown complete")


async def main():
    """Main entry point."""
    worker = SQSWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

