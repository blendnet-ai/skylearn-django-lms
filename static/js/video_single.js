import {
  getAnalytics,
  logEvent,
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-analytics.js";

const firebaseConfig = window.firebaseConfig;

const analytics = getAnalytics();

const randomId =
  Math.random().toString(36).substring(2, 15) +
  Math.random().toString(36).substring(2, 15);

// Log page enter event
const pageEnterTime = Date.now();
logEvent(analytics, "page_enter", {
  page_name: "TestPageName",
  enter_time: pageEnterTime,
  session_id: randomId,
  user_id: "123",
});
// Generate a random ID

console.log("page_enter", pageEnterTime);

// Log page exit event
window.addEventListener("beforeunload", () => {
  const pageExitTime = Date.now();
  const timeSpent = (pageExitTime - pageEnterTime) / 1000;
  console.log("page_exit", timeSpent);
  localStorage.setItem("time_spent", timeSpent);
  logEvent(analytics, "page_exit", {
    page_name: "TestPageName",
    exit_time: pageExitTime,
    time_spent: timeSpent, // In seconds
    session_id: randomId,
    user_id: "123",
  });
});
