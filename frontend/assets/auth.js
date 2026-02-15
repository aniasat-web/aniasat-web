(function () {
  const loginPath = "/login.html";
  const currentPath = window.location.pathname;
  const isLoginPage = currentPath.endsWith(loginPath);
  const PUBLIC_PAGES = new Set(["/kitchen-service-view.html"]);

  const PAGE_ROLE_REQUIREMENTS = {
    "/retreat-planner-sample.html": ["planner", "admin"],
    "/recipe-admin.html": ["admin"],
    "/user-admin.html": ["admin"],
    "/kitchen-service-view.html": ["viewer", "planner", "admin"],
    "/recipe-scaling.html": ["viewer", "planner", "admin"],
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

  function routeForRole(role) {
    if (role === "planner" || role === "admin") {
      return "/retreat-planner-sample.html";
    }
    return "/kitchen-service-view.html";
  }

  function isRoleAllowedForPage(pathname, role) {
    const required = PAGE_ROLE_REQUIREMENTS[pathname];
    if (!required) {
      return true;
    }
    return required.includes(role);
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

    applyUserUi(user);
    window.retreatAuthUser = user;
  }

  if (isLoginPage) {
    void initLoginPage();
  } else if (PUBLIC_PAGES.has(currentPath)) {
    // Public read-only pages should render without forcing auth.
    void loadCurrentUser()
      .then((user) => {
        if (user && user.role) {
          applyUserUi(user);
          window.retreatAuthUser = user;
        }
      })
      .catch(() => null);
  } else {
    void initProtectedPage();
  }
})();
