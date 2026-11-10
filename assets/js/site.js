/* site.js: behaviour shared by every page: phone menu, phone/email click events,
   and the few page features that need JavaScript (Home bar chart, Resources filter,
   Client Photo Gallery filter and lightbox, Calendly embed on the assessment page). */
(function () {
  "use strict";
  var dl = (window.dataLayer = window.dataLayer || []);

  /* ---- Phone menu ---- */
  var toggle = document.querySelector(".nav-toggle");
  var menu = document.getElementById("nav-mobile");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") !== "true";
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      menu.hidden = !open;
    });
    menu.querySelectorAll(".nav-mobile__group").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var sub = document.getElementById(btn.getAttribute("aria-controls"));
        var open = btn.getAttribute("aria-expanded") !== "true";
        menu.querySelectorAll(".nav-mobile__group").forEach(function (b) {
          b.setAttribute("aria-expanded", "false");
          document.getElementById(b.getAttribute("aria-controls")).hidden = true;
        });
        btn.setAttribute("aria-expanded", String(open));
        sub.hidden = !open;
      });
    });
  }

  /* ---- Click events for GA4 (no personal data is sent) ---- */
  function where(el) {
    if (el.closest(".site-header")) return "header";
    if (el.closest(".site-footer")) return "footer";
    return "page";
  }
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest('a[href^="tel:"], a[href^="mailto:"]');
    if (!a) return;
    dl.push({ event: a.href.indexOf("tel:") === 0 ? "phone_click" : "email_click", link_location: where(a) });
  });
  /* Assessment buttons go straight to Calendly, so count the click here */
  document.addEventListener("click", function (e) {
    var a =
      e.target.closest && e.target.closest('a[href*="calendly.com/chris_karasewich/marketing-system-assessment"]');
    if (a) dl.push({ event: "assessment_click", link_location: where(a) });
  });

  /* ---- Assessment booked page: Calendly sends people here after they book ---- */
  /* Calendly can add the booker's name and email to the address. Strip it before analytics loads,
     so no personal details ever reach Google Analytics. */
  if (/invitee_|answer_\d|event_type_/.test(location.search)) {
    try {
      history.replaceState(null, "", location.pathname + location.hash);
    } catch (x) {
      /* older browsers: nothing to do */
    }
  }
  if (location.pathname.replace(/\/$/, "") === "/marketing-systems-assessment/booked") {
    dl.push({ event: "assessment_booked" });
  }
  if (location.pathname.replace(/\/$/, "") === "/call-booked") {
    dl.push({ event: "discovery_call_booked" });
  }

  /* ---- Home: bars grow in when the chart scrolls into view ---- */
  /* The $2.34M callout counts up from $1.51M (red) to $2.34M alongside the bars, turning teal at $2M. */
  var stack = document.querySelector(".home-stack");
  var pot = document.querySelector(".home-potential");
  var potBox = pot && pot.closest(".home-callout");
  var POT_FROM = 1.51,
    POT_TO = 2.34,
    potRaf = null,
    potOn = false;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function setPot(v) {
    if (!pot) return;
    if (reduceMotion) v = POT_TO;
    pot.textContent = "$" + v.toFixed(2) + "M";
    pot.style.color = v >= 2 ? "#2e6e74" : "#b03f08";
    if (potBox) potBox.style.borderColor = v >= 2 ? "#4da4ac" : "#c44908";
  }
  function runPot() {
    if (!pot) return;
    cancelAnimationFrame(potRaf);
    var start = performance.now(),
      delay = 200,
      dur = 1520; // first orange segment starts at 200ms, last one finishes at 920ms + 800ms
    setPot(POT_FROM);
    function step(now) {
      var t = Math.min(1, Math.max(0, (now - start - delay) / dur));
      setPot(POT_FROM + (POT_TO - POT_FROM) * (1 - Math.pow(1 - t, 3)));
      if (t < 1 && potOn) potRaf = requestAnimationFrame(step);
      else potRaf = null;
    }
    potRaf = requestAnimationFrame(step);
  }
  if (stack) {
    if (!("IntersectionObserver" in window)) {
      stack.classList.add("is-in");
      setPot(POT_TO);
    } else {
      setPot(POT_FROM);
      new IntersectionObserver(
        function (entries) {
          entries.forEach(function (en) {
            if (en.intersectionRatio >= 0.35) {
              if (stack.classList.contains("is-in")) return;
              stack.classList.add("is-reset");
              void stack.offsetWidth;
              stack.classList.remove("is-reset");
              stack.classList.add("is-in");
              potOn = true;
              runPot();
            } else if (!en.isIntersecting) {
              stack.classList.add("is-reset");
              stack.classList.remove("is-in");
              potOn = false;
              cancelAnimationFrame(potRaf);
              setPot(POT_FROM);
            }
          });
        },
        { threshold: [0, 0.35] },
      ).observe(stack);
    }
  }

  /* ---- Sidebar filters (Resources categories, Gallery clients) ---- */
  function sidebarFilter(btnSel, itemSel, key, onPick) {
    var btns = document.querySelectorAll(btnSel);
    if (!btns.length) return;
    function pick(btn) {
      var val = btn.getAttribute("data-" + key);
      btns.forEach(function (b) {
        var on = b === btn;
        b.setAttribute("aria-pressed", String(on));
        b.style.borderLeftColor = on ? "#C44908" : "transparent";
        b.style.paddingLeft = on ? "14px" : "0";
        b.style.fontWeight = on ? "700" : "400";
        b.style.color = on ? "#1E2859" : "#8A7A62";
      });
      var shown = 0;
      document.querySelectorAll(itemSel).forEach(function (it) {
        var show = val === "All" || it.getAttribute("data-" + key) === val;
        it.style.display = show ? "" : "none"; // inline display styles beat the hidden attribute
        if (show) shown += 1;
      });
      if (onPick) onPick(val, shown);
    }
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        pick(b);
      });
      b.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          pick(b);
        }
      });
    });
  }
  sidebarFilter(".res-cat", ".res-card", "cat", function (val) {
    var h = document.querySelector("[data-res-heading]");
    if (h) h.textContent = val === "All" ? "Latest Posts" : val;
  });

  var grid = document.querySelector(".gal-grid");
  if (grid) {
    var figs = Array.prototype.slice.call(grid.children);
    sidebarFilter(".gal-client", ".gal-grid > figure", "client", function (val) {
      if (val === "All") {
        for (var i = figs.length - 1; i > 0; i--) {
          var j = Math.floor(Math.random() * (i + 1));
          var t = figs[i];
          figs[i] = figs[j];
          figs[j] = t;
        }
        figs.forEach(function (f) {
          grid.appendChild(f);
        });
      }
    });
    /* Lightbox */
    var lb = document.createElement("div");
    lb.className = "gal-lightbox";
    lb.hidden = true;
    lb.setAttribute("role", "dialog");
    lb.setAttribute("aria-modal", "true");
    lb.setAttribute("aria-label", "Photo viewer");
    lb.innerHTML =
      '<button type="button" class="gal-lb-close" aria-label="Close">✕</button>' +
      '<button type="button" class="gal-lb-prev" aria-label="Previous photo">‹</button>' +
      '<figure class="gal-lb-fig"><img alt=""><figcaption></figcaption></figure>' +
      '<button type="button" class="gal-lb-next" aria-label="Next photo">›</button>';
    document.body.appendChild(lb);
    var lbImg = lb.querySelector("img"),
      lbCap = lb.querySelector("figcaption"),
      cur = 0,
      list = [],
      last = null;
    function visible() {
      return figs.filter(function (f) {
        return f.style.display !== "none";
      });
    }
    function show(i) {
      cur = (i + list.length) % list.length;
      var img = list[cur].querySelector("img");
      lbImg.src = img.getAttribute("data-full") || img.currentSrc || img.src;
      lbImg.alt = img.alt;
      lbCap.textContent =
        img.alt + " · " + list[cur].getAttribute("data-client") + " · " + (cur + 1) + " / " + list.length;
    }
    function close() {
      lb.hidden = true;
      document.body.style.overflow = "";
      if (last) last.focus();
    }
    grid.addEventListener("click", function (e) {
      var btn = e.target.closest(".gal-thumb");
      if (!btn) return;
      last = btn;
      list = visible();
      show(list.indexOf(btn.closest("figure")));
      lb.hidden = false;
      document.body.style.overflow = "hidden";
      lb.querySelector(".gal-lb-close").focus();
    });
    lb.querySelector(".gal-lb-close").addEventListener("click", close);
    lb.querySelector(".gal-lb-prev").addEventListener("click", function () {
      show(cur - 1);
    });
    lb.querySelector(".gal-lb-next").addEventListener("click", function () {
      show(cur + 1);
    });
    lb.addEventListener("click", function (e) {
      if (e.target === lb) close();
    });
    document.addEventListener("keydown", function (e) {
      if (lb.hidden) return;
      if (e.key === "Escape") close();
      else if (e.key === "ArrowRight") show(cur + 1);
      else if (e.key === "ArrowLeft") show(cur - 1);
    });
  }

  /* ---- Calendly inline widget (assessment page only); loads when the booking section nears view ---- */
  var cal = document.querySelector(".calendly-inline-widget");
  if (cal) {
    var load = function () {
      if (document.querySelector('script[src*="assets.calendly.com"]')) return;
      var s = document.createElement("script");
      s.src = "https://assets.calendly.com/assets/external/widget.js";
      s.async = true;
      document.head.appendChild(s);
    };
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(
        function (en) {
          if (
            en.some(function (x) {
              return x.isIntersecting;
            })
          ) {
            load();
            io.disconnect();
          }
        },
        { rootMargin: "600px" },
      );
      io.observe(cal);
    } else {
      load();
    }
    window.addEventListener("message", function (e) {
      if (e.origin === "https://calendly.com" && e.data && e.data.event === "calendly.event_scheduled") {
        dl.push({ event: "booking_complete", booking_type: "marketing_systems_assessment" });
      }
    });
  }

  /* ---- Vimeo videos load the player only when someone clicks play ---- */
  document.querySelectorAll(".video-facade[data-vimeo]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      if (document.documentElement.hasAttribute("data-demo")) return; // review copy: open on Vimeo instead
      e.preventDefault();
      var f = document.createElement("iframe");
      f.src = "https://player.vimeo.com/video/" + a.getAttribute("data-vimeo") + "?autoplay=1&badge=0&autopause=0";
      f.title = a.querySelector(".video-facade__title").textContent;
      f.allow = "autoplay; fullscreen; picture-in-picture";
      f.style.cssText = "position:absolute;inset:0;width:100%;height:100%;border:0";
      a.replaceWith(f);
    });
  });
})();
