"use strict";
import { auth } from "./firebase.js";

auth.onAuthStateChanged((user) => {
  const nextUrl = document
    .getElementById("next-url")
    .getAttribute("data-next-url");

  if (user) {
    user
      .getIdToken()
      .then(
        (token) =>
          (document.cookie = `firebaseToken=${token}; path=/; max-age=3600; SameSite=Strict; Secure`)
      );

    window.location.href = nextUrl;
  }
});
