document.addEventListener("DOMContentLoaded", function () {
  // Module Performance Chart
  const modulePerformanceCtx = document.getElementById(
    "modulePerformanceChart"
  );

  if (modulePerformanceCtx) {
    // Initial data for weekly view
    const weeklyData = {
      labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
      datasets: [
        {
          label: "Average Score",
          data: [76, 74, 77, 75, 78, 76, 77],
          borderColor: "#82272e",
          backgroundColor: "rgba(130, 39, 46, 0.1)",
          tension: 0.4,
          fill: true,
        },
        {
          label: "Completion Rate",
          data: [82, 83, 84, 85, 87, 86, 88],
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          tension: 0.4,
          fill: true,
          yAxisID: "y1",
        },
      ],
    };

    // Monthly data
    const monthlyData = {
      labels: ["Week 1", "Week 2", "Week 3", "Week 4"],
      datasets: [
        {
          label: "Average Score",
          data: [74, 75, 77, 79],
          borderColor: "#82272e",
          backgroundColor: "rgba(130, 39, 46, 0.1)",
          tension: 0.4,
          fill: true,
        },
        {
          label: "Completion Rate",
          data: [80, 82, 85, 88],
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          tension: 0.4,
          fill: true,
          yAxisID: "y1",
        },
      ],
    };

    // Yearly data
    const yearlyData = {
      labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
      datasets: [
        {
          label: "Average Score",
          data: [72, 73, 74, 75, 76, 77],
          borderColor: "#82272e",
          backgroundColor: "rgba(130, 39, 46, 0.1)",
          tension: 0.4,
          fill: true,
        },
        {
          label: "Completion Rate",
          data: [76, 78, 81, 83, 84, 87],
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59, 130, 246, 0.1)",
          tension: 0.4,
          fill: true,
          yAxisID: "y1",
        },
      ],
    };

    const modulePerformanceChart = new Chart(modulePerformanceCtx, {
      type: "line",
      data: {
        labels: weeklyData.labels,
        datasets: weeklyData.datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        scales: {
          y: {
            beginAtZero: false,
            min: 65,
            max: 100,
            ticks: {
              stepSize: 5,
            },
            title: {
              display: true,
              text: "Score (%)",
            },
          },
          y1: {
            beginAtZero: false,
            min: 65,
            max: 100,
            position: "right",
            grid: {
              drawOnChartArea: false,
            },
            title: {
              display: true,
              text: "Completion Rate (%)",
            },
          },
          x: {
            grid: {
              display: false,
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
        let data;

        switch (period) {
          case "week":
            data = weeklyData;
            break;
          case "month":
            data = monthlyData;
            break;
          case "year":
            data = yearlyData;
            break;
        }

        modulePerformanceChart.data.labels = data.labels;
        modulePerformanceChart.data.datasets = data.datasets;
        modulePerformanceChart.update();
      });
    });
  }

  // Student Distribution Chart
  const moduleStudentDistributionCtx = document.getElementById(
    "moduleStudentDistributionChart"
  );

  if (moduleStudentDistributionCtx) {
    new Chart(moduleStudentDistributionCtx, {
      type: "doughnut",
      data: {
        labels: ["Completed", "In Progress", "Not Started"],
        datasets: [
          {
            data: [715, 85, 42],
            backgroundColor: ["#10b981", "#3b82f6", "#9ca3af"],
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
              boxWidth: 12,
            },
          },
        },
        cutout: "70%",
      },
    });
  }

  // Program Distribution Chart
  const programDistributionCtx = document.getElementById(
    "programDistributionChart"
  );

  if (programDistributionCtx) {
    new Chart(programDistributionCtx, {
      type: "bar",
      data: {
        labels: ["MBBS", "BDS", "Nursing", "Pharmacy", "Physio", "Ayurvedic"],
        datasets: [
          {
            label: "Students",
            data: [450, 160, 95, 75, 42, 20],
            backgroundColor: [
              "#82272e",
              "#9f1239",
              "#be123c",
              "#e11d48",
              "#f43f5e",
              "#fb7185",
            ],
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
          y: {
            beginAtZero: true,
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
            title: {
              display: true,
              text: "Number of Students",
            },
          },
          x: {
            grid: {
              display: false,
            },
          },
        },
      },
    });
  }

  // Time Analysis Chart
  const timeAnalysisCtx = document.getElementById("timeAnalysisChart");

  if (timeAnalysisCtx) {
    new Chart(timeAnalysisCtx, {
      type: "horizontalBar",
      data: {
        labels: [
          "Heart Anatomy",
          "Cardiac Physiology",
          "ECG Interpretation",
          "Congenital Defects",
          "Valvular Disease",
        ],
        datasets: [
          {
            label: "Average Time (minutes)",
            data: [45, 65, 80, 55, 60],
            backgroundColor: "#82272e",
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
            title: {
              display: true,
              text: "Time (minutes)",
            },
          },
          y: {
            grid: {
              display: false,
            },
          },
        },
      },
    });
  }

  // Topic search
  const topicSearch = document.querySelector(
    ".module-table-card .search-input"
  );
  if (topicSearch) {
    topicSearch.addEventListener("input", function () {
      const searchTerm = this.value.toLowerCase();
      const tableRows = document.querySelectorAll(
        ".module-table-card tbody tr"
      );

      tableRows.forEach((row) => {
        const topicName = row
          .querySelector("td:first-child")
          .textContent.toLowerCase();
        if (topicName.includes(searchTerm)) {
          row.style.display = "";
        } else {
          row.style.display = "none";
        }
      });
    });
  }

  // Student filter
  const studentFilter = document.querySelector(
    ".module-table-card .filter-select"
  );
  if (studentFilter) {
    studentFilter.addEventListener("change", function () {
      const filter = this.value;
      const tableRows = document.querySelectorAll(
        ".module-table-card:nth-of-type(4) tbody tr"
      );

      tableRows.forEach((row) => {
        const status = row
          .querySelector(".status-badge")
          .textContent.toLowerCase();

        if (
          filter === "all" ||
          (filter === "completed" && status === "completed") ||
          (filter === "in-progress" && status === "in progress") ||
          (filter === "not-started" && status === "not started")
        ) {
          row.style.display = "";
        } else {
          row.style.display = "none";
        }
      });
    });
  }

  // Pagination
  const pageButtons = document.querySelectorAll(
    ".module-table-card .page-number"
  );
  pageButtons.forEach((button) => {
    button.addEventListener("click", function () {
      pageButtons.forEach((btn) => btn.classList.remove("active"));
      this.classList.add("active");

      // In a real app, this would load the appropriate page of data
      showNotification(`Navigated to page ${this.textContent}`);
    });
  });

  const prevPageBtn = document.querySelector(".module-table-card .prev-page");
  if (prevPageBtn) {
    prevPageBtn.addEventListener("click", function () {
      const activePage = document.querySelector(
        ".module-table-card .page-number.active"
      );
      const pageNumber = parseInt(activePage.textContent);

      if (pageNumber > 1) {
        const prevPage = document.querySelector(
          `.module-table-card .page-number:nth-child(${pageNumber - 1})`
        );
        activePage.classList.remove("active");
        prevPage.classList.add("active");

        // In a real app, this would load the previous page
        showNotification(`Navigated to page ${pageNumber - 1}`);
      }
    });
  }

  const nextPageBtn = document.querySelector(".module-table-card .next-page");
  if (nextPageBtn) {
    nextPageBtn.addEventListener("click", function () {
      const activePage = document.querySelector(
        ".module-table-card .page-number.active"
      );
      const pageNumber = parseInt(activePage.textContent);
      const totalPages = document.querySelectorAll(
        ".module-table-card .page-number"
      ).length;

      if (pageNumber < totalPages) {
        const nextPage = document.querySelector(
          `.module-table-card .page-number:nth-child(${pageNumber + 1})`
        );
        activePage.classList.remove("active");
        nextPage.classList.add("active");

        // In a real app, this would load the next page
        showNotification(`Navigated to page ${pageNumber + 1}`);
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
