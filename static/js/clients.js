document.addEventListener("DOMContentLoaded", function () {
  // Tab Switching
  const tabButtons = document.querySelectorAll(".client-tab");
  const tabContents = document.querySelectorAll(".client-tab-content");

  tabButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const tabId = this.getAttribute("data-tab");

      // Remove active class from all tabs and contents
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      tabContents.forEach((content) => content.classList.remove("active"));

      // Add active class to current tab and content
      this.classList.add("active");
      document.getElementById(`${tabId}-tab`).classList.add("active");
    });
  });

  // Client Performance Chart
  const clientPerformanceCtx = document.getElementById(
    "clientPerformanceChart"
  );

  if (clientPerformanceCtx) {
    new Chart(clientPerformanceCtx, {
      type: "line",
      data: {
        labels: [
          "Week 1",
          "Week 2",
          "Week 3",
          "Week 4",
          "Week 5",
          "Week 6",
          "Week 7",
          "Week 8",
        ],
        datasets: [
          {
            label: "Test Scores",
            data: [88, 90, 87, 92, 94, 91, 95, 96],
            borderColor: "#82272e",
            backgroundColor: "rgba(130, 39, 46, 0.1)",
            tension: 0.4,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
          },
          y: {
            beginAtZero: false,
            min: 70,
            max: 100,
            ticks: {
              stepSize: 5,
            },
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
          },
        },
      },
    });
  }

  // Score Trends Chart in Performance Tab
  const scoresTrendCtx = document.getElementById("scoresTrendChart");

  if (scoresTrendCtx) {
    // Initial data for weekly view
    const weeklyData = {
      labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
      data: [92, 88, 95, 90, 96, 93, 94],
    };

    // Monthly data
    const monthlyData = {
      labels: ["Week 1", "Week 2", "Week 3", "Week 4"],
      data: [89, 92, 94, 95],
    };

    // Yearly data
    const yearlyData = {
      labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"],
      data: [82, 85, 88, 86, 90, 89, 91, 93, 95],
    };

    const scoresTrendChart = new Chart(scoresTrendCtx, {
      type: "line",
      data: {
        labels: weeklyData.labels,
        datasets: [
          {
            label: "Score",
            data: weeklyData.data,
            borderColor: "#82272e",
            backgroundColor: "rgba(130, 39, 46, 0.1)",
            tension: 0.4,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
          },
          y: {
            beginAtZero: false,
            min: 70,
            max: 100,
            ticks: {
              stepSize: 5,
            },
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
          },
        },
      },
    });

    // Period filter buttons
    const periodFilterBtns = document.querySelectorAll(".chart-filter-btn");
    periodFilterBtns.forEach((button) => {
      button.addEventListener("click", function () {
        periodFilterBtns.forEach((btn) => btn.classList.remove("active"));
        this.classList.add("active");

        const period = this.getAttribute("data-period");
        let chartData;

        switch (period) {
          case "week":
            chartData = weeklyData;
            break;
          case "month":
            chartData = monthlyData;
            break;
          case "year":
            chartData = yearlyData;
            break;
        }

        scoresTrendChart.data.labels = chartData.labels;
        scoresTrendChart.data.datasets[0].data = chartData.data;
        scoresTrendChart.update();
      });
    });
  }

  // Strength Analysis Chart
  const strengthAnalysisCtx = document.getElementById("strengthAnalysisChart");

  if (strengthAnalysisCtx) {
    new Chart(strengthAnalysisCtx, {
      type: "radar",
      data: {
        labels: [
          "Cardiovascular",
          "Respiratory",
          "Digestive",
          "Neurology",
          "Endocrine",
          "Renal",
        ],
        datasets: [
          {
            label: "Performance",
            data: [96, 92, 94, 85, 88, 78],
            fill: true,
            backgroundColor: "rgba(130, 39, 46, 0.2)",
            borderColor: "#82272e",
            pointBackgroundColor: "#82272e",
            pointBorderColor: "#fff",
            pointHoverBackgroundColor: "#fff",
            pointHoverBorderColor: "#82272e",
          },
        ],
      },
      options: {
        elements: {
          line: {
            borderWidth: 2,
          },
        },
        scales: {
          r: {
            angleLines: {
              display: true,
            },
            suggestedMin: 60,
            suggestedMax: 100,
          },
        },
      },
    });
  }

  // Module Filter
  const moduleFilterSelect = document.querySelector(".module-filter-select");
  if (moduleFilterSelect) {
    moduleFilterSelect.addEventListener("change", function () {
      const filter = this.value;
      const moduleItems = document.querySelectorAll(".module-item");

      if (filter === "all") {
        moduleItems.forEach((item) => (item.style.display = ""));
      } else {
        moduleItems.forEach((item) => {
          if (item.classList.contains(filter)) {
            item.style.display = "";
          } else {
            item.style.display = "none";
          }
        });
      }
    });
  }

  // Test search in Performance tab
  const testSearch = document.querySelector(
    ".performance-table-card .search-input"
  );
  if (testSearch) {
    testSearch.addEventListener("input", function () {
      const searchTerm = this.value.toLowerCase();
      const tableRows = document.querySelectorAll(
        ".performance-table tbody tr"
      );

      tableRows.forEach((row) => {
        const testName = row
          .querySelector("td:first-child")
          .textContent.toLowerCase();
        if (testName.includes(searchTerm)) {
          row.style.display = "";
        } else {
          row.style.display = "none";
        }
      });
    });
  }

  // Test filter in Performance tab
  const testFilter = document.querySelector(
    ".performance-table-card .filter-select"
  );
  if (testFilter) {
    testFilter.addEventListener("change", function () {
      const filter = this.value;
      const tableRows = document.querySelectorAll(
        ".performance-table tbody tr"
      );

      tableRows.forEach((row) => {
        const testType = row
          .querySelector("td:nth-child(2)")
          .textContent.toLowerCase();
        const testStatus = row
          .querySelector(".status-badge")
          .textContent.toLowerCase();

        if (
          filter === "all" ||
          (filter === "mock" && testType.includes("mock")) ||
          (filter === "quiz" && testType.includes("quiz")) ||
          (filter === "passed" && testStatus === "passed") ||
          (filter === "failed" && testStatus === "failed")
        ) {
          row.style.display = "";
        } else {
          row.style.display = "none";
        }
      });
    });
  }

  // Activity log filter
  const activityFilter = document.querySelector(
    ".activity-log-card .filter-select"
  );
  if (activityFilter) {
    activityFilter.addEventListener("change", function () {
      const filter = this.value;
      const activityItems = document.querySelectorAll(".activity-log-item");

      activityItems.forEach((item) => {
        const icon = item.querySelector(".activity-log-icon");

        if (filter === "all" || icon.classList.contains(filter)) {
          item.style.display = "";
        } else {
          item.style.display = "none";
        }
      });
    });
  }

  // Load more activity button
  const loadMoreBtn = document.querySelector(".btn-load-more");
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener("click", function () {
      // In a real application, this would load additional activity log items
      showNotification("Loading more activity...");
    });
  }

  // Pagination
  const pageButtons = document.querySelectorAll(
    ".performance-table-card .page-number"
  );
  pageButtons.forEach((button) => {
    button.addEventListener("click", function () {
      pageButtons.forEach((btn) => btn.classList.remove("active"));
      this.classList.add("active");

      // In a real app, this would load the appropriate page of data
      showNotification(`Navigated to page ${this.textContent}`);
    });
  });

  const prevPageBtn = document.querySelector(
    ".performance-table-card .prev-page"
  );
  if (prevPageBtn) {
    prevPageBtn.addEventListener("click", function () {
      const activePage = document.querySelector(
        ".performance-table-card .page-number.active"
      );
      const pageNumber = parseInt(activePage.textContent);

      if (pageNumber > 1) {
        const prevPage = document.querySelector(
          `.performance-table-card .page-number:nth-child(${pageNumber - 1})`
        );
        activePage.classList.remove("active");
        prevPage.classList.add("active");

        // In a real app, this would load the previous page
        showNotification(`Navigated to page ${pageNumber - 1}`);
      }
    });
  }

  const nextPageBtn = document.querySelector(
    ".performance-table-card .next-page"
  );
  if (nextPageBtn) {
    nextPageBtn.addEventListener("click", function () {
      const activePage = document.querySelector(
        ".performance-table-card .page-number.active"
      );
      const pageNumber = parseInt(activePage.textContent);
      const totalPages = document.querySelectorAll(
        ".performance-table-card .page-number"
      ).length;

      if (pageNumber < totalPages) {
        const nextPage = document.querySelector(
          `.performance-table-card .page-number:nth-child(${pageNumber + 1})`
        );
        activePage.classList.remove("active");
        nextPage.classList.add("active");

        // In a real app, this would load the next page
        showNotification(`Navigated to page ${pageNumber + 1}`);
      }
    });
  }
});

// Shared notification function
function showNotification(message) {
  const notification = document.getElementById("notification");
  notification.textContent = message;
  notification.classList.add("show");

  setTimeout(() => {
    notification.classList.remove("show");
  }, 3000);
}
