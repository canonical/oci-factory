import asyncio
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

import logging
import os
import sys
from pathlib import Path

path_root = Path(__file__).parents[2]
sys.path.append(str(path_root))
# `TWC_LOG_LEVEL` is the mapped value of `log-level` in the charm config
logging.basicConfig(level=os.environ.get("TWC_LOG_LEVEL", "info").upper())

with workflow.unsafe.imports_passed_through():
    import oci_factory.activities.activity_consume_events as consume_events


@workflow.defn
class ConsumeEventsWorkflow:
    @workflow.run
    async def run(self, kafka_topic: str, consumer_group: str) -> dict:
        """Launches an activity to consume Kafka events from the Event Bus,
        on a given topic.

        :param kafka_topic: topic name
        :param consumer_group: name of the consumer group
        """
        workflow.logger.info(
            f"Running Kafka consumer workflow, from topic {kafka_topic}, "
            f"with the consumer group {consumer_group}"
        )

        try:
            await workflow.execute_activity(
                consume_events.consume,
                args=[kafka_topic, consumer_group],
                start_to_close_timeout=timedelta(days=365),
                heartbeat_timeout=timedelta(seconds=400),
                retry_policy=RetryPolicy(
                    backoff_coefficient=1.2,
                    maximum_interval=timedelta(seconds=30),
                ),
            )
        except ActivityError:
            workflow.logger.error(
                "Consumer activity failed, continuing as new workflow"
            )

        await asyncio.sleep(1)
        workflow.continue_as_new(args=[kafka_topic, consumer_group])
