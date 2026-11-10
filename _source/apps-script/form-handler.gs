/**
 * form-handler.gs: receives every adeasy.com form submission.
 *
 * Setup (once): Google Sheet owned by an AdEasy Workspace account > Extensions > Apps Script >
 * paste this file > Project Settings > Script Properties:
 *   TURNSTILE_SECRET   Cloudflare Turnstile secret key (never put it in the website repo)
 * Deploy > New deployment > Web app > Execute as: Me, Who has access: Anyone. Copy the /exec URL
 * into tools/site_config.py (FORM_ENDPOINT).
 * Later changes: Deploy > Manage deployments > edit the SAME deployment > New version.
 * A new deployment makes a new URL and every form pointing at the old one breaks.
 *
 * What it does:
 *   1. Drops bot submissions (honeypot field "website" filled in).
 *   2. Checks the Turnstile token with Cloudflare before anything else.
 *   3. Contact form: saves a row to the "Leads" tab, emails support@adeasy.com (BCC forms@adeasy.com),
 *      reply-to set to the visitor, subject "[ADE] Contact: <name>".
 *   4. Careers form: emails careers@adeasy.com with the resume attached (BCC forms@adeasy.com),
 *      and logs the application (without the file) on the "Applications" tab.
 *   5. Replies {ok:true} only after the save/email worked, so the site fires generate_lead only then.
 *   6. Emails chris@adeasy.com if something fails, so a broken form never goes unnoticed.
 */

const TO_LEADS = "support@adeasy.com";
const TO_CAREERS = "careers@adeasy.com";
const MONITOR = "forms@adeasy.com";
const ALERT = "chris@adeasy.com";
const SUBJECT_TAG = "[ADE]";

function doPost(e) {
  let data = {};
  try {
    data = JSON.parse(e.postData.contents);
    if (data.website) return reply({ ok: true }); // honeypot: pretend success, keep nothing

    if (!verifyTurnstile(data["cf-turnstile-response"])) {
      return reply({ ok: false, error: "verification_failed" });
    }
    delete data["cf-turnstile-response"];

    if (data.form_name === "Careers application") {
      handleCareers(data);
    } else {
      handleLead(data);
    }
    return reply({ ok: true });
  } catch (err) {
    MailApp.sendEmail(
      ALERT,
      `${SUBJECT_TAG} Website form error`,
      `The adeasy.com form handler failed.\n\nError: ${err}\nForm: ${data.form_name || "unknown"}\nPage: ${data.page || ""}\nTime: ${new Date()}`,
    );
    return reply({ ok: false, error: "server_error" });
  }
}

function verifyTurnstile(token) {
  const secret = PropertiesService.getScriptProperties().getProperty("TURNSTILE_SECRET");
  if (!secret) return true; // Turnstile not set up yet
  if (!token) return false;
  const res = UrlFetchApp.fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "post",
    payload: { secret: secret, response: token },
    muteHttpExceptions: true,
  });
  return JSON.parse(res.getContentText()).success === true;
}

function handleLead(d) {
  const sheet = tab("Leads", ["Submitted", "Form", "Name", "Company", "Email", "Phone", "Message", "Consent", "Page"]);
  sheet.appendRow([
    new Date(),
    d.form_name,
    d.name,
    d.company,
    d.email,
    d.phone,
    d.message,
    d.consent ? "Yes" : "No",
    d.page,
  ]);
  const body = [
    `New ${d.form_name} submission from adeasy.com`,
    "",
    `Name: ${d.name || ""}`,
    `Company: ${d.company || ""}`,
    `Email: ${d.email || ""}`,
    `Phone: ${d.phone || ""}`,
    "",
    `Message:\n${d.message || ""}`,
    "",
    `Page: ${d.page || ""}`,
  ].join("\n");
  MailApp.sendEmail({
    to: TO_LEADS,
    bcc: MONITOR,
    replyTo: d.email,
    subject: `${SUBJECT_TAG} ${d.form_name}: ${d.name || "New lead"}`,
    body: body,
  });
}

function handleCareers(d) {
  const attachments = [];
  if (d.file_b64) {
    attachments.push(
      Utilities.newBlob(
        Utilities.base64Decode(d.file_b64),
        d.file_type || "application/pdf",
        d.file_name || "resume.pdf",
      ),
    );
  }
  const fields = Object.keys(d)
    .filter((k) => !["file_b64", "file_type", "file_name", "form_name", "website"].includes(k))
    .map((k) => `${k}: ${d[k]}`)
    .join("\n");
  MailApp.sendEmail({
    to: TO_CAREERS,
    bcc: MONITOR,
    replyTo: d.email,
    subject: `${SUBJECT_TAG} Careers application: ${d.name || "New applicant"}`,
    body: `New application from adeasy.com\n\n${fields}`,
    attachments: attachments,
  });
  tab("Applications", ["Submitted", "Name", "Email", "Role", "Page", "Resume attached"]).appendRow([
    new Date(),
    d.name,
    d.email,
    d.role || "",
    d.page,
    attachments.length ? "Yes" : "No",
  ]);
}

function tab(name, headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.appendRow(headers);
  }
  return sh;
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
