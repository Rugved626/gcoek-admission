/* student.js — GCE Admission Portal | Student form interactions */

document.addEventListener("DOMContentLoaded", () => {

  // ── Year transition → dynamic credit/scholarship fields ──────
  const yearTransition    = document.getElementById("yearTransition");
  const credit1Wrap       = document.getElementById("credit1Wrap");
  const credit2Wrap       = document.getElementById("credit2Wrap");
  const credit3Wrap       = document.getElementById("credit3Wrap");
  const schReg1Wrap       = document.getElementById("schReg1Wrap");
  const schReg2Wrap       = document.getElementById("schReg2Wrap");
  const schReg3Wrap       = document.getElementById("schReg3Wrap");
  const firstYearCredits  = document.getElementById("firstYearCredits");
  const secondYearCredits = document.getElementById("secondYearCredits");
  const thirdYearCredits  = document.getElementById("thirdYearCredits");
  const totalCredits      = document.getElementById("totalCredits");

  function applyYearTransition() {
    const val  = yearTransition ? yearTransition.value : "";
    const show2 = val === "2nd to 3rd" || val === "3rd to 4th";
    const show3 = val === "3rd to 4th";

    if (credit1Wrap) credit1Wrap.style.display = val  ? "block" : "none";
    if (credit2Wrap) credit2Wrap.style.display = show2 ? "block" : "none";
    if (credit3Wrap) credit3Wrap.style.display = show3 ? "block" : "none";

    if (!show2 && secondYearCredits) secondYearCredits.value = "";
    if (!show3 && thirdYearCredits)  thirdYearCredits.value  = "";

    if (schReg1Wrap) schReg1Wrap.style.display = val  ? "block" : "none";
    if (schReg2Wrap) schReg2Wrap.style.display = show2 ? "block" : "none";
    if (schReg3Wrap) schReg3Wrap.style.display = show3 ? "block" : "none";

    calculateTotal();
  }

  function calculateTotal() {
    const f = parseInt(firstYearCredits  ? firstYearCredits.value  : 0) || 0;
    const s = parseInt(secondYearCredits ? secondYearCredits.value : 0) || 0;
    const t = parseInt(thirdYearCredits  ? thirdYearCredits.value  : 0) || 0;
    if (totalCredits) totalCredits.value = f + s + t;
  }

  if (yearTransition) {
    yearTransition.addEventListener("change", applyYearTransition);
    applyYearTransition();
  }
  if (firstYearCredits)  firstYearCredits.addEventListener("input",  calculateTotal);
  if (secondYearCredits) secondYearCredits.addEventListener("input", calculateTotal);
  if (thirdYearCredits)  thirdYearCredits.addEventListener("input",  calculateTotal);

  // ── Scholarship toggle ────────────────────────────────────────
  const scholarshipYes     = document.getElementById("scholarshipYes");
  const scholarshipNo      = document.getElementById("scholarshipNo");
  const scholarshipWrapper = document.getElementById("scholarshipDetailsWrapper");

  function toggleScholarship() {
    if (!scholarshipWrapper) return;
    scholarshipWrapper.style.display =
      (scholarshipYes && scholarshipYes.checked) ? "block" : "none";
  }

  if (scholarshipYes) scholarshipYes.addEventListener("change", toggleScholarship);
  if (scholarshipNo)  scholarshipNo.addEventListener("change",  toggleScholarship);
  toggleScholarship();

  // ── Scholarship scheme "Other" → custom text field ───────────
  const schemeDropdown   = document.getElementById("schemeDropdown");
  const customSchemeWrap = document.getElementById("customSchemeWrap");
  const customSchemeName = document.getElementById("customSchemeName");

  function toggleCustomScheme() {
    if (!schemeDropdown || !customSchemeWrap) return;
    const isOther = schemeDropdown.value === "Other";
    customSchemeWrap.style.display = isOther ? "block" : "none";
    if (customSchemeName) {
      customSchemeName.required = isOther;
      if (!isOther) customSchemeName.value = "";
    }
  }

  if (schemeDropdown) {
    schemeDropdown.addEventListener("change", toggleCustomScheme);
    toggleCustomScheme();
  }

  // ── IFSC uppercase enforcement ────────────────────────────────
  const ifscInput = document.querySelector("input[name='ifsc_code']");
  if (ifscInput) {
    ifscInput.addEventListener("input", () => {
      const pos = ifscInput.selectionStart;
      ifscInput.value = ifscInput.value.toUpperCase();
      ifscInput.setSelectionRange(pos, pos);
    });
  }

  // ── Reset button restores dynamic visibility ──────────────────
  const resetBtn = document.querySelector("button[type='reset']");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      setTimeout(() => {
        applyYearTransition();
        toggleScholarship();
        toggleCustomScheme();
      }, 0);
    });
  }

});
