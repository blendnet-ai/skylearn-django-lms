import {
  sendSignInLinkToEmail,
  isSignInWithEmailLink,
  signInWithEmailLink,
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

import { auth } from "./firebase.js";

const actionCodeSettings = {
  url: window.location.href,
  handleCodeInApp: true,
};

const messageWrapper = document.getElementById("message-wrapper");
const authContainer = document.getElementById("auth-container");

// Show email input form
function showEmailForm() {
  authContainer.innerHTML = `
      <form id="email-login-form">
          <div class="form-group mb-3">
              <label class="mb-2" for="email">
                  <i class="fas fa-envelope me-2"></i>Email Address
              </label>
              <input type="email" name="email" id="email" class="form-control" required>
          </div>
          
          <button type="submit" class="btn btn-primary" id="login-btn">
              <i class="fas fa-paper-plane"></i>
              <small>Send Login Link</small>
          </button>
      </form>
  `;

  // Add form submit handler
  document
    .getElementById("email-login-form")
    .addEventListener("submit", handleEmailSubmit);
}

// Handle email form submission
async function handleEmailSubmit(e) {
  e.preventDefault();

  const emailInput = document.getElementById("email");
  const loginBtn = document.getElementById("login-btn");

  // Disable button and show loading state
  loginBtn.disabled = true;
  loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

  try {
    await sendSignInLinkToEmail(auth, emailInput.value, actionCodeSettings);

    // Save email for later use
    window.localStorage.setItem("emailForSignIn", emailInput.value);

    messageWrapper.innerHTML = `
          <div class="alert alert-success">
              <i class="fas fa-check-circle"></i> Check your email for the login link!
          </div>
      `;
    emailInput.value = "";
  } catch (error) {
    console.error("Error sending login link:", error);
    messageWrapper.innerHTML = `
          <div class="alert alert-danger">
              <i class="fas fa-exclamation-circle"></i> ${error.message}
          </div>
      `;
  } finally {
    // Reset button state
    loginBtn.disabled = false;
    loginBtn.innerHTML =
      '<i class="fas fa-paper-plane"></i> <small>Send Login Link</small>';
  }
}

// Handle sign-in completion
async function handleSignInCompletion(email) {
  authContainer.innerHTML = `
      <div class="text-center">
          <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
          <p>Completing sign in...</p>
      </div>
  `;

  try {
    const result = await signInWithEmailLink(auth, email, window.location.href);

    // Get the Firebase ID token
    const token = await result.user.getIdToken();

    document.cookie = `firebaseToken=${token}; path=/; max-age=3600; SameSite=Strict; Secure`;

    window.localStorage.setItem("authToken", token);
    window.localStorage.removeItem("emailForSignIn");

    messageWrapper.innerHTML = `
          <div class="alert alert-success">
              <i class="fas fa-check-circle"></i> Successfully signed in!
          </div>
      `;

    // Redirect to dashboard or home page
    setTimeout(() => {
      window.location.href = "/";
    }, 1000);
  } catch (error) {
    console.log("Error signing in:", error);
    messageWrapper.innerHTML = `
          <div class="alert alert-danger">
              <i class="fas fa-exclamation-circle"></i> ${error.message}
          </div>
      `;
    // Show email form again on error
    showEmailForm();
  }
}

// Initialize the page
if (isSignInWithEmailLink(auth, window.location.href)) {
  // This is a sign-in completion
  let email = window.localStorage.getItem("emailForSignIn");
  // let email = "vitika@blendnet.ai";

  if (!email) {
    // If email is not saved, show a form to enter it
    authContainer.innerHTML = `
          <form id="email-confirm-form">
              <p>{% trans 'Please confirm your email to complete sign in:' %}</p>
              <div class="form-group mb-3">
                  <input type="email" name="confirm-email" id="confirm-email" 
                         class="form-control" required>
              </div>
              <button type="submit" class="btn btn-primary">
                  {% trans 'Complete Sign In' %}
              </button>
          </form>
      `;

    document
      .getElementById("email-confirm-form")
      .addEventListener("submit", (e) => {
        e.preventDefault();
        const confirmedEmail = document.getElementById("confirm-email").value;
        handleSignInCompletion(confirmedEmail);
      });
  } else {
    // We have the email, complete the sign-in
    handleSignInCompletion(email);
  }
} else {
  showEmailForm();
}
