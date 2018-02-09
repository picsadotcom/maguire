from django.test import TestCase

from debits.models import Debit


class TestDebitModel(TestCase):

    def test_model_creation(self):
        # Setup
        self.assertEqual(Debit.objects.count(), 0)

        # Execute
        Debit.objects.create(
            client="bobby was here",
            downstream_reference=None,
            callback_url=None,
            account_name="Bobby Ninetoes",
            account_number="123412341234",
            branch_code="632005",
            account_type="current",
            status="pending",
            amount="13500.00",
            reference="123456789",
            provider=None,
            provider_reference=None,
            provider_status=None,
            scheduled_at=None,
            loaded_at=None
        )

        # Check
        self.assertEqual(Debit.objects.count(), 1)
