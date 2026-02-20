---
tags:
  - Scania/ProcessAutomation/ASP/6735
---
# Jobbergate Observability Stack Setup

This document describes the observability (tracing, metrics, error tracking) infrastructure for Jobbergate, built on OpenTelemetry with self-hosted Prometheus and Grafana dashboards.

## Overview

The observability stack provides:

- **Error/Exception Tracking**: Automatic capture of all errors across CLI, API, and Agent components
- **Usage Analytics**: Telemetry data for user interactions, template selections, and variable responses
- **Metrics**: Application performance metrics (latency, throughput, resource usage)
- **Alerting**: Automated alerts on error rates, spikes, and anomalies
- **Backward Compatibility**: Dual export to Sentry.io (optional) and local OpenTelemetry Collector

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Jobbergate Components                        │
├──────────────────────┬──────────────────────┬────────────────────┤
│  jobbergate-cli      │  jobbergate-api      │  jobbergate-agent  │
│  (Sentry + OTLP)     │  (Sentry + OTLP)     │  (Sentry + OTLP)   │
└──────────────────────┴──────────────────────┴────────────────────┘
                              ↓
                    (Dual Export via gRPC)
                              ↓
         ┌─────────────────────────────────────┐
         │  OpenTelemetry Collector (4317)     │
         │  - Receives traces & metrics        │
         │  - Batch processing                 │
         │  - Memory management                │
         └────────────┬────────────────────────┘
                      ├─────────────────────────────┐
                      ↓                             ↓
        ┌──────────────────────┐    ┌──────────────────────────┐
        │  Prometheus (9090)   │    │  Sentry.io (Optional)    │
        │  - Scrapes metrics   │    │  - Error tracking        │
        │  - Time-series DB    │    │  - Performance profiles  │
        └──────────┬───────────┘    └──────────────────────────┘
                   ↓
        ┌──────────────────────┐
        │  Grafana (3000)      │
        │  - Dashboards        │
        │  - Error tracking    │
        │  - Alert rules       │
        │  - Alerting channels │
        └──────────────────────┘
```

## Quick Start

### 1. Start the Observability Stack

```bash
cd jobbergate-composed

# Build and start all services including the observability stack
docker-compose up -d

# Wait for services to be ready (~30 seconds)
sleep 30

# Verify services are running
docker-compose ps
```

Services should be accessible at:

- **Grafana**: <http://localhost:3000> (admin/admin)
- **Prometheus**: <http://localhost:9090>
- **OpenTelemetry Collector**: localhost:4317 (gRPC)

### 2. Configure Grafana

The first time Grafana starts, it may need manual dashboard configuration:

```bash
# Option A: Automatic setup via Python script
python examples/configure_grafana.py http://localhost:3000 admin admin

# Option B: Manual setup
# 1. Log in to Grafana at http://localhost:3000
# 2. Go to Data Sources → Add data source
# 3. Select Prometheus
# 4. Set URL to http://prometheus:9090
# 5. Click "Save & Test"
```

### 3. Monitor Telemetry

Once the stack is running:

1. **Access Grafana Dashboards**:
   - Open <http://localhost:3000/grafana>
   - Dashboards → Browse
   - Select "Jobbergate Usage Analytics" or "Jobbergate Error Tracking"

2. **Check OpenTelemetry Collector Logs**:

   ```bash
   docker-compose logs otel-collector
   ```

3. **Query Prometheus Metrics**:
   - Open <http://localhost:9090/graph>
   - Enter queries like `otelcol_receiver_accepted_spans_total`

## Configuration

### Environment Variables

#### API (jobbergate-api)

```bash
# Enable/disable OpenTelemetry export
ENABLE_OTLP_EXPORT=true

# OTLP exporter endpoint (gRPC)
OTLP_EXPORTER_ENDPOINT=localhost:4317

# Timeout for OTLP export (seconds)
OTLP_EXPORTER_TIMEOUT=10

# Service name for telemetry
OTEL_SERVICE_NAME=jobbergate-api

# Service version
OTEL_SERVICE_VERSION=5.9.0

# Optional: Keep Sentry DSN for dual export (or set empty to disable)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

#### CLI (jobbergate-cli)

Same environment variables as API, just without the prefix.

#### Agent (jobbergate-agent)

Same as API, but with `JOBBERGATE_AGENT_` prefix:

```bash
JOBBERGATE_AGENT_ENABLE_OTLP_EXPORT=true
JOBBERGATE_AGENT_OTLP_EXPORTER_ENDPOINT=localhost:4317
JOBBERGATE_AGENT_OTLP_EXPORTER_TIMEOUT=10
JOBBERGATE_AGENT_OTEL_SERVICE_NAME=jobbergate-agent
```

### Docker-Compose Configuration

In `jobbergate-composed/docker-compose.yml`, the observability stack includes:

- **otel-collector**: Receives and processes telemetry data
- **prometheus**: Stores time-series metrics (15-day retention by default)
- **grafana**: Visualization and alerting dashboard

Update `otel-collector-config.yaml` to customize:

- Batch processing parameters
- Memory limits
- Export destinations

## Dashboards

### 1. Usage Analytics Dashboard

Tracks user interactions and application usage:

**Metrics displayed**:

- Number of spans received per service
- Template selections
- Variable answer distributions
- User action funnel
- Activity trends over time

