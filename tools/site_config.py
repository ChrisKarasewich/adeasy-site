# site_config.py: every ID, key and URL the site needs, in one place.
# build-html.py reads this file. Change a value here, re-run the build, and every page picks it up.

SITE = "https://adeasy.com"  # canonical host: apex, no trailing slash (www redirects here)

# Tracking. Leave blank until confirmed; the build then leaves the tag out instead of shipping a placeholder.
GTM_ID = ""  # e.g. GTM-ABC1234 (Hugh to confirm; must be AdEasy's existing container)
GTM_DELAY_MS = 2000  # GTM loads on first interaction, or this long after window load

# Forms
FORM_ENDPOINT = ""  # Google Apps Script web app URL (/exec). Blank = demo mode (validate, then thank-you page)
TURNSTILE_SITEKEY = ""  # Cloudflare Turnstile site key (public). The secret key lives only in Apps Script.

# Search Console HTML-tag verification (content value only). Blank if verified by DNS.
GSC_VERIFICATION = ""

# Business facts used in schema and llms.txt. Keep identical to the Google Business Profile and LinkedIn.
ORG = {
    "name": "AdEasy",
    "legalName": "AdEasy Inc.",
    "phone": "+1-204-809-4978",
    "phone_display": "204-809-4978",
    "email": "support@adeasy.com",
    "street": "309 McDermot Ave, Unit 230",
    "city": "Winnipeg",
    "region": "MB",
    "postal": "R3A 1T3",
    "country": "CA",
    "founder": "Chris Karasewich",
    "foundingDate": "2013",
    "sameAs": [
        "https://www.linkedin.com/company/itsadeasy",
        "https://www.facebook.com/itsadeasy/",
        "https://www.instagram.com/itsadeasy/",
        "https://www.youtube.com/channel/UCTTRJCenKIkPTxS1tkMbgWQ",
        "https://vimeo.com/itsadeasy",
        # Add the Google Business Profile link here once confirmed.
    ],
    "founder_linkedin": "https://www.linkedin.com/in/karasewich",
}

BOOKING_URL = "https://calendly.com/chris_karasewich/discovery-call"
