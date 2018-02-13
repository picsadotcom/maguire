import hashlib
import requests
from django.utils import timezone
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
from xml.dom import minidom

from debits.providers.base import Provider
from debits.models import Debit


class EasyDebitProvider(Provider):
    """
    EasyDebit provider. Expects self.config dict to contain:
    - authentication
        - service_reference (string - XXXX-XXXX-XXXX-XXXX)
        - username (string - username)
    - bank_ref (string - usually company slug - max 4 chars usable)
    - group_code (string - where debits are placed in hierarchy)
    """

    provider_name = "EasyDebit"
    config = {
        "base_url": "",
        "authentication": {
            "service_reference": None,
            "username": None
        },
        "bank_ref": None,
        "group_code": None
    }

    def setup_provider(self):
        """
        All provider specific setup should happen in here.
        Subclasses should override this method to perform extra setup.
        """

        service_reference = bytes(self.config["authentication"]["service_reference"], "utf-8")
        username = bytes(self.config["authentication"]["username"], "utf-8")
        md5hash = bytes(hashlib.md5(service_reference).hexdigest().upper(), "utf-8")
        self.config["authentication"]["hash"] = hashlib.sha256(username+md5hash).hexdigest()

    def _auth_header(self):
        e_credentials = Element('CR')
        se_username = SubElement(e_credentials, 'U')
        se_username.text = self.config["authentication"]["username"]
        se_password = SubElement(e_credentials, 'P')
        se_password.text = self.config["authentication"]["hash"]
        return e_credentials

    def _format_debit(self, debit):
        """
        Takes a debit model instance and turns it into a XML Payment Item node
        (Client Identification) - VARCHAR(20)
        (Group Code) - VARCHAR (10)
        (NAEDO or Debit Order) - CHAR(1) D or N
        (Service Mode for service type (NAEDO or Debit Order) - VARCHAR(5) 2
        (Amount) - DECIMAL / DOUBLE
        (Action Date) - VARCHAR(8) DDMMYYYY
        (Client Reference – Reference 1) VARCHAR(50)
        (Internal Reference – Reference 2) VARCHAR (40) N/R
        (Bank Reference) - VARCHAR (50)
        (Account Type) - VARCHAR (5) 1 - Current, 2 - Savings
        (Branch Code) - VARCHAR (6)
        (Account Number) - VARCHAR (15)
        (Account Holder) - VARCHAR (100)
        (Identification Type) - VARCHAR (5) N/R
        (Identification Number) - VARCHAR (20) N/R
        """
        e_paymentitem = Element('PI')

        se_client_id = SubElement(e_paymentitem, 'CI')
        se_client_id.text = debit.reference
        se_group_code = SubElement(e_paymentitem, 'GC')
        se_group_code.text = self.config["group_code"]
        se_service_type = SubElement(e_paymentitem, 'ST')
        se_service_type.text = "D"
        se_service_mode = SubElement(e_paymentitem, 'SM')
        se_service_mode.text = "2"
        se_amount = SubElement(e_paymentitem, 'A')
        se_amount.text = str(debit.amount)
        se_action_date = SubElement(e_paymentitem, 'AD')
        se_action_date.text = debit.scheduled_at.strftime("%d%m%Y")
        se_client_reference = SubElement(e_paymentitem, 'CR')
        se_client_reference.text = debit.reference
        se_internal_reference = SubElement(e_paymentitem, 'CR')
        se_internal_reference.text = debit.client
        se_bank_reference = SubElement(e_paymentitem, 'BR')
        se_bank_reference.text = self.config["bank_ref"]
        se_account_type = SubElement(e_paymentitem, 'AT')
        if debit.account_type == "current":
            se_account_type.text = "1"
        elif debit.account_type == "savings":
            se_account_type.text = "2"
        se_branch_code = SubElement(e_paymentitem, 'BC')
        se_branch_code.text = debit.branch_code
        se_account_number = SubElement(e_paymentitem, 'AN')
        se_account_number.text = debit.account_number
        se_account_holder = SubElement(e_paymentitem, 'AH')
        se_account_holder.text = debit.account_name
        # Not required to have values
        SubElement(e_paymentitem, 'IT')
        SubElement(e_paymentitem, 'IN')

        return e_paymentitem

    def load_debits(self, ids):
        """
        This must be overridden to read debits from system and do the right
        thing with them.
        """
        debits = Debit.objects.filter(id__in=ids)
        if debits.count() is not 0:
            e_root = Element('SRQ')
            e_root.append(self._auth_header())
            se_paymentlist = SubElement(e_root, 'PL')
            for debit in debits:
                debit.status = "processing"
                debit.save()
                se_paymentlist.append(self._format_debit(debit))

            # you don't get a proper XML header without minidom, some API's hate that
            reparsed = minidom.parseString(tostring(e_root, encoding='utf-8'))
            payload = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
            url = self.config["base_url"] + "SaveOnceOffPayments"
            response = requests.post(
                url, data=payload, headers={'Content-Type': 'application/xml'})

            # update the debits
            response_root = fromstring(response.text)

            # process any errors
            error_list = response_root.find('EL')
            if(len(error_list)) > 0:
                for error in error_list:
                    # mark the debits as 'failed' if there are errors
                    debit = Debit.objects.get(
                        reference=error.find('CI').text,
                        id__in=debits.values_list('id')
                    )
                    debit.status = "failed"
                    debit.save()
                    # remove the failed debit from the debits queryset
                    debits = debits.exclude(id=debit.id)

            for debit in debits:
                debit.provider = self.provider_name
                debit.loaded_at = timezone.now()
                debit.provider_reference = "TBC"
                debit.status = "loaded"
                debit.save()

            return "Successfully loaded {} debits. Failed to load {} debits.".format(
                debits.count(), len(error_list))
        else:
            return "No debits to submit"

    def check_status(self, id):
        """
        This must be overridden to check status of debit on EasyDebit.
        /Services/PaymentService.svc/PartnerServices/GetPaymentStatus
        """
        raise NotImplementedError()
