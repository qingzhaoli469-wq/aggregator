# -*- coding: utf-8 -*-
"""Microsoft Graph mailbox adapter for an existing Outlook.com account.

Required environment:
  OUTLOOK_EMAIL
  OUTLOOK_CLIENT_ID
  OUTLOOK_REFRESH_TOKEN

Optional:
  OUTLOOK_TENANT (defaults to common)

The user must create/authorize the Microsoft identity application themselves
with delegated Mail.Read and offline_access permissions. This module never
creates Microsoft accounts and never automates CAPTCHA or phone verification.
"""
import json
import os
import urllib.parse
import urllib.request

import utils
from logger import logger

from mailtm import Account, Message, TemporaryMail


class OutlookGraphMail(TemporaryMail):
    """Read messages from an existing Outlook.com mailbox using Graph."""

    def __init__(self) -> None:
        super().__init__()
        self.api_address = "https://graph.microsoft.com/v1.0"
        self.email = os.environ.get("OUTLOOK_EMAIL", "").strip()
        self.client_id = os.environ.get("OUTLOOK_CLIENT_ID", "").strip()
        self.refresh_token = os.environ.get("OUTLOOK_REFRESH_TOKEN", "").strip()
        self.tenant = os.environ.get("OUTLOOK_TENANT", "common").strip() or "common"
        self.access_token = ""

    def get_domains_list(self) -> list[str]:
        return ["outlook.com", "hotmail.com"]

    def get_account(self, retry: int = 1) -> Account:
        if not (self.email and self.client_id and self.refresh_token):
            logger.error(
                "[OutlookGraphError] configure OUTLOOK_EMAIL, OUTLOOK_CLIENT_ID and OUTLOOK_REFRESH_TOKEN"
            )
            return None
        if "@" not in self.email:
            logger.error("[OutlookGraphError] OUTLOOK_EMAIL is not a valid email address")
            return None
        return Account(address=self.email)

    def _refresh_access_token(self) -> bool:
        endpoint = (
            f"https://login.microsoftonline.com/{urllib.parse.quote(self.tenant)}/oauth2/v2.0/token"
        )
        payload = urllib.parse.urlencode({
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": "https://graph.microsoft.com/Mail.Read offline_access",
        }).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20, context=utils.CTX) as response:
                data = json.loads(response.read().decode("utf-8"))
            self.access_token = data.get("access_token", "")
            rotated = data.get("refresh_token", "")
            if rotated and rotated != self.refresh_token:
                logger.warning(
                    "[OutlookGraphInfo] Microsoft returned a rotated refresh token; "
                    "update OUTLOOK_REFRESH_TOKEN in your secret store if future refreshes fail"
                )
            return bool(self.access_token)
        except Exception as exc:
            logger.error(f"[OutlookGraphError] cannot refresh Microsoft Graph token: {exc}")
            self.access_token = ""
            return False

    def get_messages(self, account: Account) -> list[Message]:
        if not account or account.address.lower() != self.email.lower():
            return []
        if not self.access_token and not self._refresh_access_token():
            return []

        query = urllib.parse.urlencode({
            "$top": "15",
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,body,bodyPreview,from,toRecipients,receivedDateTime",
        })
        request = urllib.request.Request(
            f"{self.api_address}/me/mailFolders/inbox/messages?{query}",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20, context=utils.CTX) as response:
                payload = json.loads(response.read().decode("utf-8"))
            messages = []
            for item in payload.get("value", []):
                sender = (item.get("from") or {}).get("emailAddress") or {}
                body = item.get("body") or {}
                body_text = body.get("content", "") or item.get("bodyPreview", "")
                messages.append(Message(
                    id=item.get("id", ""),
                    sender={sender.get("address", ""): sender.get("name", "")},
                    to={x.get("emailAddress", {}).get("address", ""):
                        x.get("emailAddress", {}).get("name", "")
                        for x in item.get("toRecipients", [])},
                    subject=item.get("subject", ""),
                    text=body_text,
                    html=body_text if body.get("contentType", "").lower() == "html" else "",
                    intro=item.get("bodyPreview", ""),
                    data=item,
                ))
            return messages
        except Exception as exc:
            logger.error(f"[OutlookGraphError] cannot read inbox: {exc}")
            # An expired access token can be refreshed once on the next poll.
            self.access_token = ""
            return []

    def monitor_account(self, account: Account, timeout: int = 300, sleep: int = 3) -> Message | None:
        """Wait for a message whose Graph ID was not present at startup."""
        import time

        if not account:
            return None
        timeout = min(600, max(0, timeout))
        sleep = min(max(1, sleep), 10)
        initial = self.get_messages(account)
        seen = {item.id for item in initial if item.id}
        deadline = time.time() + timeout
        while time.time() < deadline:
            for item in self.get_messages(account):
                if item.id and item.id not in seen:
                    return item
            time.sleep(sleep)
        return None

    def delete_account(self, account: Account) -> bool:
        # Never delete the user's real Outlook mailbox or its messages.
        return True
