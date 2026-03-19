(function () {
  const loginPath = "/login.html";
  const currentPath = window.location.pathname;
  const isLoginPage = currentPath.endsWith(loginPath);
  const PUBLIC_PAGES = new Set([
    "/kitchen-service-view.html",
    "/kitchen-test-view.html",
    "/inventory-remove.html",
    "/about.html",
    "/about-sri-m.html",
    "/sacred-grove.html",
    "/volunteer.html",
    "/faq.html",
    "/volunteer-contact.html",
    "/index.html",
    "/",
  ]);

  const PAGE_ROLE_REQUIREMENTS = {
    "/": ["viewer", "planner", "admin"],
    "/index.html": ["viewer", "planner", "admin"],
    "/retreat-planner-sample.html": ["planner", "admin"],
    "/shopping-list.html": ["planner", "admin"],
    "/recipe-admin.html": ["admin"],
    "/ingredient-admin.html": ["admin"],
    "/user-admin.html": ["admin"],
    "/kitchen-service-view.html": ["viewer", "planner", "admin"],
    "/kitchen-test-view.html": ["viewer", "planner", "admin"],
    "/recipe-scaling.html": ["viewer", "planner", "admin"],
    "/inventory-home.html": ["viewer", "planner", "admin"],
    "/inventory-baseline.html": ["viewer", "planner", "admin"],
    "/inventory-orders.html": ["viewer", "planner", "admin"],
    "/inventory-receiving.html": ["viewer", "planner", "admin"],
    "/inventory-add.html": ["viewer", "planner", "admin"],
    "/inventory-remove.html": ["viewer", "planner", "admin"],
    "/inventory.html": ["viewer", "planner", "admin"],
    "/retreat-inventory.html": ["viewer", "planner", "admin"],
    "/change-password.html": ["viewer", "planner", "admin"],
    "/kitchen.html": ["viewer", "planner", "admin"],
    "/about.html": ["viewer", "planner", "admin"],
    "/about-sri-m.html": ["viewer", "planner", "admin"],
    "/sacred-grove.html": ["viewer", "planner", "admin"],
    "/volunteer.html": ["viewer", "planner", "admin"],
    "/faq.html": ["viewer", "planner", "admin"],
    "/volunteer-contact.html": ["viewer", "planner", "admin"],
  };

  function resolveApiBase() {
    const queryValue = new URLSearchParams(window.location.search).get("api");
    const base = queryValue && queryValue.trim() ? queryValue.trim() : window.location.origin;
    return base.replace(/\/+$/, "");
  }

  const API_BASE = resolveApiBase();

  function apiUrl(path) {
    return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  }

  function redirectToLogin() {
    const params = new URLSearchParams();
    params.set("next", `${window.location.pathname}${window.location.search}`);
    const apiOverride = new URLSearchParams(window.location.search).get("api");
    if (apiOverride && apiOverride.trim() && apiOverride.trim() !== window.location.origin) {
      params.set("api", apiOverride.trim());
    }
    window.location.href = `${loginPath}?${params.toString()}`;
  }

  function buildLoginHref() {
    const params = new URLSearchParams();
    params.set("next", `${window.location.pathname}${window.location.search}`);
    const apiOverride = new URLSearchParams(window.location.search).get("api");
    if (apiOverride && apiOverride.trim() && apiOverride.trim() !== window.location.origin) {
      params.set("api", apiOverride.trim());
    }
    return `${loginPath}?${params.toString()}`;
  }

  function buildChangePasswordHref() {
    const params = new URLSearchParams();
    const apiOverride = new URLSearchParams(window.location.search).get("api");
    if (apiOverride && apiOverride.trim() && apiOverride.trim() !== window.location.origin) {
      params.set("api", apiOverride.trim());
    }
    const query = params.toString();
    return `/change-password.html${query ? `?${query}` : ""}`;
  }

  function routeForRole(role) {
    return "/index.html";
  }

  function isRoleAllowedForPage(pathname, role) {
    const required = PAGE_ROLE_REQUIREMENTS[pathname];
    if (!required) {
      return true;
    }
    return required.includes(role);
  }

  function resolvePathnameFromHref(href) {
    try {
      return new URL(href, window.location.href).pathname;
    } catch (_error) {
      return null;
    }
  }

  function shouldShowPathForRole(pathname, role) {
    if (!pathname) {
      return true;
    }
    if (pathname === loginPath) {
      return true;
    }
    const required = PAGE_ROLE_REQUIREMENTS[pathname];
    if (required) {
      if (!role) {
        return PUBLIC_PAGES.has(pathname);
      }
      return required.includes(role);
    }
    if (!role) {
      return PUBLIC_PAGES.has(pathname);
    }
    return true;
  }

  function syncActiveNavLink() {
    const links = Array.from(document.querySelectorAll(".navbar .nav-link[href]"));
    links.forEach((link) => link.classList.remove("active"));

    const dropdownItems = Array.from(document.querySelectorAll(".navbar .dropdown-item[href]"));
    dropdownItems.forEach((item) => item.classList.remove("active"));

    const routeCandidates = currentPath === "/" ? ["/", "/index.html"] : [currentPath];

    const activeLinks = links.filter((link) => {
      const parent = link.closest(".nav-item");
      if (parent && parent.classList.contains("d-none")) {
        return false;
      }
      if (link.classList.contains("d-none")) {
        return false;
      }
      const path = resolvePathnameFromHref(link.getAttribute("href") || "");
      return path && routeCandidates.includes(path);
    });
    activeLinks.forEach((link) => link.classList.add("active"));

    const activeDropdownItems = dropdownItems.filter((item) => {
      if (item.classList.contains("d-none")) {
        return false;
      }
      const parentDropdown = item.closest(".nav-item.dropdown");
      if (parentDropdown && parentDropdown.classList.contains("d-none")) {
        return false;
      }
      const path = resolvePathnameFromHref(item.getAttribute("href") || "");
      return path && routeCandidates.includes(path);
    });

    activeDropdownItems.forEach((activeDropdownItem) => {
      activeDropdownItem.classList.add("active");
      const parentToggle = activeDropdownItem.closest(".dropdown")?.querySelector(".dropdown-toggle");
      if (parentToggle) {
        parentToggle.classList.add("active");
      }
    });

  }

  function ensureGuestLoginCta(role) {
    const navList = document.querySelector(".navbar .navbar-nav");
    if (!navList) {
      return;
    }
    let item = document.getElementById("guestLoginNavItem");
    if (role || isLoginPage) {
      if (item) {
        item.remove();
      }
      return;
    }
    if (!item) {
      item = document.createElement("li");
      item.id = "guestLoginNavItem";
      item.className = "nav-item ms-lg-2";
      const anchor = document.createElement("a");
      anchor.className = "btn btn-sm btn-primary px-3";
      anchor.textContent = "Sign In";
      item.appendChild(anchor);
      navList.appendChild(item);
    }
    const link = item.querySelector("a");
    if (link) {
      link.href = buildLoginHref();
    }
  }

  function applyNavVisibility(role) {
    const links = Array.from(document.querySelectorAll(".navbar .nav-link[href]"));
    links.forEach((link) => {
      const path = resolvePathnameFromHref(link.getAttribute("href") || "");
      const show = shouldShowPathForRole(path, role || null);
      const parent = link.closest(".nav-item");
      if (parent && !parent.classList.contains("dropdown")) {
        parent.classList.toggle("d-none", !show);
      } else if (!parent) {
        link.classList.toggle("d-none", !show);
      }
    });

    const dropdownItems = Array.from(document.querySelectorAll(".navbar .dropdown-item[href]"));
    dropdownItems.forEach((item) => {
      const path = resolvePathnameFromHref(item.getAttribute("href") || "");
      const show = shouldShowPathForRole(path, role || null);
      item.classList.toggle("d-none", !show);
    });

    // Defensive guard: Ingredients belongs under Kitchen nav, never under Admin.
    const adminDropdowns = Array.from(document.querySelectorAll(".navbar .nav-item.dropdown"));
    adminDropdowns.forEach((dropdown) => {
      const isAdminMenu = Boolean(dropdown.querySelector(".dropdown-toggle .fa-gear"));
      if (!isAdminMenu) {
        return;
      }
      const ingredientLinks = dropdown.querySelectorAll(".dropdown-item[href='ingredient-admin.html']");
      ingredientLinks.forEach((item) => item.classList.add("d-none"));
    });

    const dropdowns = Array.from(document.querySelectorAll(".navbar .nav-item.dropdown"));
    dropdowns.forEach((dropdown) => {
      const visibleItems = dropdown.querySelectorAll(".dropdown-item:not(.d-none)");
      dropdown.classList.toggle("d-none", visibleItems.length === 0);
    });

    const kitchenSubnav = document.querySelector(".kitchen-subnav");
    const kitchenTabs = Array.from(document.querySelectorAll(".kitchen-subnav a[href]"));
    kitchenTabs.forEach((tab) => {
      const path = resolvePathnameFromHref(tab.getAttribute("href") || "");
      const show = shouldShowPathForRole(path, role || null);
      tab.classList.toggle("d-none", !show);
    });
    if (kitchenSubnav) {
      const visibleTabs = kitchenSubnav.querySelectorAll("a[href]:not(.d-none)");
      kitchenSubnav.classList.toggle("d-none", visibleTabs.length === 0);
    }

    if (!role) {
      const authUserLabel = document.getElementById("authUserLabel");
      if (authUserLabel) {
        authUserLabel.classList.add("d-none");
      }
      const changePasswordBtn = document.getElementById("changePasswordBtn");
      if (changePasswordBtn) {
        changePasswordBtn.classList.add("d-none");
      }
      const logoutBtn = document.getElementById("logoutBtn");
      if (logoutBtn) {
        logoutBtn.classList.add("d-none");
      }
    }

    ensureGuestLoginCta(role || null);
    syncActiveNavLink();
  }

  function initMobileNavbarAutoClose() {
    const navCollapse = document.getElementById("navbarContent");
    if (!navCollapse || !window.bootstrap || !window.bootstrap.Collapse) {
      return;
    }
    if (navCollapse.dataset.mobileAutoCloseBound === "1") {
      return;
    }
    navCollapse.dataset.mobileAutoCloseBound = "1";

    navCollapse.addEventListener("click", (event) => {
      const target = event.target instanceof Element
        ? event.target.closest("a[href], button#logoutBtn")
        : null;
      if (!target) {
        return;
      }

      // Keep navbar open when the tap is only expanding a dropdown menu.
      if (target.matches("[data-bs-toggle='dropdown']")) {
        return;
      }

      if (window.matchMedia("(min-width: 992px)").matches) {
        return;
      }

      const collapse = window.bootstrap.Collapse.getOrCreateInstance(navCollapse, { toggle: false });
      collapse.hide();
    });
  }

  async function parseJsonSafe(response) {
    try {
      return await response.json();
    } catch (_error) {
      return null;
    }
  }

  function patchFetchForSessionExpiry() {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (...args) => {
      const response = await originalFetch(...args);
      try {
        const input = args[0];
        const rawUrl =
          typeof input === "string"
            ? input
            : input instanceof Request
              ? input.url
              : String(input || "");
        const resolvedUrl = new URL(rawUrl, window.location.href);
        const isApi = resolvedUrl.pathname.startsWith("/api");
        const isLoginEndpoint = resolvedUrl.pathname === "/api/auth/login";
        if (!isLoginPage && isApi && !isLoginEndpoint && response.status === 401) {
          redirectToLogin();
        }
      } catch (_error) {
        // Ignore URL parse errors and return response as-is.
      }
      return response;
    };
  }

  async function loadCurrentUser() {
    const response = await fetch(apiUrl("/api/auth/me"), {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      return null;
    }
    return parseJsonSafe(response);
  }

  function applyUserUi(user) {
    const label = document.getElementById("authUserLabel");
    if (label) {
      label.textContent = `${user.username} (${user.role})`;
      label.classList.remove("d-none");
    }

    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
      const parent = logoutBtn.parentElement;
      if (parent) {
        let changePasswordBtn = document.getElementById("changePasswordBtn");
        if (!changePasswordBtn && currentPath !== "/change-password.html") {
          changePasswordBtn = document.createElement("a");
          changePasswordBtn.id = "changePasswordBtn";
          changePasswordBtn.className = "btn btn-sm btn-outline-primary d-none";
          parent.insertBefore(changePasswordBtn, logoutBtn);
        }
        if (changePasswordBtn) {
          changePasswordBtn.href = buildChangePasswordHref();
          changePasswordBtn.textContent = "Change Password";
          changePasswordBtn.classList.remove("d-none");
        }
      }

      logoutBtn.classList.remove("d-none");
      logoutBtn.addEventListener("click", async () => {
        try {
          await fetch(apiUrl("/api/auth/logout"), {
            method: "POST",
            credentials: "include",
          });
        } finally {
          redirectToLogin();
        }
      });
    }
  }

  async function initLoginPage() {
    const form = document.getElementById("loginForm");
    const usernameInput = document.getElementById("loginUsername");
    const passwordInput = document.getElementById("loginPassword");
    const status = document.getElementById("loginStatus");
    const bootstrapHint = document.getElementById("bootstrapHint");

    const existing = await loadCurrentUser();
    if (existing && existing.role) {
      const next = new URLSearchParams(window.location.search).get("next");
      window.location.href = next || routeForRole(existing.role);
      return;
    }

    applyNavVisibility(null);

    try {
      const bootstrapResponse = await fetch(apiUrl("/api/auth/bootstrap-status"), {
        method: "GET",
        credentials: "include",
      });
      if (bootstrapResponse.ok) {
        const bootstrap = await parseJsonSafe(bootstrapResponse);
        if (bootstrapHint && bootstrap && bootstrap.has_users === false) {
          bootstrapHint.textContent =
            "No users configured. Set bootstrap admin env vars and redeploy.";
          bootstrapHint.classList.remove("d-none");
        }
      }
    } catch (_error) {
      // Ignore bootstrap status failures on login page.
    }

    if (!form || !usernameInput || !passwordInput || !status) {
      return;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      status.textContent = "Signing in...";
      status.className = "small text-muted mt-2";

      try {
        const response = await fetch(apiUrl("/api/auth/login"), {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: usernameInput.value.trim(),
            password: passwordInput.value,
          }),
        });

        if (!response.ok) {
          const errorPayload = await parseJsonSafe(response);
          const detail = errorPayload && errorPayload.detail ? errorPayload.detail : "Login failed.";
          throw new Error(detail);
        }

        const payload = await parseJsonSafe(response);
        const next = new URLSearchParams(window.location.search).get("next");
        window.location.href = next || routeForRole(payload?.role);
      } catch (error) {
        status.textContent = error instanceof Error ? error.message : String(error);
        status.className = "small text-danger mt-2";
      }
    });
  }

  async function initProtectedPage() {
    patchFetchForSessionExpiry();
    const user = await loadCurrentUser();
    if (!user || !user.role) {
      redirectToLogin();
      return;
    }

    if (!isRoleAllowedForPage(currentPath, user.role)) {
      window.location.href = routeForRole(user.role);
      return;
    }

    applyNavVisibility(user.role);
    applyUserUi(user);
    window.retreatAuthUser = user;
  }

  initMobileNavbarAutoClose();

  if (isLoginPage) {
    void initLoginPage();
  } else if (PUBLIC_PAGES.has(currentPath)) {
    // Public read-only pages should render without forcing auth.
    void loadCurrentUser()
      .then((user) => {
        if (user && user.role) {
          applyNavVisibility(user.role);
          applyUserUi(user);
          window.retreatAuthUser = user;
          return;
        }
        applyNavVisibility(null);
      })
      .catch(() => {
        applyNavVisibility(null);
      });
  } else {
    void initProtectedPage();
  }
})();
