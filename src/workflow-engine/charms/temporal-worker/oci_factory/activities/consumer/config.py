import os

try:
    from importlib.resources import as_file, files
except ImportError:
    from importlib_resources import as_file, files


class Config:
    _capath_ctx = None
    _capath = None

    def __init__(self, username=None, password=None):
        if username is None or password is None:
            username = os.environ["ROCKS_EVENTBUS_USERNAME"]
            password = os.environ["ROCKS_EVENTBUS_PASSWORD"]
        self._username = username
        self._password = password

    def __enter__(self):
        self._capath_ctx = as_file(files(__package__).joinpath("ca.crt"))
        self._capath = self._capath_ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._capath_ctx.__exit__(exc_type, exc_value, traceback)

    def get_producer_config(self):
        return {
            "bootstrap.servers": os.getenv(
                "ROCKS_EVENTBUS_KAFKA_ADDRESS", "kafka.staging.cs.canonical.com:9094"
            ),
            "security.protocol": "SASL_SSL",
            "sasl.username": self._username,
            "sasl.password": self._password,
            "sasl.mechanism": "SCRAM-SHA-512",
            "ssl.ca.location": self._capath,
        }

    def get_consumer_config(self, consumer_group):
        def_conf = self.get_producer_config()
        consumer_conf = {
            "group.id": consumer_group,
            "enable.auto.commit": True,
            "auto.offset.reset": "earliest",
        }
        def_conf.update(consumer_conf)
        return def_conf

    def get_registry_config(self):
        return {
            "url": os.getenv(
                "ROCKS_EVENTBUS_KARAPACE_URL",
                "https://karapace.staging.cs.canonical.com",
            ),
            "basic.auth.user.info": f"{self._username}:{self._password}",
        }
