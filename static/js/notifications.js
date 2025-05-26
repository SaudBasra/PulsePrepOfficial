document.addEventListener("DOMContentLoaded", function () {
  // Show notification badge if there are unread notifications
  const hasUnreadNotifications = true; // Set to true for demo purposes
  const notificationBadge = document.querySelector(".notification-badge");

  if (hasUnreadNotifications) {
    notificationBadge.classList.add("show");
  }

  // Toggle notification dropdown
  const notificationBell = document.querySelector(".notification-container");
  const notificationDropdown = document.getElementById("notification-dropdown");

  notificationBell.addEventListener("click", function (e) {
    e.stopPropagation();
    notificationDropdown.classList.toggle("show");

    // Remove the badge when opening the dropdown
    if (notificationDropdown.classList.contains("show")) {
      notificationBadge.classList.remove("show");
    }
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", function (e) {
    if (
      !notificationDropdown.contains(e.target) &&
      !notificationBell.contains(e.target)
    ) {
      notificationDropdown.classList.remove("show");
    }
  });

  // Mark individual notifications as read
  const markReadButtons = document.querySelectorAll(".mark-read-btn");
  markReadButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.stopPropagation();
      const notificationItem = this.closest(".notification-item");

      // Toggle between read and unread states
      if (notificationItem.classList.contains("unread")) {
        notificationItem.classList.remove("unread");
        this.innerHTML = '<i class="far fa-circle"></i>';
      } else {
        notificationItem.classList.add("unread");
        this.innerHTML = '<i class="fas fa-circle"></i>';
      }

      // Check if there are any unread notifications left
      updateUnreadBadge();
    });
  });

  // Mark all as read
  const markAllReadBtn = document.querySelector(".mark-all-read");
  markAllReadBtn.addEventListener("click", function () {
    const unreadItems = document.querySelectorAll(".notification-item.unread");
    unreadItems.forEach((item) => {
      item.classList.remove("unread");
      const readBtn = item.querySelector(".mark-read-btn");
      readBtn.innerHTML = '<i class="far fa-circle"></i>';
    });

    // Hide the badge
    notificationBadge.classList.remove("show");
  });

  // Open notification settings page
  const notificationSettingsBtn = document.querySelector(
    ".notification-settings-btn"
  );
  notificationSettingsBtn.addEventListener("click", function () {
    window.location.href = "notifications.html";
  });

  // Function to check if there are unread notifications and update badge
  function updateUnreadBadge() {
    const unreadItems = document.querySelectorAll(".notification-item.unread");
    if (unreadItems.length > 0) {
      notificationBadge.classList.add("show");
    } else {
      notificationBadge.classList.remove("show");
    }
  }

  // Save notification settings
  const saveSettingsBtn = document.querySelector(".save-settings-btn");
  if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener("click", function () {
      // In a real app, this would save the settings to a database
      showNotification("Notification settings saved successfully");
    });
  }

  // Add click event to notification items to show detailed view
  const notificationItems = document.querySelectorAll(".notification-item");
  notificationItems.forEach((item) => {
    item.addEventListener("click", function () {
      // In a real app, this would open the relevant page or show more details
      const notificationText = this.querySelector(
        ".notification-content p"
      ).textContent;
      showNotification("Viewing: " + notificationText.substring(0, 30) + "...");
    });
  });
});

// Show notification toast
function showNotification(message) {
  const notification = document.getElementById("notification");
  notification.textContent = message;
  notification.className = "notification-toast";

  setTimeout(() => {
    notification.classList.add("show");
  }, 1000);

  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => {
      notification.textContent = "";
    }, 300);
  }, 3000);
}
