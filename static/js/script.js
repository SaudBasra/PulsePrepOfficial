document.addEventListener("DOMContentLoaded", function () {
  // Select elements
  const mobileMenuBtn = document.querySelector(".mobile-menu-btn");
  const navMenu = document.querySelector(".nav-menu");
  const body = document.body;

  // Create overlay element if it doesn't exist
  if (!document.querySelector(".overlay")) {
    const overlay = document.createElement("div");
    overlay.className = "overlay";
    document.body.appendChild(overlay);
  }

  const overlay = document.querySelector(".overlay");

  // Toggle mobile menu
  mobileMenuBtn.addEventListener("click", function () {
    navMenu.classList.toggle("show");
    overlay.classList.toggle("show");

    // Toggle icon between bars and X
    if (navMenu.classList.contains("show")) {
      mobileMenuBtn.innerHTML = '<i class="fas fa-times"></i>';
      body.style.overflow = "hidden"; // Prevent scrolling
    } else {
      mobileMenuBtn.innerHTML = '<i class="fas fa-bars"></i>';
      body.style.overflow = ""; // Enable scrolling
    }
  });

  // Close menu when clicking overlay
  overlay.addEventListener("click", function () {
    navMenu.classList.remove("show");
    overlay.classList.remove("show");
    mobileMenuBtn.innerHTML = '<i class="fas fa-bars"></i>';
    body.style.overflow = "";
  });

  // Close menu on window resize (if desktop view)
  window.addEventListener("resize", function () {
    if (window.innerWidth > 820) {
      navMenu.classList.remove("show");
      overlay.classList.remove("show");
      mobileMenuBtn.innerHTML = '<i class="fas fa-bars"></i>';
      body.style.overflow = "";
    }
  });

  // Set active state for current page
  const currentPage = window.location.pathname.split("/").pop();
  const navLinks = document.querySelectorAll(".nav-menu a");

  navLinks.forEach((link) => {
    const linkPage = link.getAttribute("href");
    if (
      linkPage === currentPage ||
      (currentPage === "" && linkPage === "index.html") ||
      (currentPage === "/" && linkPage === "index.html")
    ) {
      link.classList.add("active");
    }
  });

  // Optional: Add smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();

      const targetId = this.getAttribute("href");
      if (targetId === "#") return;

      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        // Close mobile menu if open
        if (navMenu.classList.contains("show")) {
          navMenu.classList.remove("show");
          overlay.classList.remove("show");
          mobileMenuBtn.innerHTML = '<i class="fas fa-bars"></i>';
          body.style.overflow = "";
        }

        // Scroll to the element
        targetElement.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });
});
