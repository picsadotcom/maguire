from datetime import timedelta

import responses

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from debits.models import Debit
from debits.providers.easydebit.provider import EasyDebitProvider


class TestDebits(TestCase):

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
            scheduled_at=timezone.now(),
            loaded_at=None
        )

        # Check
        self.assertEqual(Debit.objects.count(), 1)

    @responses.activate
    def test_load_debits_succesful(self):
        # Setup
        # setup easydebit provider
        provider = EasyDebitProvider()
        provider.config = settings.DEBIT_CONFIG
        provider.setup_provider()

        # setup response
        xml_body = """
            <SRP xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <EL/>
            </SRP>
        """
        responses.add(
            responses.POST,
            'https://www.slowdebit.co.za:8888/Services/PaymentService.svc/PartnerServices/SaveOnceOffPayments',  # noqa
            body=xml_body, status=200, content_type='application/xml'
        )

        debit = Debit.objects.create(
            client="bobby was here",
            downstream_reference=None,
            callback_url=None,
            account_name="Bobby Ninetoes",
            account_number="123412341234",
            branch_code="632005",
            account_type="current",
            status="pending",
            amount="13500.00",
            reference="111222111",
            provider=None,
            provider_reference=None,
            provider_status=None,
            scheduled_at=timezone.now() + timedelta(hours=48),
            loaded_at=None
        )

        # Execute
        result = provider.load_debits(ids=[str(debit.id)])

        # Check
        self.assertEqual(result, "Successfully loaded 1 debits. Failed to load 0 debits.")

        debit.refresh_from_db()
        self.assertEqual(debit.status, "loaded")

    @responses.activate
    def test_load_debits_fail(self):
        # Setup
        # setup easydebit provider
        provider = EasyDebitProvider()
        provider.config = settings.DEBIT_CONFIG
        provider.setup_provider()

        # setup response
        xml_body = """
            <SRP xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <EL>
                    <E>
                        <CI>222333222</CI>
                        <CL>
                            <C>PMT-AD-000003</C>
                        </CL>
                    </E>
                </EL>
            </SRP>
        """
        responses.add(
            responses.POST,
            'https://www.slowdebit.co.za:8888/Services/PaymentService.svc/PartnerServices/SaveOnceOffPayments',  # noqa
            body=xml_body, status=200, content_type='application/xml'
        )

        debit = Debit.objects.create(
            client="bobby was here",
            downstream_reference=None,
            callback_url=None,
            account_name="Bobby Ninetoes",
            account_number="123412341234",
            branch_code="632005",
            account_type="current",
            status="pending",
            amount="13500.00",
            reference="222333222",
            provider=None,
            provider_reference=None,
            provider_status=None,
            scheduled_at=timezone.now() - timedelta(hours=48),
            loaded_at=None
        )

        # Execute
        result = provider.load_debits(ids=[str(debit.id)])

        # Check
        self.assertEqual(result, "Successfully loaded 0 debits. Failed to load 1 debits.")

        debit.refresh_from_db()
        self.assertEqual(debit.status, "failed")

    @responses.activate
    def test_load_debits_success_and_fail(self):
        # Setup
        # setup easydebit provider
        provider = EasyDebitProvider()
        provider.config = settings.DEBIT_CONFIG
        provider.setup_provider()

        # setup response
        xml_body = """
            <SRP xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <EL>
                    <E>
                        <CI>222333222</CI>
                        <CL>
                            <C>PMT-AD-000003</C>
                        </CL>
                    </E>
                </EL>
            </SRP>
        """
        responses.add(
            responses.POST,
            'https://www.slowdebit.co.za:8888/Services/PaymentService.svc/PartnerServices/SaveOnceOffPayments',  # noqa
            body=xml_body, status=200, content_type='application/xml'
        )

        debit1 = Debit.objects.create(
            client="bobby was here",
            downstream_reference=None,
            callback_url=None,
            account_name="Bobby Ninetoes",
            account_number="123412341234",
            branch_code="632005",
            account_type="current",
            status="pending",
            amount="13500.00",
            reference="111222111",
            provider=None,
            provider_reference=None,
            provider_status=None,
            scheduled_at=timezone.now() + timedelta(hours=48),
            loaded_at=None
        )

        debit2 = Debit.objects.create(
            client="bobby was here",
            downstream_reference=None,
            callback_url=None,
            account_name="Bobby Ninetoes",
            account_number="123412341234",
            branch_code="632005",
            account_type="current",
            status="pending",
            amount="13500.00",
            reference="222333222",
            provider=None,
            provider_reference=None,
            provider_status=None,
            scheduled_at=timezone.now() - timedelta(hours=48),
            loaded_at=None
        )

        # Execute
        result = provider.load_debits(ids=[str(debit1.id), str(debit2.id)])

        # Check
        self.assertEqual(result, "Successfully loaded 1 debits. Failed to load 1 debits.")

        debit1.refresh_from_db()
        self.assertEqual(debit1.status, "loaded")

        debit2.refresh_from_db()
        self.assertEqual(debit2.status, "failed")
