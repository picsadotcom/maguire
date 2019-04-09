from django.contrib.contenttypes.models import ContentType
import django_filters
from graphene import relay, AbstractType, String, Field
from graphene.types.datetime import DateTime
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django_filters import OrderingFilter

from .models import Debit
from maguire.utils import (uuid_from_b64, schema_get_mutation_data, schema_update_model,
                           schema_define_user, schema_create_updated_event, TotalCountMixin)


# Graphene will automatically map the Debit model's fields onto the DebitNode.
# This is configured in the DebitNode's Meta class (as you can see below)

DEBIT_FILTERS = {
    'branch_code': ['exact', 'icontains', 'istartswith'],
    'account_number': ['exact', 'icontains', 'istartswith'],
    'account_name': ['exact', 'icontains', 'istartswith'],
    'provider': ['exact'],
    'client': ['exact'],
    'downstream_reference': ['exact', 'icontains', 'istartswith'],
    'reference': ['exact', 'icontains', 'istartswith'],
    'provider_reference': ['exact', 'icontains', 'istartswith'],
    'amount': ['lt', 'gt', 'lte', 'gte', 'exact'],
}


class DebitNode(DjangoObjectType, TotalCountMixin):
    class Meta:
        model = Debit
        # Allow for some more advanced filtering here
        filter_fields = DEBIT_FILTERS
        interfaces = (relay.Node, )

    @classmethod
    def get_node(cls, id, context, info):
        # HTTP request
        try:
            node = cls._meta.model.objects.get(id=id)
        except cls._meta.model.DoesNotExist:
            return cls._meta.model.objects.none()
        if context is not None:
            if context.user.is_authenticated:
                return node
            else:
                return cls._meta.model.objects.none()
        else:  # Not a HTTP request - no permissions testing currently
            return node


class DebitFilter(django_filters.FilterSet):

    class Meta:
        model = Debit
        fields = DEBIT_FILTERS

    order_by = OrderingFilter(fields=['created_at', 'scheduled_at', 'loaded_at'])


class DebitMutation(relay.ClientIDMutation):
    """
    Not all debit fields are mutatable via API. Some only through task etc.
    """

    class Input:
        id = String()
        client = String()
        downstream_reference = String()
        callback_url = String()
        account_name = String()
        account_number = String()
        branch_code = String()
        account_type = String()
        amount = String()
        scheduled_at = DateTime()

    debit = Field(DebitNode)

    @classmethod
    def mutate_and_get_payload(cls, input, context, info):
        fk_fields = ["updated_by"]
        non_fk_fields = ["client", "downstream_reference", "callback_url",
                         "account_name", "account_number", "branch_code",
                         "account_type", "amount", "scheduled_at"]

        if "id" in input:  # lookup existing
            id = uuid_from_b64(input.get("id"))
            try:
                debit = Debit.objects.get(id=id)
            except Debit.DoesNotExist:
                return DebitMutation(debit=None)

            # Gather mutation data
            mutation_data = schema_get_mutation_data(fk_fields, non_fk_fields, input, context,
                                                     update=True)
            # Update the model
            event_data = schema_update_model(debit, mutation_data, fk_fields)
            # Define the user
            user = schema_define_user(context, "debit_schema")
            # Create a model.updated Event
            source_model = ContentType.objects.get(app_label='debits', model='debit')
            schema_create_updated_event(source_model, id, event_data, user)

        else:  # create new
            # Gather mutation data
            mutation_data = schema_get_mutation_data(fk_fields, non_fk_fields, input, context,
                                                     update=False)
            # Create the model
            debit = Debit.objects.create(**mutation_data)

        return DebitMutation(debit=debit)


class Query(AbstractType):
    debit = relay.Node.Field(DebitNode)
    debits = DjangoFilterConnectionField(DebitNode, filterset_class=DebitFilter)

    def resolve_debits(self, args, context, info):
        # context will reference to the Django request
        if context is not None:
            if context.user.is_authenticated:
                return DebitFilter(args, queryset=Debit.objects.all()).qs
            else:
                return Debit.objects.none()
        else:  # Not a HTTP request - no permissions testing currently
            return DebitFilter(args, queryset=Debit.objects.all()).qs


class Mutation(AbstractType):
    debit_mutate = DebitMutation.Field()
