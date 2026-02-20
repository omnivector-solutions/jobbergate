"""OpenTelemetry instrumentation for Jobbergate CLI.

This module initializes and configures OpenTelemetry tracing and metrics
to work alongside Sentry SDK for dual export (local OpenTelemetry Collector
and optional Sentry.io for backward compatibility).
"""

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry import trace

from jobbergate_cli.config import settings

_tracer_provider: TracerProvider | None = None
_tracer: trace.Tracer | None = None


def init_telemetry() -> None:
    """Initialize OpenTelemetry tracing provider and exporter.
    
    Sets up OTLP exporter to send spans to the configured endpoint.
    Uses batch span processor to reduce overhead.
    """
    global _tracer_provider, _tracer

    if not settings.enable_otlp_export:
        return

    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otlp_exporter_endpoint,
            timeout=settings.otlp_exporter_timeout,
        )

        _tracer_provider = TracerProvider()
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        trace.set_tracer_provider(_tracer_provider)

        _tracer = trace.get_tracer(__name__)
    except Exception as e:
        # Log error but don't fail - telemetry is not critical
        import sys
        print(f"Failed to initialize OpenTelemetry: {e}", file=sys.stderr)


def get_tracer() -> trace.Tracer | None:
    """Get the global tracer instance.
    
    Returns None if telemetry is not enabled or failed to initialize.
    """
    return _tracer


def shutdown_telemetry() -> None:
    """Shutdown telemetry provider and flush pending spans."""
    global _tracer_provider

    if _tracer_provider is not None:
        _tracer_provider.force_flush(timeout_millis=5000)
        _tracer_provider.shutdown()
