(function () {
  const STYLE_ID = "kitchenGuestAccessStyles";

  function resolveApiBase() {
    const queryValue = new URLSearchParams(window.location.search).get("api");
    const base = queryValue && queryValue.trim() ? queryValue.trim() : window.location.origin;
    return base.replace(/\/+$/, "");
  }

  function apiUrl(path) {
    const base = resolveApiBase();
    return `${base}${path.startsWith("/") ? path : `/${path}`}`;
  }

  function buildLoginHref() {
    const params = new URLSearchParams();
    params.set("next", `${window.location.pathname}${window.location.search}`);
    const apiOverride = new URLSearchParams(window.location.search).get("api");
    if (apiOverride && apiOverride.trim() && apiOverride.trim() !== window.location.origin) {
      params.set("api", apiOverride.trim());
    }
    return `/login.html?${params.toString()}`;
  }

  async function readErrorDetail(response) {
    const text = await response.text();
    if (!text) {
      return `HTTP ${response.status}`;
    }
    try {
      const parsed = JSON.parse(text);
      if (parsed && parsed.detail) {
        return parsed.detail;
      }
    } catch (_error) {
      // Ignore invalid JSON and fall back to raw text.
    }
    return text;
  }

  async function fetchAccessStatus(scope) {
    const response = await fetch(apiUrl(`/api/kitchen-access/${encodeURIComponent(scope)}`), {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(await readErrorDetail(response));
    }
    return response.json();
  }

  async function loginWithCode(scope, accessCode) {
    const response = await fetch(apiUrl(`/api/kitchen-access/${encodeURIComponent(scope)}/login`), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accessCode }),
    });
    if (!response.ok) {
      throw new Error(await readErrorDetail(response));
    }
    return response.json();
  }

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) {
      return;
    }
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .kitchen-access-overlay {
        position: fixed;
        inset: 0;
        z-index: 1080;
        background: rgba(24, 24, 27, 0.58);
        backdrop-filter: blur(6px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.5rem;
      }
      .kitchen-access-card {
        width: min(100%, 32rem);
        border-radius: 1.25rem;
        background: #fffdf8;
        border: 1px solid rgba(217, 119, 6, 0.18);
        box-shadow: 0 24px 60px rgba(15, 23, 42, 0.28);
        padding: 1.5rem;
      }
      .kitchen-access-kicker {
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 800;
        color: #b45309;
      }
      .kitchen-access-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
      }
      .kitchen-access-status {
        min-height: 1.25rem;
      }
    `;
    document.head.appendChild(style);
  }

  function createOverlay(options) {
    const overlay = document.createElement("div");
    overlay.className = "kitchen-access-overlay";
    overlay.innerHTML = `
      <div class="kitchen-access-card">
        <div class="kitchen-access-kicker mb-2">Shared Kitchen Access</div>
        <h1 class="h4 fw-bold mb-2">${options.title}</h1>
        <p class="text-muted mb-3">${options.description}</p>
        <div id="kitchenAccessGuestHelp" class="small text-muted mb-3"></div>
        <div id="kitchenAccessFormWrap">
          <label class="form-label fw-semibold" for="kitchenAccessCodeInput">Shared Access Code</label>
          <input id="kitchenAccessCodeInput" type="password" class="form-control mb-3" placeholder="Enter shared code" autocomplete="one-time-code" />
        </div>
        <div id="kitchenAccessStatus" class="small kitchen-access-status mb-3 text-danger"></div>
        <div class="kitchen-access-actions">
          <button id="kitchenAccessSubmitBtn" type="button" class="btn btn-primary">Continue</button>
          <button id="kitchenAccessRefreshBtn" type="button" class="btn btn-outline-secondary">Check Again</button>
          <a id="kitchenAccessLoginBtn" class="btn btn-outline-dark" href="${buildLoginHref()}">Sign In</a>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    return {
      overlay,
      guestHelp: overlay.querySelector("#kitchenAccessGuestHelp"),
      formWrap: overlay.querySelector("#kitchenAccessFormWrap"),
      codeInput: overlay.querySelector("#kitchenAccessCodeInput"),
      status: overlay.querySelector("#kitchenAccessStatus"),
      submitBtn: overlay.querySelector("#kitchenAccessSubmitBtn"),
      refreshBtn: overlay.querySelector("#kitchenAccessRefreshBtn"),
    };
  }

  function setStatusMessage(element, message, tone) {
    if (!element) {
      return;
    }
    element.textContent = message || "";
    element.className = `small kitchen-access-status mb-3 text-${tone || "danger"}`;
  }

  function setBusy(elements, disabled) {
    elements.submitBtn.disabled = disabled;
    elements.refreshBtn.disabled = disabled;
    elements.codeInput.disabled = disabled;
  }

  function renderAccessState(elements, payload) {
    const guestEnabled = Boolean(payload && payload.guestAccessEnabled);
    const sessionHours = Number(payload && payload.guestSessionHours) || 24;
    if (guestEnabled) {
      elements.formWrap.classList.remove("d-none");
      elements.submitBtn.classList.remove("d-none");
      elements.guestHelp.textContent = `Enter the shared code to continue. Guest access on this browser lasts about ${sessionHours} hour${sessionHours === 1 ? "" : "s"}.`;
    } else {
      elements.formWrap.classList.add("d-none");
      elements.submitBtn.classList.add("d-none");
      elements.guestHelp.textContent = "Shared-code access is not configured for this page right now. Sign in or ask an admin to set a code in the admin panel.";
    }
  }

  async function ensurePageAccess(options) {
    ensureStyles();
    const scope = String(options && options.scope ? options.scope : "").trim();
    if (!scope) {
      throw new Error("Kitchen access scope is required.");
    }

    const overlay = createOverlay({
      title: options.title || "Kitchen Access Required",
      description: options.description || "Enter the shared code or sign in to continue.",
    });

    async function refreshStatus() {
      const payload = await fetchAccessStatus(scope);
      if (payload && payload.authorized) {
        overlay.overlay.remove();
        return payload;
      }
      renderAccessState(overlay, payload);
      setStatusMessage(overlay.status, "", "danger");
      return null;
    }

    let initial = null;
    try {
      initial = await refreshStatus();
    } catch (error) {
      setStatusMessage(
        overlay.status,
        error instanceof Error ? error.message : String(error),
        "danger",
      );
    }
    if (initial) {
      return initial;
    }

    return new Promise((resolve, reject) => {
      overlay.submitBtn.addEventListener("click", async () => {
        const accessCode = overlay.codeInput.value.trim();
        if (!accessCode) {
          setStatusMessage(overlay.status, "Enter the shared access code first.", "danger");
          overlay.codeInput.focus();
          return;
        }

        setBusy(overlay, true);
        setStatusMessage(overlay.status, "Checking access...", "muted");
        try {
          await loginWithCode(scope, accessCode);
          const payload = await refreshStatus();
          if (payload) {
            resolve(payload);
            return;
          }
          setStatusMessage(overlay.status, "Access was granted, but the page could not verify it. Try again.", "danger");
        } catch (error) {
          setStatusMessage(
            overlay.status,
            error instanceof Error ? error.message : String(error),
            "danger",
          );
        } finally {
          setBusy(overlay, false);
        }
      });

      overlay.refreshBtn.addEventListener("click", async () => {
        setBusy(overlay, true);
        setStatusMessage(overlay.status, "Checking access...", "muted");
        try {
          const payload = await refreshStatus();
          if (payload) {
            resolve(payload);
            return;
          }
          setStatusMessage(overlay.status, "", "danger");
        } catch (error) {
          setStatusMessage(
            overlay.status,
            error instanceof Error ? error.message : String(error),
            "danger",
          );
        } finally {
          setBusy(overlay, false);
        }
      });

      overlay.codeInput.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") {
          return;
        }
        event.preventDefault();
        overlay.submitBtn.click();
      });

      window.addEventListener(
        "beforeunload",
        () => {
          reject(new Error("Page unloaded before kitchen access was granted."));
        },
        { once: true },
      );
    });
  }

  window.kitchenGuestAccess = {
    ensurePageAccess,
  };
})();
