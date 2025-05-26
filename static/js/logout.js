document.addEventListener("DOMContentLoaded", function () {
  // Show a welcome back message if the user clicks "Login Again"
  const loginButton = document.querySelector(".login-button");
  if (loginButton) {
    loginButton.addEventListener("click", function (e) {
      // Store a flag in localStorage to show welcome message on login page
      localStorage.setItem("showWelcomeBack", "true");
    });
  }

  // Optional: Set a timeout to automatically redirect to home page
  // Uncomment this code if you want this functionality
  /*
  const redirectDelay = 60; // seconds
  let countdown = redirectDelay;

  const timer = setInterval(function() {
    countdown--;

    if (countdown <= 0) {
      clearInterval(timer);
      window.location.href = 'index.html';
    }
  }, 1000);
  */

  // Optional: Add animation for the logout confirmation
  const logoutIcon = document.querySelector(".logout-icon i");
  if (logoutIcon) {
    setTimeout(function () {
      logoutIcon.classList.add("animated");
    }, 300);
  }

  // Optional: Display when the logout happened
  const logoutTimeElement = document.createElement("div");
  logoutTimeElement.className = "logout-time";

  const now = new Date();
  const options = {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "numeric",
    year: "numeric",
  };
  const timeString = now.toLocaleDateString("en-US", options);

  logoutTimeElement.textContent = `Logged out at ${timeString}`;
  logoutTimeElement.style.fontSize = "14px";
  logoutTimeElement.style.color = "#6b7280";
  logoutTimeElement.style.marginTop = "10px";

  const logoutContent = document.querySelector(".logout-content p");
  if (logoutContent) {
    logoutContent.after(logoutTimeElement);
  }
});
