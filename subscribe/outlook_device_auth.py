#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-time Microsoft device-code authorization for the Outlook Graph adapter.

Set MS_CLIENT_ID before running. Keep the resulting refresh token private.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


TENANT = os.environ.get("OUTLOOK_TENANT", "common").strip() or "common"
CLIENT_ID = os.environ.get("MS_CLIENT_ID", "").strip()
SCOPES = "offline_access https://graph.microsoft.com/Mail.Read"


def post_form(url: str, values: dict[str, str]) -> dict:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(values).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except Exception:
            raise


def main() -> int:
    if not CLIENT_ID:
        print("Set MS_CLIENT_ID to your Microsoft app's Application (client) ID.")
        return 2

    root = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0"
    device = post_form(f"{root}/devicecode", {"client_id": CLIENT_ID, "scope": SCOPES})
    if "device_code" not in device:
        print("Microsoft device authorization could not start:")
        print(json.dumps(device, indent=2))
        return 1

    print(device.get("message", "Complete the Microsoft device sign-in shown below."))
    interval = int(device.get("interval", 5))
    deadline = time.time() + int(device.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(interval)
        result = post_form(
            f"{root}/token",
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": CLIENT_ID,
                "device_code": device["device_code"],
            },
        )
        if result.get("refresh_token"):
            print("\nAuthorization succeeded. Store this value as the GitHub Actions secret")
            print("OUTLOOK_REFRESH_TOKEN. Do not share or commit it:\n")
            print(result["refresh_token"])
            return 0
        error = result.get("error", "")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        print("Microsoft authorization failed:")
        print(json.dumps(result, indent=2))
        return 1

    print("Device code expired. Run the helper again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
