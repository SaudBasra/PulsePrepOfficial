document.addEventListener("DOMContentLoaded", function () {
  // Toggle sidebar
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");
  const mainContent = document.querySelector(".main-content");

  // Handle sidebar toggle
  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevent click from triggering document click
      sidebar.classList.toggle("active");
    });
  }

  // Close sidebar when clicking outside
  document.addEventListener("click", function (e) {
    // Only if we're on mobile and sidebar is open
    if (window.innerWidth <= 768 && sidebar.classList.contains("active")) {
      // Check if click is outside the sidebar
      if (!sidebar.contains(e.target) && e.target !== sidebarToggle) {
        sidebar.classList.remove("active");
      }
    }
  });

  // Prevent clicks inside sidebar from closing it
  sidebar.addEventListener("click", function (e) {
    e.stopPropagation();
  });

  // Handle media query changes
  const mediaQuery = window.matchMedia("(max-width: 768px)");

  function handleMediaChange(e) {
    if (e.matches) {
      sidebar.classList.remove("active");
      mainContent.classList.remove("expanded");
    } else {
      sidebar.classList.remove("collapsed");
      mainContent.classList.remove("expanded");
    }
  }

  mediaQuery.addEventListener("change", handleMediaChange);
  handleMediaChange(mediaQuery);

  // Form functionality for the Manage Questions page
  setupFormInteractions();
  
  // Initialize analytics animations
  animateAnalyticsCards();
});

// Animate analytics cards on page load
function animateAnalyticsCards() {
  const cards = document.querySelectorAll('.analytics-card');
  const difficultyBars = document.querySelectorAll('.difficulty-fill');
  
  // Animate cards
  cards.forEach((card, index) => {
    setTimeout(() => {
      card.style.transform = 'translateY(0)';
      card.style.opacity = '1';
    }, index * 100);
  });
  
  // Animate difficulty bars
  setTimeout(() => {
    difficultyBars.forEach(bar => {
      const width = bar.style.width;
      bar.style.width = '0%';
      setTimeout(() => {
        bar.style.width = width;
      }, 100);
    });
  }, 500);
}

