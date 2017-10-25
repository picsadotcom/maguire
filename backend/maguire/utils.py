from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import uuid
import base64
import random

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

import boto3
from botocore.client import Config


from graphene import relay, Int, ObjectType

from events.models import Event


class TotalCountMixin(ObjectType):
    @classmethod
    def get_connection(cls):
        class CountableConnection(relay.Connection):
            total_count = Int()

            class Meta:
                name = '{}Connection'.format(cls._meta.name)
                node = cls

            @staticmethod
            def resolve_total_count(root, args, context, info):
                return root.length

        return CountableConnection


def uuid_from_b64(encoded):
    # UUIDs are based encoded and prefixed with `SomethingNode:`
    if encoded is not None:
        decoded = base64.b64decode(encoded)
        the_uuid = uuid.UUID(str(decoded.split(b":")[1], "utf-8"))
        return the_uuid
    else:
        return None


def int_from_b64(encoded):
    # Int's from GraphQL are based encoded and prefixed with `SomethingNode:`
    if encoded is not None:
        decoded = base64.b64decode(encoded)
        the_int = int(decoded.split(b":")[1])
        return the_int
    else:
        return None


def b64_from_uuid(the_uuid, node):
    # UUIDs are based encoded and prefixed with `SomethingNode:`
    to_encode = "%s:%s" % (node, the_uuid)
    encoded = base64.b64encode(to_encode.encode("utf-8"))
    return encoded


def parse_schema_non_fk_fields(mutation_data, non_fk_fields, input):
    for field in non_fk_fields:
        if field in input:
            field_value = input.get(field)
            mutation_data[field] = field_value
    return mutation_data


def parse_schema_fk_fields(mutation_data, fk_fields, input):
    for field in fk_fields:

        if field == 'updated_by':
            pass  # handled in get_mutation_data

        if field == 'related_model' and 'related_model' in input:
            related_model = ContentType.objects.get(
                id=int_from_b64(input.get('related_model', None)))
            mutation_data["related_model"] = related_model

        if field == 'source_model' and 'source_model' in input:
            source_model = ContentType.objects.get(
                id=int_from_b64(input.get('source_model', None)))
            mutation_data["source_model"] = source_model

        # if field == 'modelname' and 'modelname' in input:
        #     modelname = ModelName.objects.get(
        #         id=uuid_from_b64(input.get('modelname', None)))
        #     mutation_data['modelname'] = modelname

    return mutation_data


def schema_get_mutation_data(fk_fields, non_fk_fields, input, context, update):
    mutation_data = {}
    # . FK fields
    mutation_data = parse_schema_fk_fields(mutation_data, fk_fields, input)
    # . Non FK fields
    mutation_data = parse_schema_non_fk_fields(mutation_data, non_fk_fields, input)  # noqa
    # . Context
    if context is not None:
        if update:
            mutation_data["updated_by"] = context.user
        else:
            mutation_data["created_by"] = context.user
    return mutation_data


def schema_update_model(model_instance, mutation_data, fk_fields):
    event_data = {}
    for field, value in mutation_data.items():
        setattr(model_instance, field, value)
        # update event data dict and update it to make it json serializable
        if field in fk_fields:
            # make fk json serializable
            event_data[field] = str(value.id)
        elif isinstance(value, datetime):
            # make date json serializeable
            event_data[field] = value.isoformat()
        else:
            event_data[field] = value
    model_instance.save()
    return event_data


def schema_define_user(context, username):
    if context is None:
        user, created = User.objects.get_or_create(username=username)
    else:
        user = context.user
    return user


def schema_create_updated_event(source_model, id, event_data, user):
    Event.objects.create(**{
        "source_model": source_model,
        "source_id": id,
        "event_at": timezone.now(),
        "event_type": "model.updated",
        "event_data": event_data,
        "created_by": user
    })


def float_to_decimal(val):
    """
    Function that turns a Float number into a Decimal (rounded to two decimal
    points)
    By nature, this is an approximation, so use with caution
    """
    # 1. multiply by 10^2 for two decimal point accuracy
    val_100 = val * 100
    # 2. round this float value into an integer with 0 decimal digits
    val_rounded = int(round(val_100))  # int() only for python 2 compatibility
    # 3. turn this value into a string
    val_str = str(val_rounded)
    # 4. pad the string with a zeros until it's at least two chars long
    while len(val_str) < 2:
        val_str = "0" + val_str
    # 4. add back the decimal point to this string
    val_str_dec = val_str[:-2] + "." + val_str[-2:]
    # 5. turn the string into a decimal value
    val_dec = Decimal(val_str_dec)

    return val_dec


def load_s3_client():
    client = boto3.client(
        's3',
        config=Config(signature_version='s3v4'),
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )
    return client


def objects_as_json(d):
    for k, v in d.items():
        if isinstance(v, dict):
            d[k] = objects_as_json(v)
        elif isinstance(v, Decimal):
            d[k] = str(v.quantize(Decimal('.01'), rounding=ROUND_DOWN))
        elif isinstance(v, uuid.UUID):
            d[k] = str(v)
    return d


def random_digits(digits):
    lower = 10**(digits-1)
    upper = 10**digits - 1
    return random.randint(lower, upper)


def digits_of(number):
    return [int(digit) for digit in str(number)]


def luhn_checksum(the_number):
    digits = digits_of(the_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for digit in even_digits:
        total += sum(digits_of(2 * digit))
    return total % 10


def calculate_luhn(partial_number):
    check_digit = luhn_checksum(int(partial_number) * 10)
    return check_digit if check_digit == 0 else 10 - check_digit
