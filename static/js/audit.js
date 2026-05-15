/* audit.js — GCE Admission Portal | Audit log page filter */

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("auditSearch");
  const rows  = document.querySelectorAll("#auditTable tr");
  if (!input) return;

  input.addEventListener("input", () => {
    const term = input.value.toLowerCase();
    rows.forEach(row => {
      row.style.display = row.innerText.toLowerCase().includes(term) ? "" : "none";
    });
  });
});
