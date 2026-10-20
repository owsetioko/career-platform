// Opt-in consent for Google Analytics. gtag.js is not requested until the
// visitor accepts; declining (or no JavaScript) means nothing goes to Google.
(function () {
  var measurementId = document.currentScript.dataset.measurementId;
  var storageKey = "analytics-consent";
  var banner = document.getElementById("consent-banner");
  var openButtons = document.querySelectorAll("[data-consent-open]");

  function stored() {
    try {
      return localStorage.getItem(storageKey);
    } catch (error) {
      return null;
    }
  }

  function store(choice) {
    try {
      localStorage.setItem(storageKey, choice);
    } catch (error) {
      // Storage blocked: the choice applies to this page view only.
    }
  }

  function loadAnalytics() {
    if (window.gtag) return;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () {
      window.dataLayer.push(arguments);
    };
    window.gtag("consent", "default", {
      analytics_storage: "granted",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
    });
    window.gtag("js", new Date());
    window.gtag("config", measurementId, {
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
    });
    var tag = document.createElement("script");
    tag.async = true;
    tag.src =
      "https://www.googletagmanager.com/gtag/js?id=" +
      encodeURIComponent(measurementId);
    document.head.appendChild(tag);
  }

  // Remove _ga and _ga_* cookies from this host and each parent domain.
  function clearAnalyticsCookies() {
    var labels = location.hostname.split(".");
    var domains = [""];
    for (var i = 0; i < labels.length - 1; i++) {
      domains.push("; domain=." + labels.slice(i).join("."));
    }
    document.cookie.split(";").forEach(function (pair) {
      var name = pair.split("=")[0].trim();
      if (name !== "_ga" && name.indexOf("_ga_") !== 0) return;
      domains.forEach(function (domain) {
        document.cookie =
          name + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" + domain;
      });
    });
  }

  function showBanner() {
    banner.hidden = false;
  }

  function choose(choice) {
    var wasLoaded = Boolean(window.gtag);
    store(choice);
    banner.hidden = true;
    if (openButtons.length) openButtons[0].focus();
    if (choice === "granted") {
      loadAnalytics();
    } else {
      clearAnalyticsCookies();
      // gtag.js cannot be unloaded, so start a clean page without it.
      if (wasLoaded) location.reload();
    }
  }

  banner.querySelectorAll("[data-consent]").forEach(function (button) {
    button.addEventListener("click", function () {
      choose(button.dataset.consent);
    });
  });

  openButtons.forEach(function (button) {
    button.hidden = false;
    button.addEventListener("click", function () {
      showBanner();
      banner.querySelector("[data-consent]").focus();
    });
  });

  if (stored() === "granted") {
    loadAnalytics();
  } else if (stored() !== "denied") {
    showBanner();
  }
})();
