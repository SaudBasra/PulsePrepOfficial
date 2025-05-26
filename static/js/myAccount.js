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

  // Profile form submission
  const profileForm = document.querySelector(".profile-form");
  if (profileForm) {
    profileForm.addEventListener("submit", function (e) {
      e.preventDefault();

      // Show success message (would typically save to server)
      showToast("Profile updated successfully!", "success");
    });
  }

  // Security form submission
  const securityForm = document.querySelector(".security-form");
  if (securityForm) {
    securityForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const newPassword = document.getElementById("new-password").value;
      const confirmPassword = document.getElementById("confirm-password").value;

      if (newPassword !== confirmPassword) {
        showToast("Passwords do not match!", "error");
        return;
      }

      // Would typically validate and update password on server
      showToast("Password updated successfully!", "success");
      this.reset();
    });
  }

  // Preferences save button
  const savePreferencesBtn = document.querySelector(
    "#preferences .action-button.primary"
  );
  if (savePreferencesBtn) {
    savePreferencesBtn.addEventListener("click", function () {
      showToast("Preferences saved successfully!", "success");
    });
  }

  // Two-factor authentication buttons
  const twoFactorButtons = document.querySelectorAll(
    ".two-factor-actions .action-button"
  );
  twoFactorButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const action = this.textContent.trim();
      showToast(`${action} action initiated`, "info");
    });
  });

  // Session logout buttons
  const logoutButtons = document.querySelectorAll(".link-button.danger");
  logoutButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const row = this.closest("tr");

      // Animate removal
      row.style.backgroundColor = "#ffebee";
      setTimeout(() => {
        row.style.opacity = "0";
        row.style.height = "0";
        row.style.transition = "opacity 0.5s, height 0.5s";

        setTimeout(() => {
          row.remove();
          showToast("Device logged out successfully", "success");
        }, 500);
      }, 100);
    });
  });

  // Logout all devices button
  const logoutAllBtn = document.querySelector(
    ".sessions-actions .action-button"
  );
  if (logoutAllBtn) {
    logoutAllBtn.addEventListener("click", function () {
      const sessionRows = document.querySelectorAll(
        ".sessions-table tbody tr:not(.current-session)"
      );

      if (sessionRows.length === 0) {
        showToast("No other active sessions", "info");
        return;
      }

      sessionRows.forEach((row) => {
        row.style.backgroundColor = "#ffebee";
        setTimeout(() => {
          row.style.opacity = "0";
          row.style.height = "0";
          row.style.transition = "opacity 0.5s, height 0.5s";
        }, 100);
      });

      setTimeout(() => {
        sessionRows.forEach((row) => row.remove());
        showToast("All other devices logged out successfully", "success");
      }, 600);
    });
  }

  // Admin card buttons
  const adminCardButtons = document.querySelectorAll(
    ".admin-card .action-button"
  );
  adminCardButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const action = this.textContent.trim();
      showToast(`Navigating to ${action}...`, "info");
    });
  });

  // API key actions
  const apiKeyButtons = document.querySelectorAll(".api-table .icon-button");
  apiKeyButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const action = this.querySelector("i").className;
      const row = this.closest("tr");
      const keyName = row.cells[0].textContent;

      if (action.includes("eye")) {
        showToast(`Viewing API key: ${keyName}`, "info");
      } else if (action.includes("edit")) {
        showToast(`Editing API key: ${keyName}`, "info");
      } else if (action.includes("trash")) {
        if (confirm(`Are you sure you want to delete API key "${keyName}"?`)) {
          row.style.backgroundColor = "#ffebee";
          setTimeout(() => {
            row.style.opacity = "0";
            row.style.height = "0";
            row.style.transition = "opacity 0.5s, height 0.5s";

            setTimeout(() => {
              row.remove();
              showToast(`API key deleted: ${keyName}`, "success");
            }, 500);
          }, 100);
        }
      }
    });
  });

  // Generate new API key button
  const generateApiBtn = document.querySelector(".api-info .action-button");
  if (generateApiBtn) {
    generateApiBtn.addEventListener("click", function () {
      showToast("New API key generated", "success");
    });
  }

  // Password strength indicator
  const newPasswordInput = document.getElementById("new-password");
  if (newPasswordInput) {
    newPasswordInput.addEventListener("input", function () {
      const password = this.value;
      const strengthBar = document.querySelector(".strength-level");
      const strengthText = document.querySelector(".password-strength span");

      let strength = 0;

      // Length check
      if (password.length >= 8) strength += 25;

      // Contains lowercase
      if (/[a-z]/.test(password)) strength += 25;

      // Contains uppercase
      if (/[A-Z]/.test(password)) strength += 25;

      // Contains number or special char
      if (/[0-9!@#$%^&*]/.test(password)) strength += 25;

      strengthBar.style.width = `${strength}%`;

      if (strength <= 25) {
        strengthBar.style.backgroundColor = "#dc3545";
        strengthText.textContent = "Weak";
      } else if (strength <= 50) {
        strengthBar.style.backgroundColor = "#ffc107";
        strengthText.textContent = "Fair";
      } else if (strength <= 75) {
        strengthBar.style.backgroundColor = "#28a745";
        strengthText.textContent = "Good";
      } else {
        strengthBar.style.backgroundColor = "#4caf50";
        strengthText.textContent = "Strong";
      }
    });
  }

  // Toast notification system
  function showToast(message, type = "info") {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector(".toast-container");
    if (!toastContainer) {
      toastContainer = document.createElement("div");
      toastContainer.className = "toast-container";
      document.body.appendChild(toastContainer);

      // Add style for toast container
      const style = document.createElement("style");
      style.textContent = `
        .toast-container {
          position: fixed;
          bottom: 20px;
          right: 20px;
          z-index: 9999;
        }

        .toast {
          min-width: 250px;
          margin-top: 10px;
          padding: 15px 20px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          transform: translateX(120%);
          transition: transform 0.3s ease;
          background-color: white;
        }

        .toast.show {
          transform: translateX(0);
        }

        .toast.success {
          border-left: 4px solid #4caf50;
        }

        .toast.error {
          border-left: 4px solid #f44336;
        }

        .toast.info {
          border-left: 4px solid #2196f3;
        }

        .toast.warning {
          border-left: 4px solid #ff9800;
        }

        .toast-close {
          background: none;
          border: none;
          cursor: pointer;
          font-size: 16px;
          color: #999;
          margin-left: 10px;
        }

        @media (max-width: 480px) {
          .toast-container {
            left: 20px;
            right: 20px;
            bottom: 20px;
          }

          .toast {
            min-width: unset;
            width: 100%;
          }
        }
      `;
      document.head.appendChild(style);
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
