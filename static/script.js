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
      localStorage.setItem("theme", "dark");
    } else {
      document.body.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
    if (desktopToggle) desktopToggle.checked = isDark;
    if (mobileToggle) mobileToggle.checked = isDark;
  }

  // Load saved theme - unification
  const savedTheme = localStorage.getItem("theme") || localStorage.getItem("mode");
  if (savedTheme === "dark") {
    setTheme(true);
  } else if (savedTheme === "light") {
    setTheme(false);
  }

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

  /* ============================
     STABLE DROPDOWN LOGIC
  ============================ */
  const userDropdown = document.querySelector('.nav-user-dropdown');
  const dropdownMenu = document.querySelector('.dropdown-menu');
  let openTimer;

  if (userDropdown && dropdownMenu) {
    // Hover to open
    userDropdown.addEventListener('mouseenter', () => {
      clearTimeout(openTimer);
      dropdownMenu.classList.add('active-dropdown');
    });

    // Hover leave to close (with delay)
    userDropdown.addEventListener('mouseleave', () => {
      openTimer = setTimeout(() => {
        dropdownMenu.classList.remove('active-dropdown');
      }, 800);
    });

    // Click to TOGGLE/CLOSE
    userDropdown.addEventListener('click', (e) => {
      // Don't close if clicking inside the menu items (let the links work)
      if (e.target.closest('.dropdown-menu')) return;

      e.stopPropagation(); // Prevent closing from the "click anywhere" listener below

      const isOpen = dropdownMenu.classList.contains('active-dropdown');
      if (isOpen) {
        dropdownMenu.classList.remove('active-dropdown');
        clearTimeout(openTimer);
      } else {
        dropdownMenu.classList.add('active-dropdown');
      }
    });

    // Click anywhere else to close
    document.addEventListener('click', () => {
      dropdownMenu.classList.remove('active-dropdown');
    });
  }

  /* ============================
     MOBILE BOTTOM NAV: EXPLORE
  ============================ */
  const exploreBtn = document.getElementById('bottomNavExplore');
  const mainSearchInput = document.getElementById('mainSearchInput');

  if (exploreBtn && mainSearchInput) {
    exploreBtn.addEventListener('click', (e) => {
      // Only trigger if we are on a page where the search bar exists and we want to focus it 
      // instead of navigating (e.g., if already on home or products page)
      if (window.innerWidth <= 768) {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => {
          mainSearchInput.focus();
        }, 300); // Wait for scroll
      }
    });
  }

});
