import django_filters
from graphql import GraphQLError
from graphene import relay, String, Field, Int
from graphene.types.datetime import DateTime
from graphene.types.json import JSONString
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django_filters import OrderingFilter
from rolepermissions.verifications import has_permission

from .models import Event

from maguire.utils import get_node_with_permission, schema_get_mutation_data


class EventFilter(django_filters.FilterSet):

    class Meta:
        model = Event
        fields = {
            'source_model': ['exact'],
            'source_id': ['exact'],
            'event_type': ['exact'],
        }

    order_by = OrderingFilter(fields=['created_at'])


class EventNode(DjangoObjectType):
    class Meta:
        model = Event
        filterset_class = EventFilter
        interfaces = (relay.Node, )

    @classmethod
    def get_node(cls, info, id):
        return get_node_with_permission(cls, id, info.context, 'access_event')


class EventMutation(relay.ClientIDMutation):

    class Input:
        id = String()
        source_model = Int()
        source_id = String()
        event_at = DateTime()
        event_type = String()
        event_data = JSONString()

    event = Field(EventNode)

    @classmethod
    def mutate_and_get_payload(cls, input, context, info):
        fk_fields = ["source_model"]
        non_fk_fields = ["source_id", "event_at", "event_type", "event_data"]

        if "id" in input:  # edit existing not support
            raise GraphQLError("Edit mutation not supported by Event model")
        else:  # create new
            # Gather mutation data
            mutation_data = schema_get_mutation_data(
                fk_fields, non_fk_fields, input, context, update=False)
            # Create the model
            event = Event.objects.create(**mutation_data)
        return EventMutation(event=event)


class Query(object):
    event = relay.Node.Field(EventNode)
    events = DjangoFilterConnectionField(EventNode)

    def resolve_events(self, info, **args):
        if info.context is not None:
            if info.context.user.is_authenticated and (
                    has_permission(info.context.user, 'list_all') or
                    has_permission(info.context.user, 'list_events')):
                return EventFilter(args, queryset=Event.objects.all()).qs
            else:
                return Event.objects.none()
        else:  # Not a HTTP request - no permissions testing currently
            return EventFilter(args, queryset=Event.objects.all()).qs


class Mutation(object):
    event_mutate = EventMutation.Field()
