document.addEventListener("DOMContentLoaded", function () {
  // Filter tabs functionality
  const filterTabs = document.querySelectorAll(".filter-tab");
  const notificationItems = document.querySelectorAll(".notification-item");

  filterTabs.forEach((tab) => {
    tab.addEventListener("click", function () {
      // Remove active class from all tabs
      filterTabs.forEach((t) => t.classList.remove("active"));

      // Add active class to clicked tab
      this.classList.add("active");

      const filter = this.getAttribute("data-filter");

      // Show/hide notifications based on filter
      notificationItems.forEach((item) => {
        if (filter === "all") {
          item.style.display = "flex";
        } else if (filter === "unread") {
          item.style.display = item.classList.contains("unread")
            ? "flex"
            : "none";
        } else {
          const itemType = item.getAttribute("data-type");
          item.style.display = itemType === filter ? "flex" : "none";
        }
      });

      // Check if any notifications are visible in each date group
      document.querySelectorAll(".notification-date-group").forEach((group) => {
        const visibleItems = group.querySelectorAll(
          ".notification-item[style='display: flex']"
        ).length;
        group.style.display = visibleItems > 0 ? "block" : "none";
      });

      // Show notification
      showNotification(`Showing ${filter} notifications`);
    });
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
  const markAllReadBtn = document.getElementById("mark-all-read-btn");
  markAllReadBtn.addEventListener("click", function () {
    const unreadItems = document.querySelectorAll(".notification-item.unread");
    unreadItems.forEach((item) => {
      item.classList.remove("unread");
      const readBtn = item.querySelector(".mark-read-btn");
      readBtn.innerHTML = '<i class="far fa-circle"></i>';
    });

    // Hide the badge
    const notificationBadge = document.querySelector(".notification-badge");
    notificationBadge.classList.remove("show");

    showNotification("All notifications marked as read");
  });

  // Settings button
  const settingsBtn = document.getElementById("settings-btn");
  settingsBtn.addEventListener("click", function () {
    window.location.href = "notifications.html";
  });

  // Pagination
  const pageNumbers = document.querySelectorAll(".page-number");
  const prevBtn = document.querySelector(".prev-page");
  const nextBtn = document.querySelector(".next-page");

  pageNumbers.forEach((btn) => {
    btn.addEventListener("click", function () {
      pageNumbers.forEach((p) => p.classList.remove("active"));
      this.classList.add("active");

      const page = this.textContent;

      // Enable/disable prev/next buttons
      prevBtn.disabled = page === "1";
      nextBtn.disabled = page === "3";

      // In a real app, this would load the appropriate page of notifications
      showNotification(`Navigated to page ${page}`);
    });
  });

  prevBtn.addEventListener("click", function () {
    const activePage = document.querySelector(".page-number.active");
    const currentPage = parseInt(activePage.textContent);

    if (currentPage > 1) {
      document.querySelectorAll(".page-number").forEach((p) => {
        p.classList.remove("active");
        if (p.textContent == currentPage - 1) {
          p.classList.add("active");
          // Enable/disable prev/next buttons
          prevBtn.disabled = p.textContent === "1";
          nextBtn.disabled = false;
        }
      });

      // In a real app, this would load the previous page
      showNotification(`Navigated to page ${currentPage - 1}`);
    }
  });

  nextBtn.addEventListener("click", function () {
    const activePage = document.querySelector(".page-number.active");
    const currentPage = parseInt(activePage.textContent);
    const maxPage = 3; // Hardcoded for demo

    if (currentPage < maxPage) {
      document.querySelectorAll(".page-number").forEach((p) => {
        p.classList.remove("active");
        if (p.textContent == currentPage + 1) {
          p.classList.add("active");
          // Enable/disable prev/next buttons
          prevBtn.disabled = false;
          nextBtn.disabled = p.textContent === "3";
        }
      });

      // In a real app, this would load the next page
      showNotification(`Navigated to page ${currentPage + 1}`);
    }
  });

  // Add click event to notification items to show detailed view
  notificationItems.forEach((item) => {
    item.addEventListener("click", function () {
      // In a real app, this would open the relevant page or show more details
      const notificationText = this.querySelector(
        ".notification-content p"
      ).textContent;

      // Mark as read when clicked
      if (this.classList.contains("unread")) {
        this.classList.remove("unread");
        const readBtn = this.querySelector(".mark-read-btn");
        readBtn.innerHTML = '<i class="far fa-circle"></i>';
        updateUnreadBadge();
      }

      showNotification("Viewing: " + notificationText.substring(0, 30) + "...");
    });
  });

  // Function to check if there are unread notifications and update badge
  function updateUnreadBadge() {
    const unreadItems = document.querySelectorAll(".notification-item.unread");
    const notificationBadge = document.querySelector(".notification-badge");

    if (unreadItems.length > 0) {
      notificationBadge.classList.add("show");
    } else {
      notificationBadge.classList.remove("show");
    }
  }
});

// Show notification toast
function showNotification(message) {
  const notification = document.getElementById("notification");
  notification.textContent = message;
  notification.className = "notification-toast";

  setTimeout(() => {
    notification.classList.add("show");
  }, 10);

  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => {
      notification.textContent = "";
    }, 300);
  }, 3000);
}
