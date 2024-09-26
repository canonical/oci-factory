"""
Type encoding utilities class.
"""

import json
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    """Custom encoder for datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
        # Let the base class default method raise the TypeError
        return super().default(obj)
