"""
Common setup for direct debit providers

"""


class Provider:

    provider_name = None
    config = None

    def setup_provider(self):
        """
        All provider specific setup should happen in here.
        Subclasses should override this method to perform extra setup.
        """
        pass

    def teardown_provider(self):
        """
        Clean-up of setup done in setup_provider should happen here.
        """
        pass

    def load_debits(self, ids):
        """
        This must be overridden to read debits from system and do the right
        thing with them.
        """
        raise NotImplementedError()

    def check_status(self, id):
        """
        This must be overridden to check status of debit on provider.
        """
        raise NotImplementedError()
