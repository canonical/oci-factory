import json
from typing import Callable, Dict, cast

try:
    from importlib.resources import as_file, files
except ImportError:
    # importlib.resources.as_file() is in Python >=3.9 and focal has 3.8
    from importlib_resources import as_file, files

import fastavro
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
from confluent_kafka.serialization import MessageField, SerializationContext

_topic_to_schema = {
    "test.rocks.release.oci": "bo.schema.avro.Oci.avsc",
    "test.rocks.team": "bo.schema.avro.Oci.avsc",
}


class SchemaClient:
    def __init__(self, registry_config: Dict[str, str]):
        self._registry = SchemaRegistryClient(registry_config)

    def topic_serializer(self, topic: str) -> Callable[[object], bytes]:
        pkg_path = _topic_to_schema.get(topic)
        if not pkg_path:
            raise KeyError(f"no schema definition for topic {topic}")
        pkg_path = "schemas/" + pkg_path
        with as_file(files(__package__).joinpath(pkg_path)) as f:
            schema = fastavro.schema.load_schema(f, _write_hint=False)
        serialize = AvroSerializer(self._registry, json.dumps(schema))
        ctx = SerializationContext(topic, MessageField.VALUE)
        return lambda value: cast(bytes, serialize(value, ctx))

    def topic_deserializer(self, topic: str) -> Callable[[bytes], object]:
        subject = topic + "-value"
        schema = self._registry.get_latest_version(subject)
        deserialize = AvroDeserializer(self._registry, schema.schema.schema_str)
        ctx = SerializationContext(topic, MessageField.VALUE)
        return lambda value: deserialize(value, ctx)
