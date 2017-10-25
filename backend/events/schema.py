import django_filters
from graphql import GraphQLError
from graphene import relay, AbstractType, String, Field, Int
from graphene.types.datetime import DateTime
from graphene.types.json import JSONString
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django_filters import OrderingFilter
from rolepermissions.verifications import has_object_permission, has_permission

from .models import Event

from maguire.utils import (schema_get_mutation_data)


# Graphene will automatically map the Event model's fields onto the EventNode.
# This is configured in the EventNode's Meta class (as you can see below)

EVENT_FILTERS = {
    'source_model': ['exact'],
    'source_id': ['exact'],
    'event_type': ['exact'],
}


class EventNode(DjangoObjectType):
    class Meta:
        model = Event
        # Allow for some more advanced filtering here
        filter_fields = EVENT_FILTERS
        interfaces = (relay.Node, )

    @classmethod
    def get_node(cls, id, context, info):
        # HTTP request
        try:
            node = cls._meta.model.objects.get(id=id)
        except cls._meta.model.DoesNotExist:
            return cls._meta.model.objects.none()
        if context is not None:
            if context.user.is_authenticated and (
                    has_object_permission('access_event', context.user, node)):
                return node
            else:
                return cls._meta.model.objects.none()
        else:  # Not a HTTP request - no permissions testing currently
            return node


class EventFilter(django_filters.FilterSet):

    class Meta:
        model = Event
        fields = EVENT_FILTERS

    order_by = OrderingFilter(fields=['created_at'])


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


class Query(AbstractType):
    event = relay.Node.Field(EventNode)
    events = DjangoFilterConnectionField(EventNode,
                                         filterset_class=EventFilter)

    def resolve_events(self, args, context, info):
        # context will reference to the Django request
        if context is not None:
            if context.user.is_authenticated and (
                    has_permission(context.user, 'list_all') or
                    has_permission(context.user, 'list_events')):
                return EventFilter(args, queryset=Event.objects.all()).qs
            else:
                return Event.objects.none()
        else:  # Not a HTTP request - no permissions testing currently
            return EventFilter(args, queryset=Event.objects.all()).qs


class Mutation(AbstractType):
    event_mutate = EventMutation.Field()
