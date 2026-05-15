/* auth.js — GCE Admission Portal | Signup client-side validation */

document.addEventListener("DOMContentLoaded", () => {

  const signupForm = document.querySelector("form[action='/signup']");
  if (!signupForm) return;

  const usernameInput = signupForm.querySelector("input[name='username']");
  const passwordInput = signupForm.querySelector("input[name='password']");
  const confirmInput  = signupForm.querySelector("input[name='confirm_password']");

  function showError(input, msg) {
    let el = input.parentElement.querySelector(".field-error");
    if (!el) {
      el = document.createElement("p");
      el.className = "field-error";
      el.style.cssText = "color:#b91c1c;font-size:12px;margin-top:4px;";
      input.parentElement.appendChild(el);
    }
    el.textContent = msg;
    el.style.display = msg ? "block" : "none";
  }

  function clearError(input) { showError(input, ""); }

  passwordInput.addEventListener("input", () => {
    if (passwordInput.value.length > 0 && passwordInput.value.length < 8) {
      showError(passwordInput, "Password must be at least 8 characters.");
    } else {
      clearError(passwordInput);
    }
    if (confirmInput.value && passwordInput.value !== confirmInput.value) {
      showError(confirmInput, "Passwords do not match.");
    } else if (confirmInput.value) {
      clearError(confirmInput);
    }
  });

  confirmInput.addEventListener("input", () => {
    if (confirmInput.value && passwordInput.value !== confirmInput.value) {
      showError(confirmInput, "Passwords do not match.");
    } else {
      clearError(confirmInput);
    }
  });

  signupForm.addEventListener("submit", e => {
    let valid = true;

    if (!/^[a-zA-Z0-9_]{3,50}$/.test(usernameInput.value.trim())) {
      showError(usernameInput, "Username: 3–50 chars, letters/numbers/underscores only.");
      valid = false;
    } else {
      clearError(usernameInput);
    }

    if (passwordInput.value.length < 8) {
      showError(passwordInput, "Password must be at least 8 characters.");
      valid = false;
    } else {
      clearError(passwordInput);
    }

    if (passwordInput.value !== confirmInput.value) {
      showError(confirmInput, "Passwords do not match.");
      valid = false;
    } else {
      clearError(confirmInput);
    }

    if (!valid) e.preventDefault();
  });

});