function setupFormInteractions() {
  // Toggle correct answer
  const answerOptions = document.querySelectorAll(
    '.answer-option input[type="radio"]'
  );

  answerOptions.forEach((radio) => {
    radio.addEventListener("change", function () {
      updateCorrectAnswerTags();
    });
  });

  // Initially set correct answer tag
  updateCorrectAnswerTags();

  // Add answer button functionality
  const addAnswerBtn = document.querySelector(".add-answer-btn");
  if (addAnswerBtn) {
    addAnswerBtn.addEventListener("click", function () {
      addNewAnswer();
    });
  }

  // Add button in the add answers row
  const btnAdd = document.querySelector(".btn-add");
  if (btnAdd) {
    btnAdd.addEventListener("click", function () {
      const addAnswerText = document.querySelector(".add-answer-text");
      if (addAnswerText.value.trim() !== "") {
        addAnswerFromInput(addAnswerText.value);
        addAnswerText.value = "";
      } else {
        showNotification("Please enter an answer text", "error");
      }
    });
  }

  // Remove button in the add answers row
  const btnRemove = document.querySelector(".btn-remove");
  if (btnRemove) {
    btnRemove.addEventListener("click", function () {
      document.querySelector(".add-answer-text").value = "";
    });
  }

  // Add delete buttons for existing answer options
  setupAnswerOptionDeleteButtons();

  // Add edit functionality to pencil icons
  const editBtns = document.querySelectorAll(".edit-btn");
  editBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      // Get the question item
      const questionItem = this.closest(".question-item");

      // Add editing class to highlight
      questionItem.classList.add("editing");

      // Get the question text
      const questionText = questionItem.querySelector(
        ".question-content span"
      ).textContent;

      // Set the question text in the editor
      document.getElementById("question-text").value = questionText;

      // Focus on the question type dropdown
      document.getElementById("question-type").focus();

      // Scroll to editor
      document
        .querySelector(".question-editor-card")
        .scrollIntoView({ behavior: "smooth" });
    });
  });

  // Add question button in header
  const addQuestionBtn = document.querySelector(".add-question-btn");
  if (addQuestionBtn) {
    addQuestionBtn.addEventListener("click", function () {
      // Clear previous inputs
      document.getElementById("question-text").value = "";

      // Reset radio selections
      const radioButtons = document.querySelectorAll(
        '.answer-option:not(.add-answer-input) input[type="radio"]'
      );
      radioButtons.forEach((radio) => {
        radio.checked = false;
      });

      // Hide all correct answer tags
      document.querySelectorAll(".correct-tag").forEach((tag) => {
        tag.style.display = "none";
      });

      // Clear the add answer input if it exists
      const addAnswerText = document.querySelector(".add-answer-text");
      if (addAnswerText) {
        addAnswerText.value = "";
      }

      // Focus on the question type dropdown
      const questionType = document.getElementById("question-type");

      // Scroll to the question editor
      const questionEditor = document.querySelector(".question-editor-card");
      if (questionEditor) {
        questionEditor.scrollIntoView({ behavior: "smooth" });

        // After scrolling, focus on the question type
        setTimeout(() => {
          questionType.focus();
        }, 500);
      }
    });
  }

  // Add question submit button functionality
  const addQuestionSubmit = document.querySelector(".add-question-submit");
  if (addQuestionSubmit) {
    addQuestionSubmit.addEventListener("click", function () {
      const questionText = document.getElementById("question-text").value;
      if (questionText.trim() === "") {
        showNotification("Please enter a question text", "error");
        return;
      }

      // Check if at least one answer is selected as correct
      const anyCorrect = Array.from(
        document.querySelectorAll(
          '.answer-option:not(.add-answer-input) input[type="radio"]'
        )
      ).some((radio) => radio.checked);
      if (!anyCorrect) {
        showNotification("Please select a correct answer", "error");
        return;
      }

      // Add the question to the questions list
      addQuestionToList(questionText);

      showNotification("Question added successfully!");

      // Clear the form for the next question
      document.getElementById("question-text").value = "";

      // Reset radio selections
      document
        .querySelectorAll('.answer-option input[type="radio"]')
        .forEach((radio) => {
          radio.checked = false;
        });

      // Hide all correct answer tags
      document.querySelectorAll(".correct-tag").forEach((tag) => {
        tag.style.display = "none";
      });

      // Scroll to questions list
      document
        .querySelector(".questions-list-card")
        .scrollIntoView({ behavior: "smooth" });
    });
  }

  // Add delete functionality to question delete buttons
  const questionDeleteBtns = document.querySelectorAll(
    ".question-item .delete-btn"
  );
  questionDeleteBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      const questionItem = this.closest(".question-item");
      if (confirm("Are you sure you want to delete this question?")) {
        questionItem.style.opacity = "0";
        questionItem.style.height = "0";
        questionItem.style.overflow = "hidden";
        questionItem.style.padding = "0";
        questionItem.style.margin = "0";
        questionItem.style.border = "none";

        setTimeout(() => {
          questionItem.remove();
          renumberQuestions();
        }, 300);

        showNotification("Question deleted");
      }
    });
  });
}

// Add delete buttons to all answer options
function setupAnswerOptionDeleteButtons() {
  const answerOptions = document.querySelectorAll(
    ".answer-option:not(.add-answer-input)"
  );

  answerOptions.forEach((option) => {
    // Only add delete button if it doesn't already have one
    if (!option.querySelector(".delete-option-btn")) {
      const deleteButton = document.createElement("button");
      deleteButton.className = "delete-option-btn";
      deleteButton.innerHTML = '<i class="fas fa-times"></i>';
      deleteButton.addEventListener("click", function () {
        deleteAnswerOption(option);
      });

      option.appendChild(deleteButton);
    }
  });
}

// Delete an answer option
function deleteAnswerOption(option) {
  option.classList.add("deleting");

  setTimeout(() => {
    option.remove();

    // Renumber remaining answer options
    const options = document.querySelectorAll(
      ".answer-option:not(.add-answer-input)"
    );
    options.forEach((opt, index) => {
      const radio = opt.querySelector('input[type="radio"]');
      const label = opt.querySelector("label");

      if (radio && label) {
        radio.id = `answer${index + 1}`;
        label.setAttribute("for", `answer${index + 1}`);
      }
    });

    // Update correct answer tags
    updateCorrectAnswerTags();

    showNotification("Answer option deleted");
  }, 300);
}

