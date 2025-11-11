"""AWS Lambda handler for FastAPI application using zip deployment."""

from mangum import Mangum
from app.main import app
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Note: Credential verification is done lazily on first AWS service call
# This avoids blocking Lambda initialization with VPC endpoint calls

# Create Mangum adapter - disable lifespan for Lambda
# Lifespan events don't work well in Lambda's stateless environment
handler = Mangum(app, lifespan="off")

