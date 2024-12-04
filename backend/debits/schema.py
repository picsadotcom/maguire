from django.contrib.contenttypes.models import ContentType
import django_filters
from graphene import relay, String, Field
from graphene.types.datetime import DateTime
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django_filters import OrderingFilter

from .models import Debit
from maguire.utils import (
    TotalCountMixin,
    get_node_with_permission,
    schema_create_updated_event,
    schema_define_user,
    schema_get_mutation_data,
    schema_update_model,
    uuid_from_b64,
)


class DebitFilter(django_filters.FilterSet):
    # Make CharField with choices filtering case-insensitive str lookup
    account_type = django_filters.CharFilter(
        field_name='account_type', lookup_expr='iexact')
    status = django_filters.CharFilter(
        field_name='status', lookup_expr='iexact')

    class Meta:
        model = Debit
        fields = {
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

    order_by = OrderingFilter(fields=['created_at', 'scheduled_at', 'loaded_at'])


class DebitNode(DjangoObjectType, TotalCountMixin):

    class Meta:
        model = Debit
        filterset_class = DebitFilter
        interfaces = (relay.Node, )

    @classmethod
    def get_node(cls, info, id):
        return get_node_with_permission(cls, id, info.context)


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
    def mutate_and_get_payload(cls, root, info, **input):
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
            mutation_data = schema_get_mutation_data(fk_fields, non_fk_fields, input, info.context,
                                                     update=True)
            # Update the model
            event_data = schema_update_model(debit, mutation_data, fk_fields)
            # Define the user
            user = schema_define_user(info.context, "debit_schema")
            # Create a model.updated Event
            source_model = ContentType.objects.get(app_label='debits', model='debit')
            schema_create_updated_event(source_model, id, event_data, user)

        else:  # create new
            # Gather mutation data
            mutation_data = schema_get_mutation_data(fk_fields, non_fk_fields, input, info.context,
                                                     update=False)
            # Create the model
            debit = Debit.objects.create(**mutation_data)

        return DebitMutation(debit=debit)


class Query(object):
    debit = relay.Node.Field(DebitNode)
    debits = DjangoFilterConnectionField(DebitNode)

    def resolve_debits(self, info, **args):
        if info.context is not None:
            if info.context.user.is_authenticated:
                return DebitFilter(args, queryset=Debit.objects.all()).qs
            else:
                return Debit.objects.none()
        else:  # Not a HTTP request - no permissions testing currently
            return DebitFilter(args, queryset=Debit.objects.all()).qs


class Mutation(object):
    debit_mutate = DebitMutation.Field()
