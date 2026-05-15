document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("downloadBtn");
  if (!btn) return;

  btn.addEventListener("click", () => {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF("p", "mm", "a4");

    const PW = 210, PH = 297;
    const ML = 20, MR = 20;
    const CW = PW - ML - MR; // 170mm

    // ── COLOURS ──────────────────────────────────────────────
    const C = {
      black:      [0,   0,   0],
      darkgrey:   [40,  40,  40],
      midgrey:    [100, 100, 100],
      lightgrey:  [180, 180, 180],
      rulergrey:  [210, 210, 210],
      rowshade:   [247, 247, 247],
      white:      [255, 255, 255],
      headerbg:   [30,  30,  30],
      headertext: [255, 255, 255],
      sectionbg:  [235, 235, 235],
    };

    // ── DATA ─────────────────────────────────────────────────
    const val = (n) => {
      const el = document.querySelector(`[name='${n}']`);
      return el ? (el.value || "").trim() : "";
    };
    const gender  = document.querySelector("input[name='gender']:checked")?.value || "";
    const schYes  = document.querySelector("input[name='applied_for_scholarship']:checked")?.value || "No";
    const yearTrans = val("year_transition");

    // Determine which credit years apply
    const show2Credits = yearTrans === "2nd to 3rd" || yearTrans === "3rd to 4th";
    const show3Credits = yearTrans === "3rd to 4th";

    const D = {
      full_name:                  val("full_name")                  || "N/A",
      email:                      val("email")                       || "N/A",
      bank_account_number:        val("bank_account_number")         || "N/A",
      ifsc_code:                  val("ifsc_code")                   || "N/A",
      branch:                     val("branch")                      || "N/A",
      caste:                      val("caste")                       || "N/A",
      category:                   val("category")                    || "N/A",
      gender:                     gender                             || "N/A",
      student_mobile:             val("student_mobile")              || "N/A",
      parent_mobile:              val("parent_mobile")               || "N/A",
      local_address:              val("local_address")               || "N/A",
      permanent_address:          val("permanent_address")           || "N/A",
      cet_application_number:     val("cet_application_number")      || "N/A",
      prn_number:                 val("prn_number")                  || "N/A",
      admission_date:             val("admission_taking_year")       || "N/A",
      year_transition:            yearTrans                          || "N/A",
      admission_receipt:          val("admission_receipt")           || "N/A",
      first_year_credits:         val("first_year_credits")          || "N/A",
      second_year_credits:        show2Credits ? (val("second_year_credits") || "N/A") : "—",
      third_year_credits:         show3Credits ? (val("third_year_credits")  || "N/A") : "—",
      total_credits:              val("total_credits")               || "N/A",
      scholarship:                schYes,
      income_certificate_number:  schYes === "Yes" ? (val("income_certificate_number")  || "N/A") : "Not Applicable",
      actual_income:              schYes === "Yes" ? (val("actual_income")              || "N/A") : "Not Applicable",
      scholarship_scheme:         schYes === "Yes" ? (() => {
                                    const s = val("scholarship_registration_no");
                                    if (s === "Other") return val("custom_scheme_name") || "Other";
                                    return s || "N/A";
                                  })() : "Not Applicable",
      scholarship_reg_year1:      schYes === "Yes" ? (val("scholarship_reg_year1")      || "N/A") : "Not Applicable",
      scholarship_reg_year2:      schYes === "Yes" && show2Credits ? (val("scholarship_reg_year2") || "N/A") : (schYes === "Yes" ? "—" : "Not Applicable"),
      scholarship_reg_year3:      schYes === "Yes" && show3Credits ? (val("scholarship_reg_year3") || "N/A") : (schYes === "Yes" ? "—" : "Not Applicable"),
    };

    const today = new Date().toLocaleDateString("en-IN", {
      day: "2-digit", month: "long", year: "numeric"
    });

    // ── HELPERS ───────────────────────────────────────────────
    let y = 0;

    const font = (style, size, color) => {
      doc.setFont("helvetica", style);
      doc.setFontSize(size);
      doc.setTextColor(...(color || C.black));
    };

    const hline = (yy, color, lw) => {
      doc.setDrawColor(...(color || C.lightgrey));
      doc.setLineWidth(lw || 0.2);
      doc.line(ML, yy, PW - MR, yy);
    };

    const fillRect = (x, yy, w, h, fill) => {
      doc.setFillColor(...fill);
      doc.rect(x, yy, w, h, "F");
    };

    const checkPageBreak = (needed) => {
      if (y + needed > PH - 25) {
        doc.addPage();
        doc.setDrawColor(...C.lightgrey);
        doc.setLineWidth(0.4);
        doc.rect(12, 12, PW - 24, PH - 24, "D");
        y = 20;
      }
    };

    // ── OUTER BORDER ──────────────────────────────────────────
    doc.setDrawColor(...C.lightgrey);
    doc.setLineWidth(0.4);
    doc.rect(12, 12, PW - 24, PH - 24, "D");

    y = 18;

    // ── HEADER ───────────────────────────────────────────────
    font("bold", 15, C.black);
    doc.text("GOVERNMENT COLLEGE OF ENGINEERING, KOLHAPUR", PW / 2, y, { align: "center" });
    y += 6;

    font("normal", 8.5, C.midgrey);
    doc.text("Autonomous Institute | Affiliated to Shivaji University, Kolhapur", PW / 2, y, { align: "center" });
    y += 5;

    hline(y, C.black, 0.5);
    y += 1;
    hline(y, C.lightgrey, 0.2);
    y += 5;

    font("bold", 11, C.darkgrey);
    doc.text("APPLICATION FORM FOR ADMISSION TO SECOND / THIRD YEAR DEGREE COURSE", PW / 2, y, { align: "center" });
    y += 5;
    font("normal", 8.5, C.midgrey);
    doc.text("Academic Year 2025 – 26", PW / 2, y, { align: "center" });
    y += 4;

    hline(y, C.lightgrey, 0.2);
    y += 1;
    hline(y, C.black, 0.5);
    y += 6;

    font("normal", 7.5, C.midgrey);
    doc.text(`Date: ${today}`, ML, y);
    doc.text(`Application Status: APPROVED`, PW - MR, y, { align: "right" });
    y += 7;

    // ── SECTION HELPER ────────────────────────────────────────
    const section = (title) => {
      checkPageBreak(12);
      fillRect(ML, y, CW, 6.5, C.sectionbg);
      font("bold", 8, C.darkgrey);
      doc.text(title, ML + 3, y + 4.5);
      y += 8;
    };

    // ── ROW HELPERS ───────────────────────────────────────────
    let rowIndex = 0;
    const ROW_H = 7;
    const LABEL_W = 60;

    const row = (label, value) => {
      checkPageBreak(ROW_H + 2);
      if (rowIndex % 2 === 0) fillRect(ML, y, CW, ROW_H, C.rowshade);
      doc.setDrawColor(...C.rulergrey);
      doc.setLineWidth(0.1);
      doc.rect(ML, y, CW, ROW_H, "D");

      font("bold", 7.5, C.midgrey);
      doc.text(label, ML + 3, y + ROW_H / 2 + 1.2);

      doc.setDrawColor(...C.rulergrey);
      doc.setLineWidth(0.1);
      doc.line(ML + LABEL_W, y, ML + LABEL_W, y + ROW_H);

      font("normal", 8, C.darkgrey);
      const lines = doc.splitTextToSize(String(value), CW - LABEL_W - 6);
      const textY = lines.length > 1
        ? y + 3.5 - ((lines.length - 1) * 2.8) / 2
        : y + ROW_H / 2 + 1.2;
      doc.text(lines, ML + LABEL_W + 3, textY);

      y += ROW_H;
      rowIndex++;
    };

    const row2 = (l1, v1, l2, v2) => {
      checkPageBreak(ROW_H + 2);
      const hw = CW / 2;
      if (rowIndex % 2 === 0) {
        fillRect(ML,      y, hw, ROW_H, C.rowshade);
        fillRect(ML + hw, y, hw, ROW_H, C.rowshade);
      }
      doc.setDrawColor(...C.rulergrey);
      doc.setLineWidth(0.1);
      doc.rect(ML,      y, hw, ROW_H, "D");
      doc.rect(ML + hw, y, hw, ROW_H, "D");

      font("bold", 7.5, C.midgrey);
      doc.text(l1, ML + 3, y + ROW_H / 2 + 1.2);
      doc.setDrawColor(...C.rulergrey);
      doc.line(ML + 38, y, ML + 38, y + ROW_H);
      font("normal", 8, C.darkgrey);
      doc.text(String(v1), ML + 41, y + ROW_H / 2 + 1.2);

      font("bold", 7.5, C.midgrey);
      doc.text(l2, ML + hw + 3, y + ROW_H / 2 + 1.2);
      doc.line(ML + hw + 38, y, ML + hw + 38, y + ROW_H);
      font("normal", 8, C.darkgrey);
      doc.text(String(v2), ML + hw + 41, y + ROW_H / 2 + 1.2);

      y += ROW_H;
      rowIndex++;
    };

    // ── PERSONAL DETAILS ─────────────────────────────────────
    section("1.  PERSONAL DETAILS");
    rowIndex = 0;
    row("Full Name", D.full_name);
    row("Email Address", D.email);
    row2("PRN Number", D.prn_number, "Gender", D.gender);
    row("Branch / Programme", D.branch);
    row2("Caste", D.caste, "Category", D.category);
    y += 2;

    // Bank Details sub-section
    checkPageBreak(8);
    fillRect(ML, y, CW, 5.5, [245, 245, 245]);
    font("bold", 7, [120, 80, 0]);
    doc.text("BANK DETAILS  —  Account must belong to the individual student only.", ML + 3, y + 3.8);
    y += 7;
    rowIndex = 0;
    row2("Bank Account Number", D.bank_account_number, "IFSC Code", D.ifsc_code);
    y += 3;

    // ── CONTACT DETAILS ──────────────────────────────────────
    section("2.  CONTACT DETAILS");
    rowIndex = 0;
    row2("Student Mobile", D.student_mobile, "Parent Mobile", D.parent_mobile);
    row("Local Address", D.local_address);
    row("Permanent Address", D.permanent_address);
    y += 3;

    // ── ACADEMIC DETAILS ─────────────────────────────────────
    section("3.  ACADEMIC DETAILS");
    rowIndex = 0;
    row2("CET Application No.", D.cet_application_number, "PRN Number", D.prn_number);
    row2("Admission Date", D.admission_date, "Year Transition", D.year_transition);
    row("Admission Receipt No.", D.admission_receipt);
    row("1st Year Credits", D.first_year_credits);
    if (show2Credits) row("2nd Year Credits", D.second_year_credits);
    if (show3Credits) row("3rd Year Credits", D.third_year_credits);

    // Total credits row
    checkPageBreak(ROW_H + 4);
    fillRect(ML, y, CW, ROW_H, [230, 230, 230]);
    doc.setDrawColor(...C.lightgrey);
    doc.setLineWidth(0.2);
    doc.rect(ML, y, CW, ROW_H, "D");
    font("bold", 7.5, C.darkgrey);
    doc.text("Total Credits Earned", ML + 3, y + ROW_H / 2 + 1.2);
    doc.setDrawColor(...C.lightgrey);
    doc.line(ML + LABEL_W, y, ML + LABEL_W, y + ROW_H);
    font("bold", 9, C.black);
    doc.text(String(D.total_credits), ML + LABEL_W + 3, y + ROW_H / 2 + 1.4);
    y += ROW_H + 3;

    // ── SCHOLARSHIP DETAILS ──────────────────────────────────
    section("4.  SCHOLARSHIP DETAILS");
    rowIndex = 0;
    row("Applied for Scholarship", D.scholarship);
    if (schYes === "Yes") {
      row2("Income Certificate No.", D.income_certificate_number, "Actual Income (₹)", D.actual_income);
      row("Scholarship Scheme Name", D.scholarship_scheme);
      row("1st Year Reg. Number", D.scholarship_reg_year1);
      if (show2Credits) row("2nd Year Reg. Number", D.scholarship_reg_year2);
      if (show3Credits) row("3rd Year Reg. Number", D.scholarship_reg_year3);
    }
    y += 3;

    // ── DECLARATION ──────────────────────────────────────────
    checkPageBreak(20);
    doc.setDrawColor(...C.lightgrey);
    doc.setLineWidth(0.2);
    doc.rect(ML, y, CW, 12, "D");
    font("bold", 7.5, C.darkgrey);
    doc.text("DECLARATION", ML + 3, y + 5);
    font("normal", 7, C.midgrey);
    const decl = doc.splitTextToSize(
      "I hereby declare that all information furnished above is true, complete and correct to the best of my knowledge and belief. I understand that any false information may lead to cancellation of admission.",
      CW - 6
    );
    doc.text(decl, ML + 3, y + 9.5);
    y += 16;

    // ── SIGNATURES ───────────────────────────────────────────
    checkPageBreak(30);
    hline(y, C.lightgrey, 0.2);
    y += 8;

    const sigLine = (x, w, label) => {
      doc.setDrawColor(...C.darkgrey);
      doc.setLineWidth(0.3);
      doc.line(x, y + 8, x + w, y + 8);
      font("normal", 7, C.midgrey);
      doc.text(label, x + w / 2, y + 12, { align: "center" });
    };

    sigLine(ML,       38, "Student Signature");
    sigLine(ML + 44,  38, "Signature of HOD");
    sigLine(ML + 88,  38, "Class Teacher");
    sigLine(ML + 132, 38, "Date");
    y += 18;

    // ── FOR OFFICE USE ONLY ──────────────────────────────────
    checkPageBreak(30);
    hline(y, C.lightgrey, 0.2);
    y += 4;

    font("bold", 7.5, C.midgrey);
    doc.text("FOR OFFICE USE ONLY", PW / 2, y, { align: "center" });
    y += 4;

    hline(y, C.lightgrey, 0.2);
    y += 3;

    rowIndex = 0;
    row2("Eligible for Admission",   "Yes  /  No",           "Admission Fee (₹)",    "____________________");
    row2("Fee Receipt Number",       "____________________", "UTR / Transaction No.", "____________________");

    y += 6;
    sigLine(ML, 55, "Signature of Section Clerk");
    sigLine(PW - MR - 55, 55, "Signature of Cashier");

    // ── FOOTER ───────────────────────────────────────────────
    const lastPage = doc.getNumberOfPages();
    for (let pg = 1; pg <= lastPage; pg++) {
      doc.setPage(pg);
      hline(PH - 18, C.lightgrey, 0.2);
      hline(PH - 17.5, C.black, 0.4);
      font("normal", 6.5, C.midgrey);
      doc.text(
        "Government College of Engineering, Kolhapur  ·  Admission Cell  ·  Academic Year 2025–26",
        PW / 2, PH - 13, { align: "center" }
      );
      font("normal", 6, [180, 180, 180]);
      doc.text("System generated document — valid subject to college verification.", PW / 2, PH - 9, { align: "center" });
    }

    // ── SAVE ─────────────────────────────────────────────────
    const filename = `Admission_Form_${D.prn_number !== "N/A" ? D.prn_number : D.full_name.replace(/\s+/g, "_")}.pdf`;
    doc.save(filename);
  });
});