**Typical queries**:

```prometheus
# Span count by service
sum by (service_name) (rate(otelcol_receiver_accepted_spans_total[5m]))

# Metric points received
rate(otelcol_receiver_accepted_metric_points_total[5m])
```

### 2. Error Tracking Dashboard

Monitors error rates, types, and anomalies:

**Metrics displayed**:

- Error rate (errors per minute)
- Error count by type/exception
- Error trend over 24 hours
- Error spike visualization
- Errors by component

**Alert rules**:

- `High Error Rate`: > 5 errors/min for 5 minutes
- `Error Spike`: > 50% increase in 1 hour
- `Critical Exceptions`: Authentication, database connection errors

## Alerting

### Alert Rules

Configure alert rules in Grafana:

1. Go to **Alerts** → **Alert Rules**
2. Click **New Alert Rule**
3. Set condition based on Prometheus metrics
4. Configure notification channels (Email, Slack, etc.)

### Example Alert Rules

#### High Error Rate

```
Alert if: error_rate > 5 errors/min for 5 minutes
Severity: Critical
Action: Page on-call engineer
```

#### Error Spike

```
Alert if: percent_increase(errors, 1h) > 50% for 10 minutes
Severity: Warning
Action: Send Slack notification
```

#### Component-Specific Errors

```
Alert if: errors_from_component{component="api"} > 10 for 2 minutes
Severity: Warning
Action: Send email to platform team
```

### Setting Up Notification Channels

1. **Email Notifications**:
   - Go to **Alerting** → **Notification Channels**
   - Add new channel, type: Email
   - Configure SMTP settings

2. **Slack Notifications**:
   - Create Slack webhook: <https://api.slack.com/messaging/webhooks>
   - Add Channel, type: Slack
   - Paste webhook URL

3. **PagerDuty Notifications**:
   - Get integration key from PagerDuty
   - Add Channel, type: PagerDuty
   - Paste integration key

## Dual Export: Sentry + Local Stack

The configuration supports **dual export** for a smooth migration path:

```
Errors occur in application
         ↓
  Captured by sentry-sdk
         ↓
    Dual Export
   /           \
  ↓             ↓
Sentry.io   OpenTelemetry
(optional)   Collector
              (Local)
```

### Keeping Sentry.io

To maintain backward compatibility while adding local observability:

```bash
# Keep both DSNs configured
SENTRY_DSN=https://your-key@sentry.io/project  # Stays enabled
ENABLE_OTLP_EXPORT=true                        # Also enable OTLP
```

This sends errors to **both** Sentry.io and your local Prometheus/Grafana stack.

### Migrating Away from Sentry.io

Once you're confident in the local stack:

```bash
# Phase 1 (now): Dual export enabled (above configuration)
# Phase 2 (1-2 weeks): Monitor local stack stability, validate alerts
# Phase 3: Remove Sentry DSN
SENTRY_DSN=                                    # Clear the DSN
ENABLE_OTLP_EXPORT=true                       # Continue using local stack
```

## Observability Best Practices

### 1. Instrument User Interactions in CLI

```python
from jobbergate_cli.telemetry import get_tracer

tracer = get_tracer()

if tracer:
    with tracer.start_as_current_span("template_selection") as span:
        span.set_attribute("template_name", selected_template)
        span.set_attribute("user_id", user_id)
        # ... perform action ...
```

### 2. Customize Metrics Collection

Update `otel-collector-config.yaml` to add processors for your metrics:

```yaml
processors:
  attributes/add:
    actions:
      - key: deployment.environment
        value: local
        action: insert
```

### 3. Monitor Key Error Types

In Grafana, create alert rules for critical errors:

```prometheus
# Alert on authentication failures
increase(spans_with_status{status="authentication_error"}[5m]) > 0

# Alert on database connection errors
increase(spans_with_status{status="database_error"}[5m]) > 5
```

### 4. Regular Dashboard Reviews

- Review daily error trends
- Check error spike patterns
- Analyze usage patterns for feature popularity
- Validate alert rule effectiveness

## Troubleshooting

### No data appearing in Grafana

1. **Check OpenTelemetry Collector logs**:

   ```bash
   docker-compose logs otel-collector
   ```

2. **Verify export is enabled**:

   ```bash
   # Check environment variables
   docker-compose ps
   docker-compose exec jobbergate-api env | grep OTLP
   ```

3. **Check connectivity**:

   ```bash
   # From within a container
   docker-compose exec jobbergate-api nc -zv otel-collector 4317
   ```

### High memory usage in Collector

Adjust memory limits in `otel-collector-config.yaml`:

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 1024    # Increase this value
    spike_limit_mib: 256
```

### Sentry and OTLP both sending data

This is expected! It means dual export is working. If you want only local OTLP:

```bash
SENTRY_DSN=                # Clear/remove this
ENABLE_OTLP_EXPORT=true
```

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OpenTelemetry Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)
- [Prometheus Querying](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Alerting](https://grafana.com/docs/grafana/latest/alerting/)
- [Sentry OpenTelemetry Support](https://docs.sentry.io/product/integrations/opentelemetry/)

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review OpenTelemetry Collector logs: `docker-compose logs otel-collector`
3. Review component logs: `docker-compose logs jobbergate-api`
4. Open an issue on GitHub with error details and logs
