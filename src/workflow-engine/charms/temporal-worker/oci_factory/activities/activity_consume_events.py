from confluent_kafka import Consumer, KafkaException
from temporalio import activity

from oci_factory.activities.consumer.config import Config
from oci_factory.activities.consumer.schema import SchemaClient

import logging
import os
import subprocess

# `TWC_LOG_LEVEL` is the mapped value of `log-level` in the charm config
logging.basicConfig(level=os.environ.get("TWC_LOG_LEVEL", "info").upper())


@activity.defn
async def consume(topic: str, consumer_group: str) -> dict:
    """Connects to a Kafka topic and consumes messages

    :param topic: topic name
    :param consumer_group: name of the consumer group
    """
    activity.logger.info(
        f"Consuming messages from topic {topic} "
        f"with consumer group {consumer_group}"
    )

    with Config() as config:
        consumer_config = config.get_consumer_config(consumer_group)
        registry_config = config.get_registry_config()
        activity.logger.debug(
            "Consumer configuration details:\n"
            f" - Kafka server: {consumer_config.get('bootstrap.servers')}\n"
            f" - Karapace server: {registry_config.get('url')}\n"
            f" - Username: {consumer_config.get('sasl.username')}"
        )
        registry = SchemaClient(registry_config)
        deserialize = registry.topic_deserializer(topic)
        consumer = Consumer(consumer_config)
        consumer.subscribe([topic])
        try:
            while True:
                msg = consumer.poll(timeout=1.0)
                print(msg)

                if msg is None:
                    continue
                if msg.error():
                    raise KafkaException(msg.error())
                value = deserialize(msg.value())
                break
        finally:
            consumer.close()

    logging.info("Release: {}".format(value["release"]))

    # TODO: This part of code should be refactored once Renovate is dropped
    # Details see ROCKS-1197
    curr_file_path = os.path.dirname(os.path.realpath(__file__))
    script_full_path = os.path.join(curr_file_path, "find_images_to_update.py")

    proc = subprocess.Popen(
        ["python3", script_full_path, "{}".format(value.get("release"))]
    )
    proc.wait()

    return value
