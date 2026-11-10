# adeasy.com

AdEasy's website: plain HTML, CSS and JavaScript, hosted on Cloudflare Workers (static assets).
Every commit to `main` deploys automatically in a minute or two.

This repo is the source of truth. Always start a change from the current files here (download the
repo first), never from the old Claude Design canvas or an old zip, or fixes made since launch get lost.
Design reference (retired after launch): the Claude Design canvas, artifact `370a5aca-2fc4-45b9-950e-f8d9f7c9fc3a`.

## Folder map

```
index.html, about.html, ...   built pages, one file per URL (do not edit by hand, see below)
who-we-help/, success-stories/, portfolio/, about/   pages under those URL folders
assets/css/base.css           design tokens (colours, fonts) and base type
assets/css/layout.css         page frame, header and nav, footer
assets/css/blocks.css         shared building blocks; inlined into every page head at build time
assets/css/components.css     blog post layout, phone-size rules, forms, gallery lightbox
assets/css/pages.css          rules used by one page only, labelled by page
assets/js/site.js             phone menu, click events, Resources and Gallery filters, Calendly
assets/js/forms.js            form sending, honeypot, Turnstile, generate_lead event
assets/img/                   images (fallback JPG/PNG), named per the naming rules
assets/img/opt/               generated AVIF and WebP; never edit by hand
assets/img/og/                1200 x 630 social sharing images
_source/pages/                the body of each page (what you edit)
_source/partials/             header, footer and the assessment CTA, shared by every page
_source/img/                  original images (not deployed)
_source/seo.json              each page's title, description, social image and breadcrumb name
_source/redirect-map.csv      every old URL and where it goes (source for _redirects)
_source/apps-script/          the Google Apps Script that receives form submissions
tools/                        build and check scripts (not deployed)
_redirects, _headers, robots.txt, sitemap.xml, llms.txt, 404.html, favicons, wrangler.jsonc
```

## How a page is built

Pages are generated, so the head, header and footer are identical everywhere.

1. Edit the page body in `_source/pages/<name>.html`, or a shared piece in `_source/partials/`.
2. Run `python3 tools/build-html.py`. It writes every page: head (meta, social tags, favicon, fonts,
   critical CSS, tracking, schema), header, body, footer, and `sitemap.xml`.
3. Run `python3 tools/check-site.py`. Fix anything it reports before uploading.

Each section of a page is wrapped in `<!-- SECTION: Name -->` comments with a matching `id`;
search for `SECTION:` to see a page's structure.

## IDs and keys

All in `tools/site_config.py`:

| Setting | Value |
| --- | --- |
| GTM container | `GTM_ID` (set before launch) |
| GA4 | configured inside GTM, one config tag only |
| Form endpoint | `FORM_ENDPOINT` (Apps Script web app URL) |
| Turnstile site key | `TURNSTILE_SITEKEY` (the secret key lives only in Apps Script) |
| Search Console tag | `GSC_VERIFICATION` |

## Forms

- Contact form: saved to the "Leads" tab of the form Sheet, emailed to support@adeasy.com with
  forms@adeasy.com BCC'd, reply-to set to the visitor, subject `[ADE] Contact: <name>`.
- Careers form: emailed to careers@adeasy.com with the resume attached (forms@adeasy.com BCC'd).
- Spam protection: Cloudflare Turnstile (checked by the Apps Script with Cloudflare's siteverify)
  plus a hidden honeypot field. If verification fails the visitor sees our email and phone number.
- `generate_lead` is pushed to the dataLayer only after the script confirms the save.
- When the script changes, update the existing deployment with a new version. Never create a new
  deployment: that changes the URL and silently breaks every form.

## Tracking

GTM loads on the visitor's first interaction, or 2 seconds after the page loads. Events pushed by
the site: `generate_lead` (form_name), `phone_click` and `email_click` (link_location),
`booking_complete` (Calendly booking on the assessment page). No names, emails or phone numbers
are ever sent to GA4.

## Redirects

`_redirects` sends every old URL to its new page with a 301 (exact rules first, wildcards last).
Keep every rule permanently. To add one: add a line `old-path new-path 301`, pointing straight at
the final URL (no chains). The full review list is `_source/redirect-map.csv`.

## Images

Put the original in `_source/img/` (lowercase, hyphens, three to six descriptive words, for example
`clean-line-technician-at-van.jpg`), add its rendered widths to `_source/image-sizes.json`, then run
`python3 tools/build-images.py .`. It writes the fallback, AVIF and WebP versions and strips EXIF/GPS.
Use the image in a page as `<img src="/assets/img/<name>.jpg" alt="...">`; the build adds the rest.
Social images: `python3 tools/build-og.py`.

## Adding a page

1. Add a row to `PAGES` in `tools/pages.py` (URL, source name, nav section, type, parent).
2. Create `_source/pages/<name>.html` (copy a similar page's sections).
3. Add its title (50 to 60 characters, `| AdEasy` last), description (140 to 160 characters) and
   breadcrumb name to `_source/seo.json`; run `tools/build-og.py` for its social image.
4. Link it from the nav (`_source/partials/header.html`) or footer if it needs one.
5. Build, check, upload. The sitemap and schema update automatically.
6. Add a line to `CHANGELOG.md`.

## Deploys and rollback

GitHub `main` deploys to the `adeasy-site` Worker on Cloudflare. Uploading in GitHub's web view:
Add file > Upload files, drag the folder contents in, commit. Renamed or deleted files must be
deleted in GitHub by hand. If a deploy breaks the site, roll back from the Worker's Deployments view.
