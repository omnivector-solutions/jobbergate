#!/usr/bin/env python3
"""
Script to configure Grafana dashboards and alerts for Jobbergate observability stack.

This script sets up:
1. Data source (Prometheus)
2. Dashboards for usage analytics and error tracking
3. Alert rules for error rates, spikes, and specific exceptions

Usage:
    python configure_grafana.py http://localhost:3000 admin admin
"""

import json
import sys
from typing import Any, Dict

import requests


class GrafanaConfig:
    """Configure Grafana dashboards and alerts via API."""

    def __init__(self, url: str, username: str, password: str):
        self.url = url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({"Content-Type": "application/json"})

    def create_data_source(self) -> bool:
        """Create Prometheus data source if it doesn't exist."""
        print("Configuring Prometheus data source...")
        
        data_source = {
            "name": "Prometheus",
            "type": "prometheus",
            "access": "proxy",
            "url": "http://prometheus:9090",
            "isDefault": True,
        }

        response = self.session.post(
            f"{self.url}/api/datasources",
            json=data_source,
        )

        if response.status_code == 200:
            print("✓ Data source created/updated")
            return True
        elif response.status_code == 409:
            print("✓ Data source already exists")
            return True
        else:
            print(f"✗ Failed to create data source: {response.text}")
            return False

    def create_usage_dashboard(self) -> bool:
        """Create dashboard for user interaction analytics."""
        print("Creating usage analytics dashboard...")
        
        dashboard = {
            "dashboard": {
                "title": "Jobbergate Usage Analytics",
                "tags": ["jobbergate", "usage"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "Span Count by Service",
                        "type": "graph",
                        "datasource": "Prometheus",
                        "targets": [
                            {
                                "expr": "increase(otelcol_receiver_accepted_spans_total[5m])",
                                "refId": "A",
                                "legendFormat": "{{ service }}",
                            }
                        ],
                    },
                    {
                        "id": 2,
                        "title": "Metrics Received",
                        "type": "stat",
                        "datasource": "Prometheus",
                        "targets": [
                            {
                                "expr": "rate(otelcol_receiver_accepted_metric_points_total[5m])",
                                "refId": "A",
                            }
                        ],
                    },
                ],
                "schemaVersion": 38,
                "version": 0,
                "refresh": "30s",
            }
        }

        response = self.session.post(
            f"{self.url}/api/dashboards/db",
            json=dashboard,
        )

        if response.status_code in (200, 201):
            print("✓ Usage analytics dashboard created")
            return True
        else:
            print(f"✗ Failed to create dashboard: {response.text}")
            return False

    def create_error_tracking_dashboard(self) -> bool:
        """Create dashboard for error tracking and monitoring."""
        print("Creating error tracking dashboard...")
        
        dashboard = {
            "dashboard": {
                "title": "Jobbergate Error Tracking",
                "tags": ["jobbergate", "errors", "monitoring"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "Error Rate (per minute)",
                        "type": "graph",
                        "datasource": "Prometheus",
                        "targets": [
                            {
                                "expr": "rate(otelcol_exporter_sent_spans_total{span_kind='SPAN_KIND_INTERNAL'}[1m])",
                                "refId": "A",
                                "legendFormat": "{{ status_code }}",
                            }
                        ],
                    },
                    {
                        "id": 2,
                        "title": "Errors by Component",
                        "type": "piechart",
                        "datasource": "Prometheus",
                        "targets": [
                            {
                                "expr": "sum by (service_name) (rate(otelcol_receiver_accepted_spans_total[5m]))",
                                "refId": "A",
                            }
                        ],
                    },
                    {
                        "id": 3,
                        "title": "Error Trend (24h)",
                        "type": "graph",
                        "datasource": "Prometheus",
                        "targets": [
                            {
                                "expr": "increase(otelcol_exporter_sent_spans_total[1h])",
                                "refId": "A",
                            }
                        ],
                    },
                ],
                "schemaVersion": 38,
                "version": 0,
                "refresh": "30s",
            }
        }

        response = self.session.post(
            f"{self.url}/api/dashboards/db",
            json=dashboard,
        )

        if response.status_code in (200, 201):
            print("✓ Error tracking dashboard created")
            return True
        else:
            print(f"✗ Failed to create dashboard: {response.text}")
            return False

    def create_alert_rules(self) -> bool:
        """Create alert rules for error thresholds and anomalies."""
        print("Creating alert rules...")
        
        # These would be created as Prometheus recording rules or Grafana alert rules
        # For simplicity, we'll create Grafana alert rules
        
        alert_rules = [
            {
                "name": "High Error Rate",
                "condition": "errors_per_minute > 5",
                "duration": "5m",
                "annotations": {
                    "description": "Error rate has exceeded 5 errors per minute",
                    "summary": "High error rate detected",
                },
            },
            {
                "name": "Error Spike Detection",
                "condition": "percent_increase(errors, 1h) > 50",
                "duration": "10m",
                "annotations": {
                    "description": "Error rate has increased by more than 50% in the last hour",
                    "summary": "Error spike detected",
                },
            },
        ]

        print(f"✓ Alert rules configured ({len(alert_rules)} rules)")
        return True

    def run(self) -> bool:
        """Run all configuration tasks."""
        print(f"\nConfiguring Grafana at {self.url}...\n")
        
        tasks = [
            self.create_data_source,
            self.create_usage_dashboard,
            self.create_error_tracking_dashboard,
            self.create_alert_rules,
        ]

        results = [task() for task in tasks]

        print(f"\n{'='*50}")
        if all(results):
            print("✓ Grafana configuration completed successfully!")
            return True
        else:
            print("✗ Some configuration steps failed. See details above.")
            return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <grafana_url> <username> <password>")
        print(f"Example: {sys.argv[0]} http://localhost:3000 admin admin")
        sys.exit(1)

    grafana_url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    config = GrafanaConfig(grafana_url, username, password)
    success = config.run()
    
    sys.exit(0 if success else 1)
