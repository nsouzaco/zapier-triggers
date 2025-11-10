# Project Brief: Zapier Triggers API

## Project Overview

The Zapier Triggers API is a unified, event-driven system designed to enable real-time automation at scale. It provides a public, reliable, and developer-friendly RESTful interface for any system to send events into Zapier, triggering workflows instantly and reliably.

## Core Mission

Empower users to create reactive, agentic workflows that respond to external events in real time rather than relying on scheduled or manual triggers.

## Key Objectives

1. **Unified Event Ingestion**: Single, standardized REST endpoint for any external system to send events
2. **Real-Time Processing**: Sub-100ms latency for event acknowledgment, < 5 seconds for workflow triggering
3. **Enterprise Scale**: Support for 10,000+ events per second at launch, scaling to 100,000+ events per second
4. **High Reliability**: 99.9% uptime SLA with zero data loss guarantees
5. **Developer Experience**: Simple, intuitive API with comprehensive documentation and testing tools

## Project Scope

### In Scope
- RESTful API for event ingestion (`POST /events`)
- Event retrieval endpoint (`GET /inbox`)
- Dynamic event routing based on payload content and subscriptions
- Durable event storage and persistence
- Webhook delivery to Zapier workflow execution engine
- Rate limiting and idempotency support
- Developer testing UI (Phase 2)
- Basic analytics dashboard (Phase 2)
- Comprehensive analytics and reporting (Phase 3)

### Out of Scope
- Advanced event transformation and field mapping (beyond basic JSONPath filtering)
- Long-term archival strategies beyond configurable TTL
- Event streaming or pub/sub broadcast to multiple external subscribers
- Complex event correlation or aggregation across multiple events
- GUI for subscription management (API-driven in MVP)

## Success Criteria

### Performance Metrics
- Event ingestion latency: < 100ms (P95)
- Event processing latency: < 5 seconds (P95)
- Throughput: 10,000 events/second at launch, 100,000+ events/second scalable
- Query performance: < 1 second for up to 1,000 events

### Reliability Metrics
- Uptime SLA: 99.9% availability
- Data durability: Zero data loss
- Delivery guarantees: At-least-once delivery semantics

### Adoption Metrics
- 10% of existing Zapier integrations adopt within first 6 months
- Positive developer feedback on API usability
- Successful load testing validates all performance targets

## Timeline

- **Phase 1 (MVP)**: 8 weeks - Core API, queue, storage, and worker processing
- **Phase 2 (Post-Launch)**: 4-6 weeks - Testing UI, analytics dashboard, optimizations
- **Phase 3 (Future)**: Advanced analytics, event transformation, multi-region deployment

## Stakeholders

- **Developers**: Software engineers integrating with the API
- **Integration Partners**: Third-party services seeking Zapier integration
- **Automation Specialists**: Business automation consultants
- **Platform Engineers**: Zapier internal teams building agentic workflows

## Project ID

K1oUUDeoZrvJkVZafqHL_1761943818847