// Update correct answer tags based on radio selection
function updateCorrectAnswerTags() {
  const answerOptions = document.querySelectorAll(
    ".answer-option:not(.add-answer-input)"
  );

  answerOptions.forEach((option) => {
    const radio = option.querySelector('input[type="radio"]');
    let tag = option.querySelector(".correct-tag");

    // If tag doesn't exist, create it after the label
    if (!tag && radio && radio.checked) {
      const label = option.querySelector(".radio-label");
      tag = document.createElement("span");
      tag.className = "correct-tag";
      tag.textContent = "Correct answer";

      // Insert after the label
      if (label && label.nextSibling) {
        option.insertBefore(tag, label.nextSibling);
      } else {
        option.appendChild(tag);
      }
    } else if (tag) {
      if (radio && radio.checked) {
        tag.style.display = "inline-block";
      } else {
        tag.style.display = "none";
      }
    }
  });
}

// Add a new answer option (support up to E option)
function addNewAnswer() {
  const answerOptions = document.querySelector(".answer-options");
  const answerCount = document.querySelectorAll(
    ".answer-option:not(.add-answer-input)"
  ).length;
  
  // Limit to 5 options (A, B, C, D, E)
  if (answerCount >= 5) {
    showNotification("Maximum 5 options allowed (A-E)", "error");
    return;
  }
  
  const optionLabels = ['A', 'B', 'C', 'D', 'E'];
  const newIndex = answerCount + 1;
  const optionLetter = optionLabels[answerCount];

  // Create new answer option
  const newOption = document.createElement("div");
  newOption.className = "answer-option new-answer";

  // HTML for the new option with correct tag positioned after the label
  newOption.innerHTML = `
    <input type="radio" name="correct-answer" id="answer${newIndex}" value="${optionLetter}">
    <label for="answer${newIndex}" class="radio-label">Option ${optionLetter}</label>
    <span class="correct-tag" style="display: none;">Correct answer</span>
    <button class="delete-option-btn"><i class="fas fa-times"></i></button>
  `;

  // Get the add answers input row and insert before it
  const addAnswerInput = document.querySelector(
    ".answer-option.add-answer-input"
  );
  if (addAnswerInput) {
    answerOptions.insertBefore(newOption, addAnswerInput);
  } else {
    answerOptions.appendChild(newOption);
  }

  // Add event listener to the new radio button
  const newRadio = newOption.querySelector('input[type="radio"]');
  newRadio.addEventListener("change", function () {
    updateCorrectAnswerTags();
  });

  // Add event listener to the delete button
  const deleteBtn = newOption.querySelector(".delete-option-btn");
  deleteBtn.addEventListener("click", function () {
    deleteAnswerOption(newOption);
  });
}

// Add answer from the input (support up to E option)
function addAnswerFromInput(text) {
  const answerOptions = document.querySelector(".answer-options");
  const answerCount = document.querySelectorAll(
    ".answer-option:not(.add-answer-input)"
  ).length;
  
  // Limit to 5 options (A, B, C, D, E)
  if (answerCount >= 5) {
    showNotification("Maximum 5 options allowed (A-E)", "error");
    return;
  }
  
  const optionLabels = ['A', 'B', 'C', 'D', 'E'];
  const newIndex = answerCount + 1;
  const optionLetter = optionLabels[answerCount];

  // Create new answer option
  const newOption = document.createElement("div");
  newOption.className = "answer-option new-answer";

  // HTML for the new option with correct tag positioned after the label
  newOption.innerHTML = `
    <input type="radio" name="correct-answer" id="answer${newIndex}" value="${optionLetter}">
    <label for="answer${newIndex}" class="radio-label">${text}</label>
    <span class="correct-tag" style="display: none;">Correct answer</span>
    <button class="delete-option-btn"><i class="fas fa-times"></i></button>
  `;

  // Get the add answers input row and insert before it
  const addAnswerInput = document.querySelector(
    ".answer-option.add-answer-input"
  );
  if (addAnswerInput) {
    answerOptions.insertBefore(newOption, addAnswerInput);
  } else {
    answerOptions.appendChild(newOption);
  }

  // Add event listener to the new radio button
  const newRadio = newOption.querySelector('input[type="radio"]');
  newRadio.addEventListener("change", function () {
    updateCorrectAnswerTags();
  });

  // Add event listener to the delete button
  const deleteBtn = newOption.querySelector(".delete-option-btn");
  deleteBtn.addEventListener("click", function () {
    deleteAnswerOption(newOption);
  });
}

