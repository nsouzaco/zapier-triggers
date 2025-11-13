"""SQLAlchemy models for PostgreSQL database."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Integer, JSON, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Subscription(Base):
    """Subscription model for workflow subscriptions."""

    __tablename__ = "subscriptions"

    workflow_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(String(255), nullable=False, index=True)
    event_selector = Column(JSON, nullable=False)  # JSONPath or event_type filter
    webhook_url = Column(Text, nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, disabled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Subscription(workflow_id={self.workflow_id}, customer_id={self.customer_id}, status={self.status})>"


class Customer(Base):
    """Customer model for API key management."""

    __tablename__ = "customers"

    customer_id = Column(String(255), primary_key=True)
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    status = Column(String(50), default="active", nullable=False)  # active, disabled
    rate_limit_per_second = Column(Integer, default=1000, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Customer(customer_id={self.customer_id}, status={self.status})>"

