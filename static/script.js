// ============================
// MAIN JS FILE (DARK MODE + SLIDER)
// ============================

document.addEventListener("DOMContentLoaded", () => {

  /* ============================
     DARK MODE (SYNCED)
  ============================ */

  const desktopToggle = document.getElementById("darkToggle");
  const mobileToggle = document.getElementById("darkToggleMobile");

  function setTheme(isDark) {
    if (isDark) {
      document.body.classList.add("dark");
      localStorage.setItem("mode", "dark");
    } else {
      document.body.classList.remove("dark");
      localStorage.setItem("mode", "light");
    }
    if (desktopToggle) desktopToggle.checked = isDark;
    if (mobileToggle) mobileToggle.checked = isDark;
  }

  // Load saved mode
  const savedMode = localStorage.getItem("mode");
  setTheme(savedMode === "dark");

  if (desktopToggle) {
    desktopToggle.addEventListener("change", () => setTheme(desktopToggle.checked));
  }
  if (mobileToggle) {
    mobileToggle.addEventListener("change", () => setTheme(mobileToggle.checked));
  }

  /* ============================
     MOBILE SIDEBAR
  ============================ */

  const sidebar = document.getElementById("mobileSidebar");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebarClose = document.getElementById("sidebarClose");
  const sidebarOverlay = document.getElementById("sidebarOverlay");

  function openSidebar() {
    sidebar.classList.add("active");
    sidebarOverlay.classList.add("active");
    document.body.style.overflow = "hidden"; // Prevent scrolling
  }

  function closeSidebar() {
    sidebar.classList.remove("active");
    sidebarOverlay.classList.remove("active");
    document.body.style.overflow = "auto"; // Restore scrolling
  }

  if (sidebarToggle) sidebarToggle.addEventListener("click", openSidebar);
  if (sidebarClose) sidebarClose.addEventListener("click", closeSidebar);
  if (sidebarOverlay) sidebarOverlay.addEventListener("click", closeSidebar);


  /* ============================
     BANNER SLIDER
  ============================ */

  let slideIndex = 0;
  const slides = document.getElementsByClassName("slides");

  function showSlides() {

    if (slides.length === 0) return;

    // Hide all
    for (let i = 0; i < slides.length; i++) {
      slides[i].style.display = "none";
    }

    slideIndex++;

    if (slideIndex > slides.length) {
      slideIndex = 1;
    }

    slides[slideIndex - 1].style.display = "block";

    setTimeout(showSlides, 3000); // 3 sec
  }

  showSlides();


  /* ============================
     OPTIONAL: SMOOTH SCROLL
  ============================ */

  const links = document.querySelectorAll("a[href^='#']");

  links.forEach(link => {

    link.addEventListener("click", e => {

      e.preventDefault();

      const target = document.querySelector(
        link.getAttribute("href")
      );

      if (target) {
        target.scrollIntoView({
          behavior: "smooth"
        });
      }

    });

  });

  /* ============================
     TOAST DISMISSAL
  ============================ */

  const toasts = document.querySelectorAll('.toast');

  toasts.forEach(toast => {
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = '0.5s ease-in-out';
      setTimeout(() => toast.remove(), 500);
    }, 4000); // 4 sec
  });

  /* ============================
     LOADING OVERLAY
  ============================ */

  window.showLoading = function () {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) {
      overlay.style.display = "flex";
    }
  };

  window.hideLoading = function () {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) {
      overlay.style.display = "none";
    }
  };

});
