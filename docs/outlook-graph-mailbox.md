# Outlook.com mailbox support (Microsoft Graph)

This is an optional inbox reader for an existing Outlook.com/Hotmail account.
It does not create Microsoft accounts, register airport accounts by itself, or
automate CAPTCHA, phone checks, or other Microsoft security challenges.

## What changes

- When the Outlook secrets are configured, airport email-verification flows
  that accept a normal mailbox can use this Outlook inbox.
- Sites that explicitly require a Gmail-only whitelist continue using the
  existing Gmail provider; Outlook cannot satisfy a Gmail-only restriction.
- When the secrets are absent, the current Mail.tm/MOAKT behavior is unchanged.
- The adapter reads Inbox messages only. It never deletes the real mailbox or messages.

## Microsoft setup

1. In Microsoft Entra app registrations, create an app that supports personal
   Microsoft accounts (or organizational and personal Microsoft accounts).
2. Enable **Allow public client flows** for the app.
3. Add the delegated Microsoft Graph permission **Mail.Read**. The helper also
   requests `offline_access`.
4. In a trusted environment, set `MS_CLIENT_ID` to the app's Application
   (client) ID and run:
   `python subscribe/outlook_device_auth.py`
5. Follow Microsoft's device sign-in instructions and sign in to the mailbox
   you own. If Microsoft requires CAPTCHA, phone verification, or additional
   security checks, complete them yourself. This integration does not bypass them.
6. After consent, the helper prints a refresh token. Store it directly in the
   GitHub Actions secret `OUTLOOK_REFRESH_TOKEN`. Do not run the helper in a
   public CI job or share its terminal output.
7. Add these repository Actions secrets:
   - `OUTLOOK_EMAIL`: your existing Outlook.com/Hotmail address
   - `OUTLOOK_CLIENT_ID`: the app's Application (client) ID
   - `OUTLOOK_REFRESH_TOKEN`: the refresh token from the helper

Optional repository Actions variable:
- `OUTLOOK_TENANT`: defaults to `common`; normally leave it unchanged.

The Process workflow passes these secrets to the Python process. If they are
not configured, the current mailbox providers remain in use. Microsoft may
rotate refresh tokens; if token refresh later fails, repeat device authorization
and replace the secret. Never share mailbox passwords, access tokens, or refresh
tokens in chat, commits, issues, or logs.

## Validation

The PR includes a syntax/import check workflow. A real inbox test still requires
the mailbox owner to complete Microsoft consent and configure the three secrets.
