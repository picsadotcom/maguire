from datetime import timedelta
from freezegun import freeze_time

import responses

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from debits.models import Debit
from debits.providers.easydebit.provider import EasyDebitProvider


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
            amount="1113500.00",
            reference="123456789",
            provider=None,
            provider_reference=None,
            provider_status=None,
            scheduled_at=timezone.now(),
            loaded_at=None,
            load_attempts=0,
            last_error=None
        )

        # Check
        self.assertEqual(Debit.objects.count(), 1)


class TestDebitTasks(TestCase):

    @responses.activate
    def test_t_queue_pending_01(self):
        """Test if there are no pending debits"""

        # Setup
        from .tasks import t_queue_pending

        # Execute
        result = t_queue_pending.run()

        # Check
        self.assertEqual(result, "Queued 0 pending debit(s)")

    @responses.activate
    def test_t_queue_pending_02(self):
        """Test if there are three pending debits - one with too many load_attempts"""

        # Setup
        from .tasks import t_queue_pending

        # create debits
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
            reference="111222111",
            provider=None,
            provider_reference=None,
            provider_status=None,
            scheduled_at=timezone.now() + timedelta(hours=48),
            loaded_at=None,
            load_attempts=0,
            last_error=None
        )

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
            reference="222333222",
            provider=None,
            provider_reference=None,
            provider_status=None,
            scheduled_at=timezone.now() - timedelta(hours=48),
            loaded_at=None,
            load_attempts=1,
            last_error="PMT-AD-0000001"
        )

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
            reference="333444333",
            provider=None,
            provider_reference=None,
            provider_status=None,
            scheduled_at=timezone.now() - timedelta(hours=48),
            loaded_at=None,
            load_attempts=4,
            last_error=None
        )

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

        # Execute
        result = t_queue_pending.run()

        # Check
        self.assertEqual(result, "Queued 2 pending debit(s)")


class TestProviderEasyDebit(TestCase):

    @freeze_time("2018-02-13 12:30:00")
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
            loaded_at=None,
            load_attempts=0,
            last_error=None
        )

        # Execute
        result = provider.load_debits(ids=[str(debit.id)])

        # Check
        self.assertEqual(result, "Successfully loaded 1 debits. Failed to load 0 debits.")

        debit.refresh_from_db()
        self.assertEqual(debit.status, "loaded")
        self.assertEqual(debit.load_attempts, 1)
        self.assertEqual(debit.last_error, None)
        self.assertEqual(debit.scheduled_at, timezone.now() + timedelta(hours=48))

    @freeze_time("2018-02-13 12:30:00")
    @responses.activate
    def test_load_debits_fail_should_retry(self):
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
            loaded_at=None,
            load_attempts=1,
            last_error="PMT-AD-0000001"
        )

        # Execute
        result = provider.load_debits(ids=[str(debit.id)])

        # Check
        self.assertEqual(result, "Successfully loaded 0 debits. Failed to load 1 debits.")

        debit.refresh_from_db()
        self.assertEqual(debit.status, "pending")
        self.assertEqual(debit.load_attempts, 2)
        self.assertEqual(debit.last_error, "PMT-AD-000003")
        self.assertEqual(debit.scheduled_at, timezone.now() + timedelta(hours=48))

    @freeze_time("2018-02-13 12:30:00")
    @responses.activate
    def test_load_debits_fail_should_not_retry(self):
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
                            <C>UNKNOWN-ERROR-CODE-01</C>
                            <C>UNKNOWN-ERROR-CODE-02</C>
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
            loaded_at=None,
            load_attempts=1,
            last_error="PMT-AD-0000001"
        )

        # Execute
        result = provider.load_debits(ids=[str(debit.id)])

        # Check
        self.assertEqual(result, "Successfully loaded 0 debits. Failed to load 1 debits.")

        debit.refresh_from_db()
        self.assertEqual(debit.status, "failed")
        self.assertEqual(debit.load_attempts, 2)
        self.assertEqual(debit.last_error, "UNKNOWN-ERROR-CODE-01, UNKNOWN-ERROR-CODE-02")
        self.assertEqual(debit.scheduled_at, timezone.now() - timedelta(hours=48))

    @freeze_time("2018-02-13 12:30:00")
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
            loaded_at=None,
            load_attempts=0,
            last_error=None
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
            loaded_at=None,
            load_attempts=1,
            last_error="PMT-AD-0000001"
        )

        # Execute
        result = provider.load_debits(ids=[str(debit1.id), str(debit2.id)])

        # Check
        self.assertEqual(result, "Successfully loaded 1 debits. Failed to load 1 debits.")

        debit1.refresh_from_db()
        self.assertEqual(debit1.status, "loaded")
        self.assertEqual(debit1.load_attempts, 1)
        self.assertEqual(debit1.last_error, None)
        self.assertEqual(debit1.scheduled_at, timezone.now() + timedelta(hours=48))

        debit2.refresh_from_db()
        self.assertEqual(debit2.status, "pending")
        self.assertEqual(debit2.load_attempts, 2)
        self.assertEqual(debit2.last_error, "PMT-AD-000003")
        self.assertEqual(debit2.scheduled_at, timezone.now() + timedelta(hours=48))
