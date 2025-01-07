import os
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute


class GenerationOutputModel(Model):

    class Meta:
        table_name = os.getenv("TABLE_NAME", "ap-developer")
        region = os.getenv("REGION", "us-east-1")
        read_capacity_units = 5
        write_capacity_units = 5

    pk = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)

    function_code = UnicodeAttribute()
    commentary = UnicodeAttribute(null=True)
    sample_usage_python = UnicodeAttribute(null=True)
    sample_usage_chaos_toolkit = UnicodeAttribute(null=True)
