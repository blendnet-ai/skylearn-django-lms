"use strict";
import { auth } from "./firebase.js";

auth.onAuthStateChanged((user) => {
  const nextUrl = document
    .getElementById("next-url")
    .getAttribute("data-next-url");

  if (user) {
    const expirationDate = new Date();
    expirationDate.setFullYear(expirationDate.getFullYear() + 10); // Set expiration to 10 years from now

    user
      .getIdToken()
      .then(
        (token) =>
          (document.cookie = `firebaseToken=${token}; path=/; max-age=${expirationDate.toUTCString()}; SameSite=Strict; Secure`)
      );

    window.location.href = nextUrl;
  }
});
