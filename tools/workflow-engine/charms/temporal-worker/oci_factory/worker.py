#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.


"""Temporal client worker."""

import asyncio
import logging
import os

from activities.activity_consume_events import consume
from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig
from temporallib.auth import (
    AuthOptions,
    GoogleAuthOptions,
    KeyPair,
    MacaroonAuthOptions,
)
from temporallib.client import Client, Options
from temporallib.encryption import EncryptionOptions
from temporallib.worker import SentryOptions, Worker, WorkerOptions
from workflows.consume_events_workflow import ConsumeEventsWorkflow

logger = logging.getLogger(__name__)


def _get_auth_header():
    """Get auth options based on provider.

    Returns:
        AuthOptions object.
    """
    if os.getenv("TWC_AUTH_PROVIDER") == "candid":
        return MacaroonAuthOptions(
            keys=KeyPair(
                private=os.getenv("TWC_CANDID_PRIVATE_KEY"),
                public=os.getenv("TWC_CANDID_PUBLIC_KEY"),
            ),
            macaroon_url=os.getenv("TWC_CANDID_URL"),
            username=os.getenv("TWC_CANDID_USERNAME"),
        )

    if os.getenv("TWC_AUTH_PROVIDER") == "google":
        return GoogleAuthOptions(
            type="service_account",
            project_id=os.getenv("TWC_OIDC_PROJECT_ID"),
            private_key_id=os.getenv("TWC_OIDC_PRIVATE_KEY_ID"),
            private_key=os.getenv("TWC_OIDC_PRIVATE_KEY"),
            client_email=os.getenv("TWC_OIDC_CLIENT_EMAIL"),
            client_id=os.getenv("TWC_OIDC_CLIENT_ID"),
            auth_uri=os.getenv("TWC_OIDC_AUTH_URI"),
            token_uri=os.getenv("TWC_OIDC_TOKEN_URI"),
            auth_provider_x509_cert_url=os.getenv("TWC_OIDC_AUTH_CERT_URL"),
            # client_x509_cert_url=os.getenv("TWC_OIDC_CLIENT_CERT_URL"),
        )

    return None


def _init_runtime_with_prometheus(port: int) -> Runtime:
    """Create runtime for use with Prometheus metrics.

    Args:
        port: Port of prometheus.

    Returns:
        Runtime for temporalio with prometheus.
    """
    return Runtime(
        telemetry=TelemetryConfig(
            metrics=PrometheusConfig(bind_address=f"0.0.0.0:{port}")
        )
    )


async def run_worker():
    """Connect Temporal worker to Temporal server."""
    client_config = Options(
        host=os.getenv("TWC_HOST"),
        namespace=os.getenv("TWC_NAMESPACE"),
        queue=os.getenv("TWC_QUEUE"),
    )

    if os.getenv("TWC_TLS_ROOT_CAS", "").strip() != "":
        client_config.tls_root_cas = os.getenv("TWC_TLS_ROOT_CAS")

    if os.getenv("TWC_AUTH_PROVIDER", "").strip() != "":
        client_config.auth = AuthOptions(
            provider=os.getenv("TWC_AUTH_PROVIDER"), config=_get_auth_header()
        )

    if os.getenv("TWC_ENCRYPTION_KEY", "").strip() != "":
        client_config.encryption = EncryptionOptions(
            key=os.getenv("TWC_ENCRYPTION_KEY"), compress=True
        )

    worker_opt = None
    dsn = os.getenv("TWC_SENTRY_DSN", "").strip()
    if dsn != "":
        sentry = SentryOptions(
            dsn=dsn,
            release=os.getenv("TWC_SENTRY_RELEASE", "").strip() or None,
            environment=os.getenv("TWC_SENTRY_ENVIRONMENT", "").strip() or None,
            redact_params=os.getenv("TWC_SENTRY_REDACT_PARAMS", False),
            sample_rate=os.getenv("TWC_SENTRY_SAMPLE_RATE", 1.0),
        )

        worker_opt = WorkerOptions(sentry=sentry)

    client = await Client.connect(client_config)

    worker = Worker(
        client=client,
        task_queue=os.getenv("TWC_QUEUE"),
        workflows=[ConsumeEventsWorkflow],
        activities=[consume],
        worker_opt=worker_opt,
    )

    await worker.run()


if __name__ == "__main__":  # pragma: nocover
    asyncio.run(run_worker())
