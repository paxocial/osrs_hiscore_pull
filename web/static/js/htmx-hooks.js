// Minimal HTMX helpers: global loading state and error logging.
(function () {
  document.body.classList.add("htmx-ready");

  document.body.addEventListener("htmx:beforeRequest", function () {
    document.body.classList.add("htmx-loading");
  });

  document.body.addEventListener("htmx:afterRequest", function () {
    document.body.classList.remove("htmx-loading");
  });

  document.body.addEventListener("htmx:responseError", function (evt) {
    console.error("HTMX request failed", evt.detail);
  });
})();
