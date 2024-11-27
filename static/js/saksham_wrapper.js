import { auth } from "./firebase.js";
const url = window.location.href;
const newUrl = url.split("sakshm/")[0];
const currentUrl = new URL(window.location.href);
console.log("HERE");
console.log({
  url,
  newUrl,
});

window.addEventListener("message", (event) => {
  if (event.data && event.data.type === "ROUTE_CHANGE") {
    const newRoute = event.data.route;
    const newQueryParams = event.data.queryParams;
    console.log(newQueryParams);

    const currentUrl = new URL(window.location.href);
    currentUrl.pathname =
      currentUrl.pathname.split("sakshm/")[0] + "sakshm" + newRoute;
    currentUrl.search = newQueryParams;

    console.log("Final URL: ", currentUrl.toString());
    window.history.pushState({}, "", currentUrl);
  }
  if (event.data && event.data.type === "ROUTE_HOME") {
    console.log("ROUTE_HOME", event.data);
    const currentUrl = new URL(window.location.href);
    currentUrl.pathname =
      currentUrl.pathname.split("sakshm/")[0] + event.data.route;

    console.log("Final URL: ", currentUrl.toString());
    window.location.href = currentUrl;
  }
  if (event.data && event.data.type === "ROUTE_CHANGE_COURSE") {
    console.log("ROUTE_CHANGE_COURSE", event.data);
    console.log(event.data.courseId);
    const currentUrl = new URL(window.location.href);
    console.log("Current URL: ", currentUrl.pathname);
    currentUrl.pathname = "en/sakshm/" + event.data.route;
    currentUrl.search = `?courseId=${event.data.courseId}`;
    console.log("Final URL: ", currentUrl.toString());
    window.location.href = currentUrl;
  }
});

let isIframeLoaded = false;

// Set up iframe load listener immediately
const iframe = document.getElementById("sakshm-iframe");
if (iframe) {
  iframe.addEventListener("load", () => {
    console.log("Iframe loaded");
    isIframeLoaded = true;
  });
}

auth.onAuthStateChanged((user) => {
  console.log("onAuthStateChanged");
  if (!iframe) {
    return;
  }

  async function sendTokenToIframe() {
    const iframeWindow = iframe.contentWindow;
    const token = await auth.currentUser?.getIdToken();
    iframeWindow.postMessage({ type: "auth-token", token }, "*");
  }

  // If iframe is already loaded, send token immediately
  if (isIframeLoaded) {
    sendTokenToIframe();
  }

  // Also set up listener for future loads
  iframe.addEventListener("load", () => {
    sendTokenToIframe();
  });
});
