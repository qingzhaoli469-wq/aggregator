"""Offline tests for airport registration safety gates.

These tests deliberately avoid network requests and verify that registration
stops before creating a mailbox when the site requires unsupported challenges.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SUBSCRIBE_DIR = Path(__file__).resolve().parents[1] / "subscribe"
sys.path.insert(0, str(SUBSCRIBE_DIR))

from airport import AirPort, RegisterRequire  # noqa: E402
from mailtm import Account  # noqa: E402


class AirportRegistrationGuardTests(unittest.TestCase):
    def setUp(self):
        self.airport = AirPort(name="test", site="https://example.invalid")

    @patch("mailtm.create_instance")
    def test_skip_recaptcha_without_solving_it(self, create_mailbox):
        result = self.airport.get_subscribe(
            retry=1,
            rr=RegisterRequire(verify=True, invite=False, recaptcha=True),
            skip_captcha=True,
        )
        self.assertEqual(result, ("", ""))
        self.assertFalse(self.airport.available)
        create_mailbox.assert_not_called()

    @patch("mailtm.create_instance")
    def test_skip_invite_only_registration_without_invite(self, create_mailbox):
        result = self.airport.get_subscribe(
            retry=1,
            rr=RegisterRequire(verify=True, invite=True, recaptcha=False),
        )
        self.assertEqual(result, ("", ""))
        self.assertFalse(self.airport.available)
        create_mailbox.assert_not_called()

    @patch("mailtm.create_instance")
    def test_skip_gmail_whitelist_without_explicit_gmail_alias_mode(self, create_mailbox):
        result = self.airport.get_subscribe(
            retry=1,
            rr=RegisterRequire(
                verify=True, invite=False, recaptcha=False, whitelist=["gmail.com"]
            ),
            allow_gmail_alias=False,
        )
        self.assertEqual(result, ("", ""))
        self.assertFalse(self.airport.available)
        create_mailbox.assert_not_called()

    @patch("mailtm.create_instance")
    def test_skip_unsupported_non_gmail_whitelist(self, create_mailbox):
        result = self.airport.get_subscribe(
            retry=1,
            rr=RegisterRequire(
                verify=True, invite=False, recaptcha=False, whitelist=["outlook.com"]
            ),
            allow_gmail_alias=True,
        )
        self.assertEqual(result, ("", ""))
        self.assertFalse(self.airport.available)
        create_mailbox.assert_not_called()

    @patch("concurrent.futures.ThreadPoolExecutor")
    @patch("mailtm.create_instance")
    def test_temporary_mailbox_is_cleaned_up_when_verification_request_fails(
        self, create_mailbox, executor_class
    ):
        mailbox = MagicMock()
        account = Account(address="test@example.invalid")
        mailbox.get_account.return_value = account
        create_mailbox.return_value = mailbox

        executor = executor_class.return_value.__enter__.return_value
        future = executor.submit.return_value
        future.result.return_value = None

        with patch.object(self.airport, "sen_email_verify", return_value=False):
            result = self.airport.get_subscribe(
                retry=1,
                rr=RegisterRequire(verify=True, invite=False, recaptcha=False),
            )

        self.assertEqual(result, ("", ""))
        mailbox.delete_account.assert_called_once_with(account=account)
        future.cancel.assert_called_once()


if __name__ == "__main__":
    unittest.main()
