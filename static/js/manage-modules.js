document.addEventListener("DOMContentLoaded", function () {
  // Toggle Module Content
  const moduleHeaders = document.querySelectorAll(".module-header");

  moduleHeaders.forEach((header) => {
    header.addEventListener("click", function () {
      const moduleId = this.getAttribute("data-toggle");
      const moduleContent = document.getElementById(moduleId);
      const indicator = this.querySelector(".module-indicator");

      if (moduleContent) {
        if (moduleContent.classList.contains("collapsed")) {
          moduleContent.classList.remove("collapsed");
          indicator.classList.remove("collapsed");
          indicator.classList.add("expanded");
        } else {
          moduleContent.classList.add("collapsed");
          indicator.classList.remove("expanded");
          indicator.classList.add("collapsed");
        }
      }
    });
  });

  // Toggle Subject Content
  const subjectHeaders = document.querySelectorAll(".subject-header");

  subjectHeaders.forEach((header) => {
    header.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevent bubbling to module header

      const subjectId = this.getAttribute("data-toggle");
      const subjectContent = document.getElementById(subjectId);
      const indicator = this.querySelector(".subject-indicator");

      if (subjectContent) {
        if (subjectContent.classList.contains("collapsed")) {
          subjectContent.classList.remove("collapsed");
          indicator.classList.remove("collapsed");
          indicator.classList.add("expanded");
        } else {
          subjectContent.classList.add("collapsed");
          indicator.classList.remove("expanded");
          indicator.classList.add("collapsed");
        }
      }
    });
  });

  // Block actions - Expand All
  const expandButtons = document.querySelectorAll(
    ".block-actions button:nth-child(1)"
  );

  expandButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevent event bubbling
      const block = this.closest(".module-block-card");
      const moduleContents = block.querySelectorAll(".module-content");
      const moduleIndicators = block.querySelectorAll(".module-indicator");
      const subjectContents = block.querySelectorAll(".subject-content");
      const subjectIndicators = block.querySelectorAll(".subject-indicator");

      moduleContents.forEach((content) =>
        content.classList.remove("collapsed")
      );
      moduleIndicators.forEach((indicator) => {
        indicator.classList.remove("collapsed");
        indicator.classList.add("expanded");
      });

      subjectContents.forEach((content) =>
        content.classList.remove("collapsed")
      );
      subjectIndicators.forEach((indicator) => {
        indicator.classList.remove("collapsed");
        indicator.classList.add("expanded");
      });
    });
  });

  // Block actions - Collapse All
  const collapseButtons = document.querySelectorAll(
    ".block-actions button:nth-child(2)"
  );

  collapseButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevent event bubbling
      const block = this.closest(".module-block-card");
      const moduleContents = block.querySelectorAll(".module-content");
      const moduleIndicators = block.querySelectorAll(".module-indicator");
      const subjectContents = block.querySelectorAll(".subject-content");
      const subjectIndicators = block.querySelectorAll(".subject-indicator");

      moduleContents.forEach((content) => content.classList.add("collapsed"));
      moduleIndicators.forEach((indicator) => {
        indicator.classList.remove("expanded");
        indicator.classList.add("collapsed");
      });

      subjectContents.forEach((content) => content.classList.add("collapsed"));
      subjectIndicators.forEach((indicator) => {
        indicator.classList.remove("expanded");
        indicator.classList.add("collapsed");
      });
    });
  });

  // Edit Block Button Functionality
  const editBlockBtns = document.querySelectorAll(
    ".block-actions button:nth-child(3)"
  );

  editBlockBtns.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevent event bubbling
      const blockTitle =
        this.closest(".block-header").querySelector(
          ".block-title h2"
        ).textContent;
      openEditBlockModal(blockTitle);
    });
  });

  // Add Module to Block Button
  const addModuleToBlockBtns = document.querySelectorAll(
    ".block-actions button:nth-child(4)"
  );

  addModuleToBlockBtns.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevent event bubbling
      const blockTitle =
        this.closest(".block-header").querySelector(
          ".block-title h2"
        ).textContent;
      openAddModuleToBlockModal(blockTitle);
    });
  });

  // All action buttons in modules, subjects, and topics
  const actionButtons = document.querySelectorAll(
    ".module-actions .btn-icon, .subject-actions .btn-icon, .topic-actions .btn-icon"
  );

  actionButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevent event bubbling

      const iconClass = this.querySelector("i").className;
      let action = "";

      if (iconClass.includes("fa-edit")) {
        action = "edit";
      } else if (iconClass.includes("fa-trash-alt")) {
        action = "delete";
      } else if (iconClass.includes("fa-plus")) {
        action = "add";
      }

      let itemType = "";
      let itemName = "";

      if (this.closest(".module-actions")) {
        itemType = "module";
        itemName =
          this.closest(".module-header").querySelector(
            ".module-title span"
          ).textContent;
      } else if (this.closest(".subject-actions")) {
        itemType = "subject";
        itemName = this.closest(".subject-header").querySelector(
          ".subject-title span"
        ).textContent;
      } else if (this.closest(".topic-actions")) {
        itemType = "topic";
        itemName =
          this.closest(".topic-item").querySelector(
            ".topic-info span"
          ).textContent;
      }

      if (action === "edit") {
        openEditModal(itemType, itemName);
      } else if (action === "delete") {
        openDeleteModal(itemType, itemName);
      } else if (action === "add") {
        openAddModal(itemType, itemName);
      }
    });
  });

  // Main Add Module button
  const addModuleBtn = document.querySelector(".controls-right .btn-primary");
  if (addModuleBtn) {
    addModuleBtn.addEventListener("click", function () {
      openAddModuleModal();
    });
  }

  // Modal functions
  function openAddModuleModal() {
    showModal(
      "Add New Module",
      `
      <form id="add-module-form">
        <div class="form-group">
          <label for="module-name">Module Name</label>
          <input type="text" id="module-name" class="modal-input" placeholder="Enter module name" required>
        </div>
        <div class="form-group">
          <label for="module-block">Block</label>
          <select id="module-block" class="modal-select">
            <option value="block-a">Block A (First Prof)</option>
            <option value="block-b">Block B (Second Prof)</option>
          </select>
        </div>
        <div class="form-group">
          <label for="module-description">Description</label>
          <textarea id="module-description" class="modal-textarea" placeholder="Enter module description"></textarea>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-secondary modal-cancel">Cancel</button>
          <button type="submit" class="btn-primary">Add Module</button>
        </div>
      </form>
    `
    );

    document
      .getElementById("add-module-form")
      .addEventListener("submit", function (e) {
        e.preventDefault();
        const moduleName = document.getElementById("module-name").value;
        const blockName =
          document.getElementById("module-block").options[
            document.getElementById("module-block").selectedIndex
          ].text;

        showNotification(`Added new module: ${moduleName} to ${blockName}`);
        closeModal();
      });
  }

  function openEditBlockModal(blockName) {
    showModal(
      "Edit Block",
      `
      <form id="edit-block-form">
        <div class="form-group">
          <label for="block-name">Block Name</label>
          <input type="text" id="block-name" class="modal-input" value="${blockName}" required>
        </div>
        <div class="form-group">
          <label for="block-description">Description</label>
          <textarea id="block-description" class="modal-textarea" placeholder="Enter block description"></textarea>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-secondary modal-cancel">Cancel</button>
          <button type="submit" class="btn-primary">Save Changes</button>
        </div>
      </form>
    `
    );

    document
      .getElementById("edit-block-form")
      .addEventListener("submit", function (e) {
        e.preventDefault();
        const newBlockName = document.getElementById("block-name").value;

        showNotification(`Block updated: ${blockName} → ${newBlockName}`);
        closeModal();
      });
  }

  function openAddModuleToBlockModal(blockName) {
    showModal(
      "Add Module to " + blockName,
      `
      <form id="add-module-to-block-form">
        <div class="form-group">
          <label for="new-module-name">Module Name</label>
          <input type="text" id="new-module-name" class="modal-input" placeholder="Enter module name" required>
        </div>
        <div class="form-group">
          <label for="module-description">Description</label>
          <textarea id="module-description" class="modal-textarea" placeholder="Enter module description"></textarea>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-secondary modal-cancel">Cancel</button>
          <button type="submit" class="btn-primary">Add Module</button>
        </div>
      </form>
    `
    );

    document
      .getElementById("add-module-to-block-form")
      .addEventListener("submit", function (e) {
        e.preventDefault();
        const moduleName = document.getElementById("new-module-name").value;

        showNotification(`Added new module: ${moduleName} to ${blockName}`);
        closeModal();
      });
  }

  function openEditModal(itemType, itemName) {
    showModal(
      `Edit ${itemType}`,
      `
      <form id="edit-item-form">
        <div class="form-group">
          <label for="item-name">${
            itemType.charAt(0).toUpperCase() + itemType.slice(1)
          } Name</label>
          <input type="text" id="item-name" class="modal-input" value="${itemName}" required>
        </div>
        ${
          itemType === "module"
            ? `
        <div class="form-group">
          <label for="item-description">Description</label>
          <textarea id="item-description" class="modal-textarea" placeholder="Enter description"></textarea>
        </div>
        `
            : ""
        }
        <div class="modal-actions">
          <button type="button" class="btn-secondary modal-cancel">Cancel</button>
          <button type="submit" class="btn-primary">Save Changes</button>
        </div>
      </form>
    `
    );

    document
      .getElementById("edit-item-form")
      .addEventListener("submit", function (e) {
        e.preventDefault();
        const newName = document.getElementById("item-name").value;

        showNotification(
          `${
            itemType.charAt(0).toUpperCase() + itemType.slice(1)
          } updated: ${itemName} → ${newName}`
        );
        closeModal();
      });
  }

  function openDeleteModal(itemType, itemName) {
    showModal(
      `Delete ${itemType}`,
      `
      <div class="delete-confirmation">
        <p>Are you sure you want to delete the ${itemType} <strong>${itemName}</strong>?</p>
        <p class="warning-text">This action cannot be undone.</p>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn-secondary modal-cancel">Cancel</button>
        <button type="button" class="btn-danger confirm-delete">Delete</button>
      </div>
    `
    );

    document
      .querySelector(".confirm-delete")
      .addEventListener("click", function () {
        showNotification(
          `${
            itemType.charAt(0).toUpperCase() + itemType.slice(1)
          } deleted: ${itemName}`
        );
        closeModal();
      });
  }

  function openAddModal(itemType, parentName) {
    let childType = "";
    if (itemType === "module") childType = "subject";
    if (itemType === "subject") childType = "topic";

    showModal(
      `Add ${childType} to ${parentName}`,
      `
      <form id="add-child-form">
        <div class="form-group">
          <label for="child-name">${
            childType.charAt(0).toUpperCase() + childType.slice(1)
          } Name</label>
          <input type="text" id="child-name" class="modal-input" placeholder="Enter name" required>
        </div>
        ${
          childType === "topic"
            ? `
        <div class="form-group">
          <label for="difficulty">Difficulty</label>
          <select id="difficulty" class="modal-select">
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
        `
            : ""
        }
        <div class="modal-actions">
          <button type="button" class="btn-secondary modal-cancel">Cancel</button>
          <button type="submit" class="btn-primary">Add ${childType}</button>
        </div>
      </form>
    `
    );

    document
      .getElementById("add-child-form")
      .addEventListener("submit", function (e) {
        e.preventDefault();
        const childName = document.getElementById("child-name").value;

        showNotification(
          `Added new ${childType}: ${childName} to ${parentName}`
        );
        closeModal();
      });
  }

  // Modal functionality
  function showModal(title, content) {
    // Create modal if it doesn't exist
    if (!document.getElementById("modal-container")) {
      const modalHTML = `
        <div id="modal-overlay"></div>
        <div id="modal-container">
          <div id="modal-header">
            <h3 id="modal-title"></h3>
            <button id="modal-close"><i class="fas fa-times"></i></button>
          </div>
          <div id="modal-content"></div>
        </div>
      `;

      const modalDiv = document.createElement("div");
      modalDiv.id = "modal-wrapper";
      modalDiv.innerHTML = modalHTML;
      document.body.appendChild(modalDiv);

      // Close button functionality
      document
        .getElementById("modal-close")
        .addEventListener("click", closeModal);
      document
        .getElementById("modal-overlay")
        .addEventListener("click", closeModal);
    }

    // Set modal content
    document.getElementById("modal-title").textContent = title;
    document.getElementById("modal-content").innerHTML = content;

    // Set up cancel buttons
    const cancelBtns = document.querySelectorAll(".modal-cancel");
    cancelBtns.forEach((btn) => {
      btn.addEventListener("click", closeModal);
    });

    // Show modal
    document.getElementById("modal-wrapper").classList.add("visible");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    const modalWrapper = document.getElementById("modal-wrapper");
    if (modalWrapper) {
      modalWrapper.classList.remove("visible");
      document.body.style.overflow = "";
    }
  }

  // Search functionality
  const searchInput = document.querySelector(".search-container input");

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      const searchTerm = this.value.toLowerCase();
      const moduleItems = document.querySelectorAll(".module-item");

      moduleItems.forEach((item) => {
        const moduleTitle = item
          .querySelector(".module-title span")
          .textContent.toLowerCase();
        const moduleContent = item.querySelector(".module-content");
        const moduleIndicator = item.querySelector(".module-indicator");

        // Check if module title contains search term
        if (moduleTitle.includes(searchTerm)) {
          item.style.display = "";

          // Expand the module if there's a search term
          if (searchTerm !== "") {
            moduleContent.classList.remove("collapsed");
            moduleIndicator.classList.remove("collapsed");
            moduleIndicator.classList.add("expanded");
          }
        } else {
          // If not in module title, check in subjects and topics
          const subjectTitles = Array.from(
            item.querySelectorAll(".subject-title span")
          ).map((el) => el.textContent.toLowerCase());
          const topicTitles = Array.from(
            item.querySelectorAll(".topic-info span")
          ).map((el) => el.textContent.toLowerCase());

          const foundInSubjects = subjectTitles.some((title) =>
            title.includes(searchTerm)
          );
          const foundInTopics = topicTitles.some((title) =>
            title.includes(searchTerm)
          );

          if (foundInSubjects || foundInTopics) {
            item.style.display = "";

            // Expand the module
            moduleContent.classList.remove("collapsed");
            moduleIndicator.classList.remove("collapsed");
            moduleIndicator.classList.add("expanded");

            // Expand subjects where topics match
            if (searchTerm !== "") {
              const subjectHeaders = item.querySelectorAll(".subject-header");
              const subjectContents = item.querySelectorAll(".subject-content");
              const subjectIndicators =
                item.querySelectorAll(".subject-indicator");

              subjectHeaders.forEach((header, index) => {
                const subjectContent = subjectContents[index];
                const subjectIndicator = subjectIndicators[index];

                const topicsInSubject = Array.from(
                  subjectContent.querySelectorAll(".topic-info span")
                ).map((el) => el.textContent.toLowerCase());
                const foundInThisSubject = topicsInSubject.some((title) =>
                  title.includes(searchTerm)
                );

                if (foundInThisSubject) {
                  subjectContent.classList.remove("collapsed");
                  subjectIndicator.classList.remove("collapsed");
                  subjectIndicator.classList.add("expanded");
                }
              });
            }
          } else {
            item.style.display = "none";
          }
        }
      });
    });
  }

  // Block filter
  const blockFilter = document.querySelector(".filter-select");

  if (blockFilter) {
    blockFilter.addEventListener("change", function () {
      const filterValue = this.value;
      const blocks = document.querySelectorAll(".module-block-card");

      if (filterValue === "all") {
        blocks.forEach((block) => (block.style.display = ""));
      } else {
        blocks.forEach((block, index) => {
          if (
            (filterValue === "block-a" && index === 0) ||
            (filterValue === "block-b" && index === 1)
          ) {
            block.style.display = "";
          } else {
            block.style.display = "none";
          }
        });
      }
    });
  }
});

// Notification toast function
function showNotification(message) {
  const notification = document.getElementById("notification");
  if (notification) {
    notification.textContent = message;
    notification.classList.add("show");

    setTimeout(() => {
      notification.classList.remove("show");
    }, 3000);
  }
}
