# Product Context: Zapier Triggers API

## Why This Project Exists

Currently, triggers in Zapier are defined within individual integrations, limiting flexibility and scalability. The lack of a centralized, unified mechanism to accept and process events from diverse sources restricts the platform's ability to support real-time, event-driven workflows at enterprise scale.

## Problems It Solves

1. **Fragmented Trigger Implementation**: Eliminates the need for app-specific polling or webhook implementations
2. **Scalability Limitations**: Provides a scalable, asynchronous event processing pipeline that decouples ingestion from workflow execution
3. **Real-Time Automation Gap**: Enables instant, real-time triggering of workflows without polling delays
4. **Developer Friction**: Simplifies integration by providing a single, standardized API endpoint

## How It Should Work

### Event Flow
1. External system sends event via `POST /events` with JSON payload and API key
2. API validates, authenticates, and enqueues event to message queue
3. Returns HTTP 202 Accepted with event_id within 100ms
4. Processing workers consume events from queue
5. Workers match events against customer subscriptions
6. Matching events trigger workflows via webhook callbacks
7. Events are stored durably for retrieval and audit

### Key User Flows

**Developer Integration Flow:**
1. Developer obtains API key from Zapier
2. Developer configures workflow subscription with event selector/filter
3. Developer sends events via `POST /events` endpoint
4. Events automatically route to matching workflows
5. Developer can retrieve events via `GET /inbox` for debugging

**Workflow Subscription Flow:**
1. Customer activates Zap in Zapier
2. System creates subscription with unique webhook URL
3. Subscription includes event selector (e.g., `event_type == "order.created"`)
4. When events match, webhook callback sent to workflow execution engine
5. If Zap deactivated, subscription cleaned up automatically

## User Experience Goals

### For Developers
- **Simplicity**: Single endpoint, clear documentation, minimal setup
- **Reliability**: Predictable behavior, clear error messages, comprehensive logging
- **Performance**: Fast response times, no blocking operations
- **Transparency**: Visibility into event status, delivery attempts, failures

### For Automation Specialists
- **Real-Time Response**: Instant workflow triggering without polling delays
- **Reliability**: Guaranteed delivery with retry logic and dead-letter queue
- **Flexibility**: Flexible event matching and filtering without code changes
- **Observability**: Clear metrics on event ingestion, delivery success, latency

### For Platform Engineers
- **Scalability**: Automatic horizontal scaling to handle traffic spikes
- **Monitoring**: Comprehensive metrics, alerts, and dashboards
- **Maintainability**: Clean architecture, clear separation of concerns
- **Integration**: Seamless integration with existing Zapier infrastructure

## Alignment with Zapier Platform

The Triggers API operates as a foundational event ingestion layer that:
- Complements existing Zapier trigger ecosystem (Polling Triggers, REST Hooks)
- Provides unified, platform-level event ingestion
- Aligns with Zapier's webhook delivery patterns
- Supports batch event delivery using Zapier's array-based webhook triggering
- Maintains consistency with Zapier's API conventions and developer experience

## Value Proposition

**For External Systems:**
- Simple integration via single REST endpoint
- No need to implement polling or webhook infrastructure
- Automatic routing to relevant workflows
- Reliable delivery with retry logic

**For Zapier Platform:**
- Unified event ingestion reduces integration complexity
- Scalable architecture supports enterprise customers
- Real-time capabilities enable new automation use cases
- Foundation for agentic workflows and advanced automation

