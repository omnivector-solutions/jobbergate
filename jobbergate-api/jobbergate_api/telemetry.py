"""OpenTelemetry instrumentation for Jobbergate API.

This module initializes and configures OpenTelemetry tracing and metrics
for the FastAPI application, working alongside Sentry SDK for dual export.
"""

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

from jobbergate_api.config import settings

_tracer_provider: TracerProvider | None = None
_tracer: trace.Tracer | None = None


def init_telemetry() -> None:
    """Initialize OpenTelemetry tracing provider and FastAPI instrumentation.
    
    Sets up OTLP exporter to send spans to the configured endpoint.
    Uses batch span processor to reduce overhead.
    Instruments FastAPI to automatically capture HTTP spans.
    """
    global _tracer_provider, _tracer

    if not settings.ENABLE_OTLP_EXPORT:
        return

    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTLP_EXPORTER_ENDPOINT,
            timeout=settings.OTLP_EXPORTER_TIMEOUT,
        )

        _tracer_provider = TracerProvider()
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        trace.set_tracer_provider(_tracer_provider)

        _tracer = trace.get_tracer(__name__)
        
        # FastAPI instrumentation will be applied in main.py after app creation
    except Exception as e:
        # Log error but don't fail - telemetry is not critical
        import sys
        print(f"Failed to initialize OpenTelemetry: {e}", file=sys.stderr)


def instrument_fastapi(app) -> None:
    """Instrument FastAPI application with automatic HTTP span creation.
    
    This should be called after FastAPI app is created but before mounting routes.
    """
    if not settings.ENABLE_OTLP_EXPORT:
        return

    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception as e:
        import sys
        print(f"Failed to instrument FastAPI: {e}", file=sys.stderr)


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
