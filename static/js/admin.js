/* admin.js — GCE Admission Portal | Admin panel interactions */
/* All event logic in external JS — no inline JS in templates   */

document.addEventListener("DOMContentLoaded", () => {

  // ── Session expiry detection ─────────────────────────────────
  // If the server returns a redirect to "/" (login page), the fetch
  // response URL will differ from the current origin — warn the user.
  (function detectSessionExpiry() {
    const SESSION_MINUTES = 60;          // must match PERMANENT_SESSION_LIFETIME
    const warnAfter = (SESSION_MINUTES - 5) * 60 * 1000;  // warn 5 min before expiry

    setTimeout(() => {
      // Only warn if user is still on an admin page
      if (document.querySelector(".inst-header")) {
        const banner = document.createElement("div");
        banner.id = "sessionWarn";
        banner.style.cssText = [
          "position:fixed", "bottom:20px", "right:20px", "z-index:9999",
          "background:#78350f", "color:#fff", "padding:14px 20px",
          "border-radius:4px", "font-size:13px", "box-shadow:0 4px 20px rgba(0,0,0,0.3)",
          "max-width:340px", "line-height:1.5"
        ].join(";");
        banner.innerHTML = [
          "<strong>⚠ Session expiring soon</strong><br>",
          "Your session will expire in 5 minutes. ",
          "<a href='/logout' style='color:#fde68a;text-decoration:underline;'>Log out</a>",
          " or <a href='javascript:location.reload()' style='color:#fde68a;",
          "text-decoration:underline;'>reload</a> to extend."
        ].join("");

        // Dismiss button
        const close = document.createElement("span");
        close.textContent = " ✕";
        close.style.cssText = "cursor:pointer;margin-left:10px;opacity:0.7;";
        close.addEventListener("click", () => banner.remove());
        banner.appendChild(close);

        document.body.appendChild(banner);
      }
    }, warnAfter);
  })();

  // ── Delete confirmation modal ────────────────────────────────
  const deleteForms = document.querySelectorAll("form.delete-form");

  deleteForms.forEach(form => {
    form.addEventListener("submit", e => {
      const appId = form.dataset.id;
      const ok = window.confirm(
        `⚠ Permanently delete application #${appId}?\n\nThis action cannot be undone.`
      );
      if (!ok) e.preventDefault();
    });
  });

  // ── Application table search ─────────────────────────────────
  const searchInput = document.getElementById("searchApplications");
  const tableRows   = document.querySelectorAll("#applicationsTable tr");

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const term = searchInput.value.toLowerCase();
      tableRows.forEach(row => {
        row.style.display = row.innerText.toLowerCase().includes(term) ? "" : "none";
      });
    });
  }

  // ── Export URL builder ───────────────────────────────────────
  const exportBtn    = document.getElementById("exportBtn");
  const exportBranch = document.getElementById("exportBranch");
  const exportGender = document.getElementById("exportGender");

  function buildExportUrl() {
    if (!exportBtn) return;
    const params = new URLSearchParams();
    const branch = exportBranch ? exportBranch.value : "";
    const gender = exportGender ? exportGender.value : "";
    if (branch) params.set("branch", branch);
    if (gender) params.set("gender", gender);
    const qs = params.toString();
    exportBtn.href = "/admin/export-excel" + (qs ? "?" + qs : "");
  }

  if (exportBranch) exportBranch.addEventListener("change", buildExportUrl);
  if (exportGender) exportGender.addEventListener("change", buildExportUrl);
  buildExportUrl();

});
