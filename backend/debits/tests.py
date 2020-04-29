from datetime import timedelta
from freezegun import freeze_time

import responses

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from debits.models import Debit
from maguire.schema import schema
from debits.providers.easydebit.provider import EasyDebitProvider

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


def make_user(username="testuser", password="testpass", email="testuser@example.com",
              role=None):
    """
    Helper function to create a new User
    """
    user = User.objects.create_user(username, email, password)
    return user


class TestDebitModel(TestCase):

    def _url_string(self, string='/graphql', **url_params):
        if url_params:
            string += '?' + urlencode(url_params)
        return string

    def setUp(self):
        super(TestCase, self).setUp()
        self.adm_client = APIClient()
        self.adm_user = make_user(username="testadm", password="testpass",
                                  email="testadm@example.com", role="admin")
        adm_token = Token.objects.create(user=self.adm_user)
        self.adm_client.credentials(HTTP_AUTHORIZATION='Token ' + adm_token.key)

    def test_model_creation(self):
        # Setup
        self.assertEqual(Debit.objects.count(), 0)
        debit_data = {
            "client": "bobby was here",
            "downstream_reference": None,
            "callback_url": None,
            "account_name": "Bobby Ninetoes",
            "account_number": "123412341234",
            "branch_code": "632005",
            "account_type": "current",
            "status": "pending",
            "amount": "1113500.00",
            "reference": "123456789",
            "provider": None,
            "provider_reference": None,
            "provider_status": None,
            "scheduled_at": timezone.now(),
            "loaded_at": None,
            "load_attempts": 0,
            "last_error": None
        }

        # Execute
        Debit.objects.create(**debit_data)

        # Check
        self.assertEqual(Debit.objects.count(), 1)

        # Check combining unique=True and null=True on downstream_reference
        # Execute again
        Debit.objects.create(**debit_data)

        # Check again
        self.assertEqual(Debit.objects.count(), 2)

    @freeze_time("2016-10-30 12:00:01")
    def test_debit_graphql(self):
        # Setup
        debit = Debit.objects.create(
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

        query = '''
            query GetDebit {
                debit(id: "%s") {
                    client
                    downstreamReference
                    callbackUrl
                    accountName
                    accountNumber
                    branchCode
                    accountType
                    status
                    amount
                    reference
                    provider
                    providerReference
                    providerStatus
                    scheduledAt
                    loadedAt
                    loadAttempts
                    lastError
                }
            }
        ''' % debit.node_id
        # Execute
        result = schema.execute(query)
        # Check
        self.assertEqual(result.errors, None)
        rd = result.data['debit']
        self.assertEqual(rd['client'], "bobby was here")
        self.assertEqual(rd['downstreamReference'], None)
        self.assertEqual(rd['callbackUrl'], None)
        self.assertEqual(rd['accountName'], 'Bobby Ninetoes')
        self.assertEqual(rd['accountNumber'], '123412341234')
        self.assertEqual(rd['branchCode'], '632005')
        self.assertEqual(rd['accountType'], 'CURRENT')
        self.assertEqual(rd['status'], 'PENDING')
        self.assertEqual(rd['amount'], 1113500.0)
        self.assertEqual(rd['reference'], '123456789')
        self.assertEqual(rd['provider'], None)
        self.assertEqual(rd['providerReference'], None)
        self.assertEqual(rd['providerStatus'], None)
        self.assertEqual(rd['scheduledAt'], '2016-10-30T12:00:01+00:00')
        self.assertEqual(rd['loadedAt'], None)
        self.assertEqual(rd['loadAttempts'], 0)
        self.assertEqual(rd['lastError'], None)

    @freeze_time("2016-10-30 12:00:01")
    def test_debit_mutation_add_http(self):
        # Setup
        debit_count = Debit.objects.count()

        mutation = '''
            mutation MutateDebit {
                debitMutate(
                    input: {
                        client: "remote submittor",
                        accountName: "Remote",
                        accountNumber: "5432154321",
                        branchCode: "632001",
                        accountType: "current",
                        amount: "100000.10",
                        scheduledAt: "2016-11-30T12:00:01+00:00"
                    }
                ) {
                    debit {
                        id
                        client
                        downstreamReference
                        callbackUrl
                        accountName
                        accountNumber
                        branchCode
                        accountType
                        status
                        amount
                        reference
                        provider
                        providerReference
                        providerStatus
                        scheduledAt
                        loadedAt
                        loadAttempts
                        lastError
                    }
                }
            }
        '''
        # Execute
        result = self.adm_client.post(self._url_string(query=mutation))

        # Check
        # . check for errors
        self.assertEqual(result.status_code, 200)
        # . check object has been created
        self.assertEqual(Debit.objects.count(), debit_count + 1)
        # . check returned data
        rd = result.json()["data"]["debitMutate"]["debit"]
        self.assertEqual(rd['client'], "remote submittor")
        self.assertEqual(rd['downstreamReference'], None)
        self.assertEqual(rd['callbackUrl'], None)
        self.assertEqual(rd['accountName'], 'Remote')
        self.assertEqual(rd['accountNumber'], '5432154321')
        self.assertEqual(rd['branchCode'], '632001')
        self.assertEqual(rd['accountType'], 'CURRENT')
        self.assertEqual(rd['status'], 'PENDING')
        self.assertEqual(rd['amount'], 100000.1)
        self.assertNotEqual(rd['reference'], None)
        self.assertEqual(rd['provider'], None)
        self.assertEqual(rd['providerReference'], None)
        self.assertEqual(rd['providerStatus'], None)
        self.assertEqual(rd['scheduledAt'], '2016-11-30T12:00:01+00:00')
        self.assertEqual(rd['loadedAt'], None)
        self.assertEqual(rd['loadAttempts'], 0)
        self.assertEqual(rd['lastError'], None)


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
