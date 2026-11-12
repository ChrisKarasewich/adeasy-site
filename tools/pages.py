# pages.py: the site map. One row per page: URL, source file, nav section, page type, breadcrumb parent.
# To add a page: add a row here, add its body to _source/pages/, re-run build-html.py.
# URLs are extensionless; the file is written to <url>.html ("/" becomes index.html).

PAGES = [
    # url, source (in _source/pages, without .html), nav, type, parent url
    ("/", "home", "", "home", None),
    ("/what-we-do", "what-we-do", "services", "service-hub", "/"),
    ("/who-we-help", "who-we-help", "industries", "hub", "/"),
    ("/who-we-help/plumbing-and-drain", "plumbing-and-drain", "industries", "service", "/who-we-help"),
    ("/who-we-help/hvac-and-mechanical", "hvac-and-mechanical", "industries", "service", "/who-we-help"),
    ("/who-we-help/electrical", "electrical", "industries", "service", "/who-we-help"),
    ("/who-we-help/windows-and-doors", "windows-and-doors", "industries", "service", "/who-we-help"),
    ("/success-stories", "success-stories", "results", "hub", "/"),
    ("/success-stories/clean-line", "clean-line", "results", "case", "/success-stories"),
    ("/success-stories/mr-boomtruck", "mr-boomtruck", "results", "case", "/success-stories"),
    ("/success-stories/sterling-plumbing", "sterling-plumbing", "results", "case", "/success-stories"),
    ("/success-stories/polar-windows", "polar-windows", "results", "case", "/success-stories"),
    ("/success-stories/winnipeg-sewer-and-drain", "winnipeg-sewer-and-drain", "results", "case", "/success-stories"),
    ("/success-stories/bc-plumbing", "bc-plumbing", "results", "case", "/success-stories"),
    ("/success-stories/pinnacle-painting", "pinnacle-painting", "results", "case", "/success-stories"),
    ("/success-stories/adesa-auctions", "adesa-auctions", "results", "case", "/success-stories"),
    ("/success-stories/adult-and-teen-challenge", "adult-and-teen-challenge", "results", "case", "/success-stories"),
    ("/success-stories/pre-con-builders", "pre-con-builders", "results", "case", "/success-stories"),
    ("/success-stories/remax-dream-bike", "remax-dream-bike", "results", "case", "/success-stories"),
    ("/success-stories/ultracuts", "ultracuts", "results", "case", "/success-stories"),
    ("/resources", "resources", "resources", "hub", "/"),
    ("/about", "about", "resources", "about", "/"),
    ("/about/business-easy-podcast", "business-easy-podcast", "resources", "page", "/about"),
    ("/careers", "careers", "resources", "page", "/"),
    ("/client-photo-gallery", "client-photo-gallery", "resources", "page", "/"),
    ("/contact", "contact", "contact", "contact", "/"),
    ("/marketing-systems-assessment", "marketing-systems-assessment", "resources", "service", "/"),
    ("/thank-you", "thank-you", "", "utility", "/"),
    ("/call-booked", "call-booked", "", "utility", "/"),
    ("/careers/thank-you", "careers-thank-you", "", "utility", "/careers"),
    ("/marketing-systems-assessment/booked", "assessment-booked", "", "utility", "/marketing-systems-assessment"),
    ("/privacy-policy", "privacy-policy", "", "legal", "/"),
    ("/terms-of-use", "terms-of-use", "", "legal", "/"),
    ("/404", "404", "", "utility", "/"),  # served for any unknown URL (wrangler.jsonc: not_found_handling)
    # Blog and older case-study posts keep their old WordPress slugs so no redirect is needed.
    ("/portfolio/spring-checkup-ad-campaign", "post-spring-checkup", "results", "post", "/resources"),
    ("/portfolio/ac-fact-or-fiction-campaign", "post-ac-fact-or-fiction", "results", "post", "/resources"),
    ("/portfolio/window-grants-campaign-earns-140k-lead-generation-campaign", "post-window-grants", "results", "post", "/resources"),
    ("/portfolio/polar-windows-5-signs-facebook-lead-generation-campaign", "post-polar-5-signs", "results", "post", "/resources"),
    ("/outsourced-marketing-department-home-service-companies", "post-outsourced-marketing-department", "resources", "post", "/resources"),
    ("/whats-a-google-ad", "post-google-ads", "resources", "post", "/resources"),
    ("/what-are-facebook-ads", "post-facebook-ads", "resources", "post", "/resources"),
    ("/how-a-great-brand-voice-increases-revenue-engages-customers", "post-brand-voice", "resources", "post", "/resources"),
    ("/the-half-glass-full-perspective-how-your-business-can-flourish-during-a-global-pandemic", "post-half-glass-full", "resources", "post", "/resources"),
    ("/exchange-agency-is-now-adeasy-inc", "post-exchange-agency", "resources", "post", "/resources"),
    ("/dream-ride_fundraising_event", "post-dream-ride", "resources", "post", "/resources"),
    ("/now-hiring-inside-sales-representative", "career-inside-sales-representative", "resources", "career", "/careers"),
    ("/now-hiring-account-executive", "career-account-executive", "resources", "career", "/careers"),
    ("/now-hiring-project-coordinator", "career-project-coordinator", "resources", "career", "/careers"),
    ("/now-hiring-client-advisor", "career-client-advisor", "resources", "career", "/careers"),
    ("/now-hiring-brand-manager", "career-brand-manager", "resources", "career", "/careers"),
    ("/freelance-wordpress-developer", "career-freelance-wordpress-developer", "resources", "career", "/careers"),
    ("/part-time_videographer", "career-part-time-videographer", "resources", "career", "/careers"),
    ("/account-manager", "career-account-manager", "resources", "career", "/careers"),
]

NOINDEX = {"/thank-you", "/call-booked", "/careers/thank-you", "/marketing-systems-assessment/booked", "/404"}  # kept out of search and the sitemap


def out_file(url):
    return "index.html" if url == "/" else url.strip("/") + ".html"
