document.addEventListener("DOMContentLoaded", function () {
  // Add an overlay div for mobile sidebar
  const overlay = document.createElement("div");
  overlay.className = "sidebar-overlay";
  document.body.appendChild(overlay);

  // Get elements
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");

  // Hamburger menu toggle with debug logging
  if (sidebarToggle) {
    console.log("Sidebar toggle button found");

    sidebarToggle.addEventListener("click", function (e) {
      console.log("Sidebar toggle clicked");
      e.preventDefault();
      sidebar.classList.toggle("active");
      overlay.classList.toggle("active");
      document.body.style.overflow = sidebar.classList.contains("active")
        ? "hidden"
        : "";
    });
  } else {
    console.error("Sidebar toggle button not found");
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

  // Create test button in manage tab
  const createTestBtn = document.querySelector(
    ".test-list-header .action-button"
  );
  if (createTestBtn) {
    createTestBtn.addEventListener("click", () => {
      // Reset form if it exists
      const testForm = document.querySelector(".mock-test-form");
      if (testForm) {
        testForm.reset();
        document.querySelector(
          ".test-form-section .section-header h2"
        ).textContent = "Create New Mock Test";
        document.querySelector(".form-actions .primary").textContent =
          "Create Test";
      }

      // Switch to create test tab
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      document
        .querySelector('[data-tab="create-test"]')
        .classList.add("active");

      tabContents.forEach((content) => (content.style.display = "none"));
      document.getElementById("create-test").style.display = "block";

      // Scroll to top
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  // Form cancel button
  const cancelBtn = document.querySelector(".form-actions .secondary");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => {
      // Switch to manage tests tab
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      document
        .querySelector('[data-tab="manage-tests"]')
        .classList.add("active");

      tabContents.forEach((content) => (content.style.display = "none"));
      document.getElementById("manage-tests").style.display = "block";
    });
  }

  // Form submission
  const testForm = document.querySelector(".mock-test-form");
  if (testForm) {
    testForm.addEventListener("submit", function (e) {
      e.preventDefault();

      // Here you would normally send the form data to the server
      // For now, just show a success message
      const isEditing = document
        .querySelector(".form-actions .primary")
        .textContent.includes("Update");
      showToast(
        isEditing ? "Test updated successfully!" : "Test created successfully!",
        "success"
      );

      // Reset form
      testForm.reset();

      // Switch back to the manage tests tab
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      document
        .querySelector('[data-tab="manage-tests"]')
        .classList.add("active");

      tabContents.forEach((content) => (content.style.display = "none"));
      document.getElementById("manage-tests").style.display = "block";
    });
  }

  // Dynamic dependent dropdowns
  const degreeSelect = document.getElementById("test-degree");
  const yearSelect = document.getElementById("test-year");
  const moduleSelect = document.getElementById("test-module");
  const subjectSelect = document.getElementById("test-subject");

  if (degreeSelect && yearSelect && moduleSelect && subjectSelect) {
    degreeSelect.addEventListener("change", updateModules);
    yearSelect.addEventListener("change", updateModules);
    moduleSelect.addEventListener("change", updateSubjects);
  }

  function updateModules() {
    // This would typically fetch from server
    // For demo, just reset the options
    moduleSelect.innerHTML = '<option value="">Select Module</option>';

    if (degreeSelect.value === "mbbs") {
      moduleSelect.innerHTML += `
        <option value="anatomy">Anatomy</option>
        <option value="physiology">Physiology</option>
        <option value="biochemistry">Biochemistry</option>
        <option value="pathology">Pathology</option>
      `;
    } else if (degreeSelect.value === "bds") {
      moduleSelect.innerHTML += `
        <option value="oral-anatomy">Oral Anatomy</option>
        <option value="dental-materials">Dental Materials</option>
        <option value="oral-pathology">Oral Pathology</option>
      `;
    }

    // Reset subjects too
    updateSubjects();
  }

  function updateSubjects() {
    // This would typically fetch from server
    // For demo, just reset the options
    subjectSelect.innerHTML = '<option value="">Select Subject</option>';

    if (moduleSelect.value === "anatomy") {
      subjectSelect.innerHTML += `
        <option value="gross-anatomy">Gross Anatomy</option>
        <option value="histology">Histology</option>
        <option value="embryology">Embryology</option>
        <option value="neuroanatomy">Neuroanatomy</option>
      `;
    } else if (moduleSelect.value === "physiology") {
      subjectSelect.innerHTML += `
        <option value="general-physiology">General Physiology</option>
        <option value="neurophysiology">Neurophysiology</option>
        <option value="cardiovascular">Cardiovascular Physiology</option>
      `;
    }
  }

  // ============ IMPLEMENT ACTION ICONS FUNCTIONALITY ============

  // Edit buttons
  const editButtons = document.querySelectorAll(".icon-button .fa-edit");
  editButtons.forEach((button) => {
    button.parentElement.addEventListener("click", function (e) {
      e.preventDefault();
      const row = this.closest("tr");
      const testTitle = row.cells[0].textContent;

      // Populate form with test data (in real implementation, you'd fetch the complete data)
      document.getElementById("test-title").value = testTitle;

      // Set other form values based on the row data
      const degree = row.cells[1].textContent;
      document.getElementById("test-degree").value = degree.toLowerCase();

      document.getElementById("total-questions").value =
        row.cells[2].textContent;

      // Switch to edit tab
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      document
        .querySelector('[data-tab="create-test"]')
        .classList.add("active");

      tabContents.forEach((content) => (content.style.display = "none"));
      document.getElementById("create-test").style.display = "block";

      // Update form title
      document.querySelector(
        ".test-form-section .section-header h2"
      ).textContent = "Edit Mock Test";
      document.querySelector(".form-actions .primary").textContent =
        "Update Test";

      // Scroll to top
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });

  // Duplicate buttons
  const duplicateButtons = document.querySelectorAll(".icon-button .fa-copy");
  duplicateButtons.forEach((button) => {
    button.parentElement.addEventListener("click", function (e) {
      e.preventDefault();
      const row = this.closest("tr");
      const testTitle = row.cells[0].textContent + " (Copy)";

      // Populate form with test data
      document.getElementById("test-title").value = testTitle;

      // Set other form values based on the row data
      const degree = row.cells[1].textContent;
      document.getElementById("test-degree").value = degree.toLowerCase();

      document.getElementById("total-questions").value =
        row.cells[2].textContent;

      // Switch to create tab
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      document
        .querySelector('[data-tab="create-test"]')
        .classList.add("active");

      tabContents.forEach((content) => (content.style.display = "none"));
      document.getElementById("create-test").style.display = "block";

      // Update form title to show it's a duplicate
      document.querySelector(
        ".test-form-section .section-header h2"
      ).textContent = "Duplicate Mock Test";
      document.querySelector(".form-actions .primary").textContent =
        "Create Duplicate";

      // Scroll to top
      window.scrollTo({ top: 0, behavior: "smooth" });

      showToast("Test duplicated. Modify as needed and save.", "info");
    });
  });

  // Delete buttons
  const deleteButtons = document.querySelectorAll(".icon-button .fa-trash-alt");
  deleteButtons.forEach((button) => {
    button.parentElement.addEventListener("click", function (e) {
      e.preventDefault();
      const row = this.closest("tr");
      const testTitle = row.cells[0].textContent;

      if (confirm(`Are you sure you want to delete "${testTitle}"?`)) {
        // Remove the row with animation
        row.style.backgroundColor = "#ffebee";
        setTimeout(() => {
          row.style.opacity = "0";
          row.style.transform = "translateX(20px)";
          row.style.transition = "opacity 0.5s, transform 0.5s";

          setTimeout(() => {
            row.remove();
            showToast("Test deleted successfully", "success");
          }, 500);
        }, 100);
      }
    });
  });

  // Filter functionality
  const searchInput = document.querySelector(".search-input");
  const filterSelects = document.querySelectorAll(".filter-select");
  const filterButton = document.querySelector(".filter-group .primary");

  if (filterButton) {
    filterButton.addEventListener("click", function () {
      const searchTerm = searchInput ? searchInput.value.toLowerCase() : "";
      const statusFilter = filterSelects[0] ? filterSelects[0].value : "";
      const degreeFilter = filterSelects[1] ? filterSelects[1].value : "";

      // Show apply filter effect
      showToast("Filters applied", "info");

      // This would typically filter data from the server
      // For demo, just show that the filters are working
      console.log(
        `Applied filters: search="${searchTerm}", status="${statusFilter}", degree="${degreeFilter}"`
      );
    });
  }

  // Pagination functionality
  const paginationButtons = document.querySelectorAll(".pagination-button");
  paginationButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Remove active class from all pagination buttons
      paginationButtons.forEach((btn) => btn.classList.remove("active"));

      // Add active class to clicked button
      if (
        !this.querySelector(".fa-chevron-left") &&
        !this.querySelector(".fa-chevron-right")
      ) {
        this.classList.add("active");
      }

      // Here you would typically fetch data for the selected page
      // For demo, just show that pagination is working
      console.log(`Navigated to page: ${this.textContent || "prev/next"}`);
    });
  });

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
