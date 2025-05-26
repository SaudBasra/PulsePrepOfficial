document.addEventListener("DOMContentLoaded", function () {
  // Add an overlay div for mobile sidebar
  const overlay = document.createElement("div");
  overlay.className = "sidebar-overlay";
  document.body.appendChild(overlay);

  // Get elements
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");

  // Hamburger menu toggle
  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function (e) {
      e.preventDefault();
      sidebar.classList.toggle("active");
      overlay.classList.toggle("active");
      document.body.style.overflow = sidebar.classList.contains("active")
        ? "hidden"
        : "";
    });
  }

  // Close sidebar when clicking overlay
  overlay.addEventListener("click", function () {
    sidebar.classList.remove("active");
    overlay.classList.remove("active");
    document.body.style.overflow = "";
  });

  // Handle sidebar links on mobile - close sidebar when clicked
  const navLinks = document.querySelectorAll(".sidebar .nav-item");
  navLinks.forEach((link) => {
    link.addEventListener("click", function () {
      if (window.innerWidth <= 768) {
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
        document.body.style.overflow = "";
      }
    });
  });

  // Handle media query changes
  const mediaQuery = window.matchMedia("(max-width: 768px)");

  function handleMediaChange(e) {
    if (!e.matches) {
      // Reset sidebar state when returning to desktop
      sidebar.classList.remove("active");
      overlay.classList.remove("active");
      document.body.style.overflow = "";
    }
  }

  mediaQuery.addEventListener("change", handleMediaChange);
  handleMediaChange(mediaQuery);

  // Tab switching
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabContents = document.querySelectorAll(".tab-content");

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      // Remove active class from all buttons
      tabButtons.forEach((btn) => btn.classList.remove("active"));

      // Add active class to clicked button
      button.classList.add("active");

      // Hide all tab contents
      tabContents.forEach((content) => (content.style.display = "none"));

      // Show selected tab content
      const tabId = button.getAttribute("data-tab");
      document.getElementById(tabId).style.display = "block";
    });
  });

  // Color pickers
  const colorPickers = document.querySelectorAll(".color-picker");
  colorPickers.forEach((picker) => {
    picker.addEventListener("input", function () {
      // Update color value display next to the picker
      const colorValue = this.nextElementSibling;
      if (colorValue && colorValue.classList.contains("color-value")) {
        colorValue.textContent = this.value;
      }
    });
  });

  // Save button actions
  const saveButtons = document.querySelectorAll(".action-button.primary");
  saveButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Get the parent tab id to customize the message
      const tabContent = this.closest(".tab-content");
      let settingType = "settings";

      if (tabContent) {
        const tabId = tabContent.id;
        settingType = tabId.charAt(0).toUpperCase() + tabId.slice(1);
      }

      showToast(`${settingType} settings saved successfully!`, "success");
    });
  });

  // Reset to defaults buttons
  const resetButtons = document.querySelectorAll(".action-button.secondary");
  resetButtons.forEach((button) => {
    if (button.textContent.includes("Reset to Defaults")) {
      button.addEventListener("click", function () {
        if (
          confirm(
            "Are you sure you want to reset these settings to default values?"
          )
        ) {
          const tabContent = this.closest(".tab-content");
          let settingType = "settings";

          if (tabContent) {
            const tabId = tabContent.id;
            settingType = tabId.charAt(0).toUpperCase() + tabId.slice(1);
          }

          showToast(`${settingType} settings reset to defaults`, "info");
        }
      });
    }
  });

  // Danger zone buttons
  const dangerButtons = document.querySelectorAll(".danger-button");
  dangerButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const action = this.textContent.trim();
      if (
        confirm(
          `Are you sure you want to ${action.toLowerCase()}? This action cannot be undone.`
        )
      ) {
        showToast(`${action} completed`, "warning");
      }
    });
  });

  // Integration buttons
  const integrationButtons = document.querySelectorAll(
    ".integration-actions .action-button"
  );
  integrationButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const action = button.textContent.trim();
      const integrationItem = this.closest(".integration-item");
      const integrationName = integrationItem.querySelector("h4").textContent;

      if (action === "Connect") {
        // Simulate connecting
        showToast(`Connecting to ${integrationName}...`, "info");

        // After "connecting" (simulate with timeout)
        setTimeout(() => {
          integrationItem.classList.add("connected");
          const statusSpan = integrationItem.querySelector(
            ".integration-status"
          );
          statusSpan.textContent = "Connected";
          statusSpan.classList.remove("not-connected");

          this.textContent = "Disconnect";
          this.classList.remove("primary");
          this.classList.add("secondary");

          const infoP = integrationItem.querySelector(".integration-info p");
          const today = new Date();
          const formattedDate = `${today.toLocaleString("default", {
            month: "short",
          })} ${today.getDate()}, ${today.getFullYear()}`;
          infoP.textContent = `Connected on ${formattedDate}`;

          showToast(`Successfully connected to ${integrationName}`, "success");
        }, 1500);
      } else if (action === "Disconnect") {
        if (
          confirm(
            `Are you sure you want to disconnect from ${integrationName}?`
          )
        ) {
          // Simulate disconnecting
          showToast(`Disconnecting from ${integrationName}...`, "info");

          // After "disconnecting" (simulate with timeout)
          setTimeout(() => {
            integrationItem.classList.remove("connected");
            const statusSpan = integrationItem.querySelector(
              ".integration-status"
            );
            statusSpan.textContent = "Not Connected";
            statusSpan.classList.add("not-connected");

            this.textContent = "Connect";
            this.classList.remove("secondary");
            this.classList.add("primary");

            const infoP = integrationItem.querySelector(".integration-info p");
            if (integrationName === "Google Workspace") {
              infoP.textContent = "Cloud-based productivity suite";
            } else if (integrationName === "Stripe Payments") {
              infoP.textContent = "Online payment processing";
            }

            showToast(
              `Successfully disconnected from ${integrationName}`,
              "success"
            );
          }, 1000);
        }
      }
    });
  });

  // Add notification badges to sidebar and header
  function addNotificationBadges() {
    // Add red notification badge to the notification menu item in sidebar
    const notificationMenuItem = document.querySelector(
      ".sidebar .nav-item:nth-child(8)"
    );
    if (notificationMenuItem) {
      const badge = notificationMenuItem.querySelector(
        ".notification-badge-sidebar"
      );
      if (badge) {
        badge.style.display = "block";
      }
    }

    // Add red notification indicator to the bell icon in header
    const bellIcon = document.querySelector(".notification-icon-wrapper");
    if (bellIcon) {
      // Create notification indicator if it doesn't exist
      if (!bellIcon.querySelector(".bell-notification-badge")) {
        const notificationBadge = document.createElement("span");
        notificationBadge.className = "bell-notification-badge";
        bellIcon.appendChild(notificationBadge);
      }
    }
  }

  // Initialize notification badges
  addNotificationBadges();

  // Toast notification system
  function showToast(message, type = "info") {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector(".toast-container");
    if (!toastContainer) {
      toastContainer = document.createElement("div");
      toastContainer.className = "toast-container";
      document.body.appendChild(toastContainer);
    }

    // Create toast
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span>${message}</span>
      <button class="toast-close">&times;</button>
    `;

    // Add to container
    toastContainer.appendChild(toast);

    // Show toast (with delay for animation)
    setTimeout(() => {
      toast.classList.add("show");
    }, 10);

    // Close button
    const closeBtn = toast.querySelector(".toast-close");
    closeBtn.addEventListener("click", function () {
      toast.classList.remove("show");
      setTimeout(() => {
        toast.remove();
      }, 300);
    });

    // Auto remove after 5 seconds
    setTimeout(() => {
      if (toast.parentNode) {
        toast.classList.remove("show");
        setTimeout(() => {
          if (toast.parentNode) {
            toast.remove();
          }
        }, 300);
      }
    }, 5000);
  }
});
