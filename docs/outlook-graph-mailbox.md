# Outlook.com mailbox support (Microsoft Graph)

This is an **optional inbox reader for an existing Outlook.com/Hotmail account**.
It does not create Microsoft accounts, register airport accounts by itself, or
automate CAPTCHA, phone checks, or other Microsoft security challenges.

## What changes

- When all three environment variables below are present, the existing airport
  email-verification flow uses this Outlook inbox.
- When they are absent, the current Mail.tm/MOAKT temporary-mail behavior is unchanged.
- If a site requires a Gmail-only whitelist, the existing Gmail provider remains
  selected for that case.
- The adapter only reads the Inbox. It never deletes the real mailbox or messages.

## Microsoft setup

1. In the Microsoft Entra app registrations portal, create an app that supports
   personal Microsoft accounts (or accounts in any organizational directory and
   personal Microsoft accounts).
2. Enable **Allow public client flows** for the app.
3. Add the delegated Microsoft Graph permission **Mail.Read**. The sign-in
   helper requests `offline_access` as well.
4. Run `python subscribe/outlook_device_auth.py` in a trusted environment with
   `MS_CLIENT_ID` set to the app's Application (client) ID. Follow Microsoft's
   device sign-in instructions and sign in to the mailbox you own.
5. Copy the resulting refresh token directly into a GitHub Actions secret named
   `OUTLOOK_REFRESH_TOKEN`. Do not paste it into chat, commit it, or put it in
   a workflow file.
6. Add these repository Actions secrets:
   - `OUTLOOK_EMAIL`: your existing Outlook.com/Hotmail address
   - `OUTLOOK_CLIENT_ID`: the app's Application (client) ID
   - `OUTLOOK_REFRESH_TOKEN`: the refresh token from the helper

Optional repository Actions variable:
- `OUTLOOK_TENANT`: defaults to `common`; normally leave it unchanged.

Microsoft may return a replacement refresh token. If future token refreshes fail,
repeat the device authorization and replace the secret. Never share mailbox
passwords, access tokens, or refresh tokens.

## Local check

Run the existing Python test/lint workflow after installing the project's
requirements. The feature is opt-in and does not alter the current production
workflow until the three secrets are configured.