// Add a question to the questions list
function addQuestionToList(questionText) {
  const questionsList = document.querySelector(".questions-table");
  const questionsCount = document.querySelectorAll(".question-item").length;
  const newQuestionNumber = questionsCount + 1;

  // Create new question item
  const newQuestion = document.createElement("div");
  newQuestion.className = "question-item";

  // Get the selected question type
  const questionType = document.getElementById("question-type");
  const selectedType = questionType ? questionType.value : "Multiple Choice";

  // Get the icon based on question type
  let typeIcon = "far fa-square-check";
  if (selectedType.includes("True/False")) {
    typeIcon = "fas fa-toggle-on";
  } else if (selectedType.includes("Short Answer")) {
    typeIcon = "fas fa-font";
  } else if (selectedType.includes("Essay")) {
    typeIcon = "fas fa-align-left";
  }

  // HTML for the new question
  newQuestion.innerHTML = `
    <div class="question-number">
      <i class="fas fa-grip-lines"></i>
      <span>Question ${newQuestionNumber}</span>
    </div>
    <div class="question-content">
      <div class="question-type">
        <i class="${typeIcon}"></i>
      </div>
      <span>${questionText}</span>
    </div>
    <div class="question-actions">
      <button class="edit-btn"><i class="fas fa-pencil"></i></button>
      <button class="delete-btn"><i class="fas fa-trash"></i></button>
    </div>
  `;

  // Add to the questions list
  questionsList.appendChild(newQuestion);

  // Add event listeners to the new buttons
  const editBtn = newQuestion.querySelector(".edit-btn");
  editBtn.addEventListener("click", function () {
    // Remove editing class from all items
    document.querySelectorAll(".question-item").forEach((item) => {
      item.classList.remove("editing");
    });

    // Add editing class to highlight
    newQuestion.classList.add("editing");

    // Set the question text in the editor
    document.getElementById("question-text").value = questionText;

    // Focus on the question type dropdown
    document.getElementById("question-type").focus();

    // Scroll to editor
    document
      .querySelector(".question-editor-card")
      .scrollIntoView({ behavior: "smooth" });
  });

  const deleteBtn = newQuestion.querySelector(".delete-btn");
  deleteBtn.addEventListener("click", function () {
    if (confirm("Are you sure you want to delete this question?")) {
      newQuestion.style.opacity = "0";
      newQuestion.style.height = "0";
      newQuestion.style.overflow = "hidden";
      newQuestion.style.padding = "0";
      newQuestion.style.margin = "0";
      newQuestion.style.border = "none";

      setTimeout(() => {
        newQuestion.remove();
        renumberQuestions();
      }, 300);

      showNotification("Question deleted");
    }
  });
}

// Renumber questions after deletion
function renumberQuestions() {
  const questions = document.querySelectorAll(".question-item");
  questions.forEach((question, index) => {
    question.querySelector(".question-number span").textContent = `Question ${
      index + 1
    }`;
  });
}

// Show notification with improved styling
function showNotification(message, type = "success") {
  // Remove any existing notifications
  const existingNotifications = document.querySelectorAll(".notification");
  existingNotifications.forEach((notif) => notif.remove());

  // Create a new notification
  const notification = document.createElement("div");
  notification.className = `notification ${type}`;
  notification.innerHTML = `
    <span>${message}</span>
    <button class="close-notification" onclick="this.parentElement.remove()">
      <i class="fas fa-times"></i>
    </button>
  `;
  document.body.appendChild(notification);

  // Show the notification
  setTimeout(() => {
    notification.classList.add("show");
  }, 10);

  // Automatically hide after 3 seconds
  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 300);
  }, 3000);
}

// Analytics helper functions
function updateAnalyticsOnQuestionChange() {
  // This function would be called when questions are added/deleted
  // to update the analytics in real-time
  const totalQuestions = document.querySelectorAll('.question-item').length;
  const totalQuestionsCard = document.querySelector('.analytics-card .card-content h3');
  if (totalQuestionsCard) {
    totalQuestionsCard.textContent = totalQuestions;
  }
}

// Filter helper functions
function clearAllFilters() {
  const filterSelects = document.querySelectorAll('.filter-select');
  filterSelects.forEach(select => {
    select.value = '';
  });
  
  const searchInput = document.querySelector('.search-input');
  if (searchInput) {
    searchInput.value = '';
  }
  
  // Submit the form to apply the cleared filters
  const searchForm = document.querySelector('.search-form');
  if (searchForm) {
    searchForm.submit();
  }
}

