from confluent_kafka import Consumer, KafkaException
from temporalio import activity

from oci_factory.activities.consumer.config import Config
from oci_factory.activities.consumer.schema import SchemaClient


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

    return value
