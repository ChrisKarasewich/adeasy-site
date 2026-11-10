/* forms.js: sends every site form to the form endpoint (Google Apps Script), with a honeypot and
   Cloudflare Turnstile. Fires generate_lead only after the endpoint confirms the row saved.
   The endpoint URL is set per form by build-html.py (data-endpoint); blank = demo mode. */
(function () {
  "use strict";
  var dl = (window.dataLayer = window.dataLayer || []);

  function fail(form, msg) {
    var box = form.querySelector(".form-error");
    if (!box) {
      box = document.createElement("p");
      box.className = "form-error";
      box.setAttribute("role", "alert");
      form.appendChild(box);
    }
    box.innerHTML =
      msg ||
      'Sorry, your message didn’t go through. Please email <a href="mailto:support@adeasy.com">support@adeasy.com</a> or call <a href="tel:+12048094978">204-809-4978</a>.';
  }

  function toBase64(file) {
    return new Promise(function (resolve, reject) {
      var r = new FileReader();
      r.onload = function () {
        resolve(String(r.result).split(",")[1]);
      };
      r.onerror = reject;
      r.readAsDataURL(file);
    });
  }

  document.querySelectorAll("form[data-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var file = form.querySelector('input[type="file"]');
      if (file) {
        var f = file.files && file.files[0];
        file.setCustomValidity(f && f.size > 10 * 1024 * 1024 ? "Please upload a file under 10 MB." : "");
      }
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }
      var thanks = form.getAttribute("action") || "/thank-you";
      var endpoint = form.getAttribute("data-endpoint");
      var name = form.getAttribute("data-form");
      if (!endpoint) {
        window.location.href = thanks;
        return;
      } // demo mode: no endpoint yet

      var btn = form.querySelector('[type="submit"]');
      if (btn) {
        btn.disabled = true;
        btn.dataset.label = btn.textContent;
        btn.textContent = "Sending…";
      }
      var data = {};
      new FormData(form).forEach(function (v, k) {
        if (typeof v === "string") data[k] = v;
      });
      data.form_name = name;
      data.page = location.pathname;
      data.submitted_at = new Date().toISOString();
      var ready = Promise.resolve();
      if (file && file.files && file.files[0]) {
        var fl = file.files[0];
        ready = toBase64(fl).then(function (b64) {
          data.file_name = fl.name;
          data.file_type = fl.type;
          data.file_b64 = b64;
          delete data[file.name];
        });
      }
      ready
        .then(function () {
          // text/plain keeps this a "simple" request, so Apps Script answers without a CORS preflight
          // and its reply can be read (unlike no-cors).
          return fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "text/plain;charset=utf-8" },
            body: JSON.stringify(data),
          });
        })
        .then(function (r) {
          return r.json();
        })
        .then(function (res) {
          if (res && res.ok) {
            dl.push({ event: "generate_lead", form_name: name });
            setTimeout(function () {
              window.location.href = thanks;
            }, 300);
          } else {
            throw new Error((res && res.error) || "not saved");
          }
        })
        .catch(function () {
          fail(form);
          if (window.turnstile) {
            try {
              window.turnstile.reset();
            } catch (x) {
              /* widget gone */
            }
          }
          if (btn) {
            btn.disabled = false;
            btn.textContent = btn.dataset.label;
          }
        });
    });
  });
})();