// Export helper functions
function exportFilteredQuestions() {
  const currentUrl = new URL(window.location);
  const exportUrl = new URL('/api/export-questions/', window.location.origin);
  
  // Copy current filter parameters to export URL
  currentUrl.searchParams.forEach((value, key) => {
    if (key !== 'page') { // Don't include pagination in export
      exportUrl.searchParams.set(key, value);
    }
  });
  
  window.location.href = exportUrl.toString();
}

// End of script

// Enhanced question validation
function validateQuestionsEnhanced() {
  const form = document.querySelector('.mock-test-form');
  if (!form) return;

  const degree = document.getElementById('id_degree')?.value;
  const year = document.getElementById('id_year')?.value;
  const module = document.getElementById('id_module')?.value;
  const subject = document.getElementById('id_subject')?.value;
  const difficulty = document.getElementById('id_difficulty_level')?.value;
  const totalQuestions = document.getElementById('id_total_questions')?.value;
  const questionSource = document.querySelector('input[name="question_source"]:checked')?.value;

  if (questionSource === 'RANDOM' && totalQuestions && parseInt(totalQuestions) > 0) {
    const params = new URLSearchParams({
      degree: degree || '',
      year: year || '',
      module: module || '',
      subject: subject || '',
      difficulty: difficulty || '',
      total_questions: totalQuestions
    });

    fetch(`/mocktest/ajax/validate-questions/?${params}`)
      .then(response => response.json())
      .then(data => {
        const validationDiv = document.getElementById('question-validation');
        if (validationDiv) {
          if (data.is_sufficient) {
            validationDiv.innerHTML = `<span style="color: green;"><i class="fas fa-check-circle"></i> ${data.message}</span>`;
          } else {
            validationDiv.innerHTML = `<span style="color: red;"><i class="fas fa-exclamation-triangle"></i> Only ${data.available_count} questions available (need ${data.total_required})</span>`;
          }
        }
      })
      .catch(error => {
        console.error('Validation error:', error);
      });
  }
}

// Auto-save draft functionality
let autoSaveTimeout;
function autoSaveDraft() {
  clearTimeout(autoSaveTimeout);
  autoSaveTimeout = setTimeout(() => {
    const form = document.querySelector('.mock-test-form');
    if (form) {
      const formData = new FormData(form);
      formData.append('auto_save', 'true');
      
      fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        }
      }).then(response => {
        if (response.ok) {
          showToast('Draft saved automatically', 'info');
        }
      }).catch(error => {
        console.log('Auto-save failed:', error);
      });
    }
  }, 5000); // Save after 5 seconds of inactivity
}

// Enhanced form validation
function validateTestForm() {
  const form = document.querySelector('.mock-test-form');
  if (!form) return true;

  const title = document.getElementById('id_title')?.value.trim();
  const startDate = document.getElementById('id_start_date')?.value;
  const endDate = document.getElementById('id_end_date')?.value;
  const duration = document.getElementById('id_duration')?.value;
  const totalQuestions = document.getElementById('id_total_questions')?.value;

  // Basic validation
  if (!title) {
    showToast('Please enter a test title', 'error');
    return false;
  }

  if (!startDate || !endDate) {
    showToast('Please select start and end dates', 'error');
    return false;
  }

  if (new Date(endDate) <= new Date(startDate)) {
    showToast('End date must be after start date', 'error');
    return false;
  }

  if (!duration || parseInt(duration) < 5) {
    showToast('Duration must be at least 5 minutes', 'error');
    return false;
  }

  if (!totalQuestions || parseInt(totalQuestions) < 1) {
    showToast('Please specify number of questions', 'error');
    return false;
  }

  return true;
}

// Initialize enhanced functionality
document.addEventListener('DOMContentLoaded', function() {
  // Add validation to form fields
  const formFields = document.querySelectorAll('#id_degree, #id_year, #id_module, #id_subject, #id_difficulty_level, #id_total_questions');
  formFields.forEach(field => {
    if (field) {
      field.addEventListener('change', validateQuestionsEnhanced);
      field.addEventListener('input', autoSaveDraft);
    }
  });

  // Add validation to question source radio buttons
  document.querySelectorAll('input[name="question_source"]').forEach(radio => {
    radio.addEventListener('change', validateQuestionsEnhanced);
  });

  // Form submission validation
  const form = document.querySelector('.mock-test-form');
  if (form) {
    form.addEventListener('submit', function(e) {
      if (!validateTestForm()) {
        e.preventDefault();
      }
    });
  }

  // Initial validation
  validateQuestionsEnhanced();
});