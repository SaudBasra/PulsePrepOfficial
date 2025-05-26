document.addEventListener("DOMContentLoaded", function () {
  // Performance Trends Chart
  const performanceTrendsCtx = document.getElementById(
    "performanceTrendsChart"
  );

  if (performanceTrendsCtx) {
    const labels = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
    ];

    // Initial dataset (test scores)
    const performanceTrendsChart = new Chart(performanceTrendsCtx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Average Test Score",
            data: [68, 70, 71, 73, 75, 74, 76, 78, 72],
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
          tooltip: {
            mode: "index",
            intersect: false,
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
            min: 60,
            max: 100,
            ticks: {
              stepSize: 10,
            },
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
          },
        },
      },
    });

    // Chart control buttons
    const chartControlBtns = document.querySelectorAll(".chart-control-btn");
    chartControlBtns.forEach((button) => {
      button.addEventListener("click", function () {
        chartControlBtns.forEach((btn) => btn.classList.remove("active"));
        this.classList.add("active");

        const metric = this.getAttribute("data-metric");
        let newData, newLabel, newColor;

        switch (metric) {
          case "scores":
            newData = [68, 70, 71, 73, 75, 74, 76, 78, 72];
            newLabel = "Average Test Score";
            newColor = "#82272e";
            break;
          case "completion":
            newData = [65, 68, 72, 75, 77, 80, 82, 84, 85];
            newLabel = "Completion Rate";
            newColor = "#3b82f6";
            break;
          case "engagement":
            newData = [50, 55, 60, 65, 70, 72, 75, 78, 80];
            newLabel = "Engagement Rate";
            newColor = "#8b5cf6";
            break;
        }

        performanceTrendsChart.data.datasets[0].data = newData;
        performanceTrendsChart.data.datasets[0].label = newLabel;
        performanceTrendsChart.data.datasets[0].borderColor = newColor;
        performanceTrendsChart.data.datasets[0].backgroundColor = `${newColor}1A`; // 10% opacity
        performanceTrendsChart.update();
      });
    });
  }

  // Student Distribution Chart
  const studentDistributionCtx = document.getElementById(
    "studentDistributionChart"
  );

  if (studentDistributionCtx) {
    new Chart(studentDistributionCtx, {
      type: "doughnut",
      data: {
        labels: ["MBBS", "BDS", "Nursing", "Pharmacy", "Other"],
        datasets: [
          {
            data: [40, 25, 15, 12, 8],
            backgroundColor: [
              "#82272e",
              "#9f1239",
              "#be123c",
              "#e11d48",
              "#f43f5e",
            ],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              padding: 20,
              boxWidth: 10,
            },
          },
        },
        cutout: "70%",
      },
    });
  }

  // Activity by Time of Day Chart
  const activityTimeCtx = document.getElementById("activityTimeChart");

  if (activityTimeCtx) {
    new Chart(activityTimeCtx, {
      type: "bar",
      data: {
        labels: [
          "6-9am",
          "9-12pm",
          "12-3pm",
          "3-6pm",
          "6-9pm",
          "9-12am",
          "12-6am",
        ],
        datasets: [
          {
            label: "Activity Count",
            data: [850, 1200, 950, 1350, 1800, 950, 250],
            backgroundColor: "#82272e",
            borderRadius: 4,
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
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
            beginAtZero: true,
          },
        },
      },
    });
  }

  // Filter controls
  const applyFiltersBtn = document.getElementById("apply-filters");
  if (applyFiltersBtn) {
    applyFiltersBtn.addEventListener("click", function () {
      const dateRange = document.getElementById("date-range").value;
      const program = document.getElementById("program-filter").value;
      const module = document.getElementById("module-filter").value;

      // In a real app, this would update the data with the selected filters
      showNotification(
        `Filters applied: ${dateRange} days, Program: ${program}, Module: ${module}`
      );
    });
  }

  // Export report button
  const exportReportBtn = document.getElementById("export-report");
  if (exportReportBtn) {
    exportReportBtn.addEventListener("click", function () {
      showNotification("Exporting report as PDF...");
    });
  }

  // Module search
  const moduleSearch = document.querySelector(
    ".analytics-table-card .search-input"
  );
  if (moduleSearch) {
    moduleSearch.addEventListener("input", function () {
      const searchTerm = this.value.toLowerCase();
      const tableRows = document.querySelectorAll(".analytics-table tbody tr");

      tableRows.forEach((row) => {
        const moduleName = row
          .querySelector("td:first-child")
          .textContent.toLowerCase();
        if (moduleName.includes(searchTerm)) {
          row.style.display = "";
        } else {
          row.style.display = "none";
        }
      });
    });
  }

  // View details buttons
  const viewDetailsButtons = document.querySelectorAll(
    ".analytics-table .btn-view"
  );
  viewDetailsButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const moduleName =
        this.closest("tr").querySelector("td:first-child").textContent;

      // In a real app, this would open the module details page
      showNotification(`Viewing details for ${moduleName}`);
    });
  });

  // Pagination
  const pageButtons = document.querySelectorAll(
    ".analytics-table-card .page-number"
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
    ".analytics-table-card .prev-page"
  );
  if (prevPageBtn) {
    prevPageBtn.addEventListener("click", function () {
      const activePage = document.querySelector(
        ".analytics-table-card .page-number.active"
      );
      const pageNumber = parseInt(activePage.textContent);

      if (pageNumber > 1) {
        const prevPage = document.querySelector(
          `.analytics-table-card .page-number:nth-child(${pageNumber - 1})`
        );
        activePage.classList.remove("active");
        prevPage.classList.add("active");

        // In a real app, this would load the previous page
        showNotification(`Navigated to page ${pageNumber - 1}`);
      }
    });
  }

  const nextPageBtn = document.querySelector(
    ".analytics-table-card .next-page"
  );
  if (nextPageBtn) {
    nextPageBtn.addEventListener("click", function () {
      const activePage = document.querySelector(
        ".analytics-table-card .page-number.active"
      );
      const pageNumber = parseInt(activePage.textContent);
      const totalPages = document.querySelectorAll(
        ".analytics-table-card .page-number"
      ).length;

      if (pageNumber < totalPages) {
        const nextPage = document.querySelector(
          `.analytics-table-card .page-number:nth-child(${pageNumber + 1})`
        );
        activePage.classList.remove("active");
        nextPage.classList.add("active");

        // In a real app, this would load the next page
        showNotification(`Navigated to page ${pageNumber + 1}`);
      }
    });
  }
});
