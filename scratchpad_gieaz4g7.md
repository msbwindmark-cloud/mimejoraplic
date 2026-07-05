# Task: Log in to TrustBridge and inspect dashboard

## Plan
- [x] View the login page DOM to locate form inputs (`admin@trustbridge.com` / `password123`)
- [x] Enter credentials and submit
- [x] Verify redirects or 2FA requirements (Redirected to dashboard at `/` but encountered TemplateSyntaxError on line 226 of dashboard.html: `{% var active_fences = 0 %}`)
- [x] Take a screenshot of the dashboard and describe what is visible
- [x] Report final URL and actions

## Findings
- Found `TemplateSyntaxError` at `/` due to invalid block tag `var` at line 226 in `dashboard.html`.
- Tried to navigate to `/document/upload/` which returned 404. Discovered that the correct path is `/upload/`.
- Successfully logged in as `admin@trustbridge.com` and confirmed that navigating to `/upload/` works, showing that the login state is active and valid.


