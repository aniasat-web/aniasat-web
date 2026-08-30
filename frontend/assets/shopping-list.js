      const retreatPlanSelect = document.getElementById("retreatPlanSelect");
      const selectAllRetreatsBtn = document.getElementById("selectAllRetreatsBtn");
      const clearRetreatsBtn = document.getElementById("clearRetreatsBtn");
      const phaseSelect = document.getElementById("phaseSelect");
      const generateBtn = document.getElementById("generateBtn");
      const shoppingListSelect = document.getElementById("shoppingListSelect");
      const inlineRenameWrap = document.getElementById("inlineRenameWrap");
      const inlineRenameInput = document.getElementById("inlineRenameInput");
      const inlineRenameSaveBtn = document.getElementById("inlineRenameSaveBtn");
      const inlineRenameCancelBtn = document.getElementById("inlineRenameCancelBtn");
      const loadListBtn = document.getElementById("loadListBtn");
      const deleteListBtn = document.getElementById("deleteListBtn");
      const applyInventoryBtn = document.getElementById("applyInventoryBtn");
      const inventoryCountSelect = document.getElementById("inventoryCountSelect");
      const applyInventoryCountBtn = document.getElementById("applyInventoryCountBtn");
      const applyInventoryBox = document.getElementById("applyInventoryBox");
      const applyInventoryHint = document.getElementById("applyInventoryHint");
      const refreshListsBtn = document.getElementById("refreshListsBtn");
      const newManualListBtn = document.getElementById("newManualListBtn");
      const addItemNameInput = document.getElementById("addItemNameInput");
      const addItemQtyInput = document.getElementById("addItemQtyInput");
      const addItemUnitSelect = document.getElementById("addItemUnitSelect");
      const addItemBtn = document.getElementById("addItemBtn");
      const addItemIngredientOptions = document.getElementById("addItemIngredientOptions");
      const shoppingBody = document.getElementById("shoppingBody");
      const shoppingTableWrap = document.querySelector(".shopping-table-wrap");
      const statusPill = document.getElementById("statusPill");
      const metricItems = document.getElementById("metricItems");
      const metricOrdered = document.getElementById("metricOrdered");
      const metricReceived = document.getElementById("metricReceived");
      const metricStatus = document.getElementById("metricStatus");
      const groupModeSelect = document.getElementById("groupModeSelect");
      const hideZeroToBuyCheck = document.getElementById("hideZeroToBuyCheck");
      const shoppingCategoryFilter = document.getElementById("shoppingCategoryFilter");
      const sourceBreakdownHint = document.getElementById("sourceBreakdownHint");
      const pickupSelectionSummary = document.getElementById("pickupSelectionSummary");
      const pickupListNameInput = document.getElementById("pickupListNameInput");
      const pickupListVendorSelect = document.getElementById("pickupListVendorSelect");
      const pickupListAssigneeInput = document.getElementById("pickupListAssigneeInput");
      const pickupListDateInput = document.getElementById("pickupListDateInput");
      const pickupListNotesInput = document.getElementById("pickupListNotesInput");
      const selectVendorPickupItemsBtn = document.getElementById("selectVendorPickupItemsBtn");
      const clearPickupSelectionBtn = document.getElementById("clearPickupSelectionBtn");
      const createPickupListBtn = document.getElementById("createPickupListBtn");
      const pickupListCards = document.getElementById("pickupListCards");
      const pickupSelectVisibleCheck = document.getElementById("pickupSelectVisibleCheck");
      const activePickupBanner = document.getElementById("activePickupBanner");
      const activePickupTitle = document.getElementById("activePickupTitle");
      const activePickupMeta = document.getElementById("activePickupMeta");
      const activePickupMissing = document.getElementById("activePickupMissing");
      const downloadPickupPdfBtn = document.getElementById("downloadPickupPdfBtn");
      const closePickupViewBtn = document.getElementById("closePickupViewBtn");
      const deletePickupListBtn = document.getElementById("deletePickupListBtn");

      let API_BASE = resolveApiBase();
      const DEFAULT_API_BASE = window.location.origin.replace(/\/+$/, "");
      const ALL_RETREATS_VALUE = "__ALL_RETREATS__";
      const RENAME_SELECTED_LIST_VALUE = "__RENAME_SELECTED_LIST__";
      let vendors = [];
      let shoppingLists = [];
      let kitchenInventoryCounts = [];
      let ingredientCatalogNames = [];
      const ADD_ITEM_UNITS = ["kg", "g", "lb", "oz", "l", "ml", "each", "piece", "packet", "bag", "can", "bunch", "box", "bottle", "jar"];
      let activeListId = null;
      let activeListPhase = null;
      let activeShoppingDetail = null;
      let currentGroupMode = "category";
      let dropdownSelectedListId = null;
      let renameEditingListId = null;
      let selectedIngredientCategory = null;
      let pickupLists = [];
      let activePickupListDetail = null;
      const selectedPickupItemIds = new Set();
      const MASS_UNITS_TO_G = {
        g: 1,
        kg: 1000,
        lb: 453.59237,
        oz: 28.349523125,
      };
      const VOLUME_UNITS_TO_ML = {
        ml: 1,
        l: 1000,
        "fl oz": 29.5735295625,
        qt: 946.352946,
        gal: 3785.411784,
      };
      const METRIC_ORDERED_UNITS = new Set(["g", "kg", "ml", "l"]);
      const MASS_ORDERED_UNIT_OPTIONS = ["kg", "lb", "oz", "bag", "box", "case", "each"];
      const VOLUME_ORDERED_UNIT_OPTIONS = ["l", "gal", "qt", "fl oz", "jug", "bottle", "case", "each"];
      const COUNT_ORDERED_UNIT_OPTIONS = ["each", "bag", "box", "case", "can", "packet", "bottle", "jug"];
      const ALWAYS_AVAILABLE_ORDERED_UNITS = ["kg", "l"];

      function resolveApiBase() {
        const queryValue = new URLSearchParams(window.location.search).get("api");
        const base = queryValue && queryValue.trim() ? queryValue.trim() : window.location.origin;
        return base.replace(/\/+$/, "");
      }

      function apiUrl(path) {
        return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
      }

      function normalizeUnit(unit) {
        const value = String(unit || "").trim().toLowerCase();
        if (!value) {
          return "";
        }
        const aliases = {
          cups: "cup",
          gms: "g",
          kilogram: "kg",
          kilograms: "kg",
          kilo: "kg",
          kilos: "kg",
          gram: "g",
          grams: "g",
          liter: "l",
          liters: "l",
          litre: "l",
          litres: "l",
          milliliter: "ml",
          milliliters: "ml",
          millilitre: "ml",
          millilitres: "ml",
          tablespoon: "tbsp",
          tablespoons: "tbsp",
          tbs: "tbsp",
          teaspoon: "tsp",
          teaspoons: "tsp",
          tsb: "tsp",
          pound: "lb",
          pounds: "lb",
          lbs: "lb",
          ounce: "oz",
          ounces: "oz",
          "fluid ounce": "fl oz",
          "fluid ounces": "fl oz",
          floz: "fl oz",
          "fl. oz.": "fl oz",
          quart: "qt",
          quarts: "qt",
          gallon: "gal",
          gallons: "gal",
          eaches: "each",
          ea: "each",
          pieces: "piece",
          packets: "packet",
          packs: "pack",
          pk: "pack",
          pks: "pack",
          cans: "can",
          bunches: "bunch",
          loaves: "loaf",
          sprigs: "sprig",
          springs: "sprig",
          leaves: "leaf",
          bags: "bag",
          boxes: "box",
          cases: "case",
          bottles: "bottle",
          jugs: "jug",
          jars: "jar",
          cartons: "carton",
          tubs: "tub",
          packages: "package",
          pinches: "pinch",
          pod: "piece",
          pods: "piece",
          clove: "piece",
          cloves: "piece",
        };
        return aliases[value] || value;
      }

      function usingApiOverride() {
        return API_BASE !== DEFAULT_API_BASE;
      }

      function switchToDefaultApiBase() {
        API_BASE = DEFAULT_API_BASE;
      }

      function setStatus(message, mode = "info", options = {}) {
        const { busy = false } = options;
        statusPill.textContent = message;
        statusPill.classList.remove("info", "ok", "err");
        statusPill.classList.add(mode);
        statusPill.classList.toggle("is-busy", busy);
        statusPill.classList.toggle("ui-busy-pulse", busy);
      }

      function triggerFadeIn(node) {
        if (!node) {
          return;
        }
        node.classList.remove("ui-fade-enter");
        void node.offsetWidth;
        node.classList.add("ui-fade-enter");
      }

      function setMetricValue(node, value) {
        if (!node) {
          return;
        }
        const nextValue = String(value);
        if (node.textContent === nextValue) {
          return;
        }
        node.textContent = nextValue;
        node.classList.remove("value-updated");
        void node.offsetWidth;
        node.classList.add("value-updated");
      }

      function setButtonBusy(button, isBusy, busyLabel) {
        if (!(button instanceof HTMLButtonElement)) {
          return;
        }
        if (isBusy) {
          if (!button.dataset.originalHtml) {
            button.dataset.originalHtml = button.innerHTML;
          }
          if (!button.dataset.busyWasDisabled) {
            button.dataset.busyWasDisabled = button.disabled ? "1" : "0";
          }
          button.disabled = true;
          button.innerHTML = `<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>${busyLabel}`;
          return;
        }
        const wasDisabled = button.dataset.busyWasDisabled === "1";
        if (button.dataset.originalHtml) {
          button.innerHTML = button.dataset.originalHtml;
          delete button.dataset.originalHtml;
        }
        delete button.dataset.busyWasDisabled;
        button.disabled = wasDisabled;
      }

      function renderShoppingSkeletonRows(rowCount = 9) {
        shoppingBody.innerHTML = "";
        if (shoppingTableWrap) {
          shoppingTableWrap.classList.add("is-loading");
        }
        const total = Math.max(1, Math.min(20, Number(rowCount) || 1));
        for (let i = 0; i < total; i += 1) {
          const tr = document.createElement("tr");
          tr.className = "shopping-skeleton-row";

          for (let j = 0; j < 9; j += 1) {
            const td = document.createElement("td");
            const line = document.createElement("div");
            line.className = "ui-skeleton-line skeleton-cell";
            if (j === 1 || j === 8) {
              line.classList.add("long");
            } else if (j === 0 || j === 6 || j === 7) {
              line.classList.add("short");
            } else {
              line.classList.add("medium");
            }
            td.appendChild(line);
            tr.appendChild(td);
          }
          shoppingBody.appendChild(tr);
        }
      }

      async function parseApiError(response) {
        const raw = await response.text();
        if (!raw) return `HTTP ${response.status}`;
        try {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object" && typeof parsed.detail === "string") {
            return parsed.detail;
          }
        } catch (_err) {}
        return raw;
      }

      function formatQty(qty, unit) {
        if (qty == null || !unit) return "—";
        const numeric = Number(qty);
        if (!Number.isFinite(numeric)) return "—";
        const normalizedUnit = normalizeUnit(unit);
        const displayUnit = normalizedUnit === "l" ? "L" : normalizedUnit;
        if (normalizedUnit === "tsp" || normalizedUnit === "tbsp" || normalizedUnit === "cup") {
          return `${numeric.toFixed(1)} ${displayUnit}`;
        }
        if (normalizedUnit === "kg" || normalizedUnit === "l") {
          return `${numeric.toFixed(2).replace(/\.00$/, "")} ${displayUnit}`;
        }
        if (Math.abs(numeric - Math.round(numeric)) < 1e-9) {
          return `${Math.round(numeric)} ${displayUnit}`;
        }
        return `${numeric.toFixed(1).replace(/\.0$/, "")} ${displayUnit}`;
      }

      function formatNeededQty(qty, unit) {
        if (qty == null || !unit) return "—";
        const numeric = Number(qty);
        if (!Number.isFinite(numeric)) return "—";
        const normalizedUnit = normalizeUnit(unit);
        const displayUnit = normalizedUnit === "l" ? "L" : normalizedUnit;
        if (normalizedUnit === "tsp" || normalizedUnit === "tbsp" || normalizedUnit === "cup") {
          return `${numeric.toFixed(1)} ${displayUnit}`;
        }
        return `${Math.round(numeric)} ${displayUnit}`;
      }

      function toLbs(qty, unit) {
        const numeric = Number(qty);
        if (!Number.isFinite(numeric)) {
          return null;
        }
        const normalizedUnit = normalizeUnit(unit);
        const gPerUnit = MASS_UNITS_TO_G[normalizedUnit];
        if (!gPerUnit) {
          return null;
        }
        return (numeric * gPerUnit) / MASS_UNITS_TO_G.lb;
      }

      function formatLbsQty(qty, unit) {
        const pounds = toLbs(qty, unit);
        if (pounds == null) {
          return "—";
        }
        return `${Math.round(pounds)} lbs`;
      }

      async function loadRetreatPlans() {
        retreatPlanSelect.innerHTML = "";

        const allOption = document.createElement("option");
        allOption.value = ALL_RETREATS_VALUE;
        allOption.textContent = "All Retreats (Combined)";
        allOption.selected = true;
        retreatPlanSelect.appendChild(allOption);

        const response = await fetch(apiUrl("/api/retreat-plans"), { credentials: "include" });
        if (!response.ok) {
          throw new Error(await parseApiError(response));
        }
        const rawPlans = await response.json();
        const plans = Array.isArray(rawPlans) ? rawPlans : [];

        if (!plans.length) {
          const emptyOption = document.createElement("option");
          emptyOption.value = "";
          emptyOption.textContent = "No retreat plans found";
          emptyOption.disabled = true;
          retreatPlanSelect.appendChild(emptyOption);
          return 0;
        }
        const sorted = [...plans].sort((a, b) => {
          const da = a.start_date || "";
          const db = b.start_date || "";
          if (da !== db) return da.localeCompare(db);
          return (a.name || "").localeCompare(b.name || "");
        });
        sorted.forEach((plan) => {
          const option = document.createElement("option");
          option.value = String(plan.id);
          option.textContent = plan.name;
          retreatPlanSelect.appendChild(option);
        });
        return sorted.length;
      }

      function renderRetreatPlanLoadError(message) {
        retreatPlanSelect.innerHTML = "";
        const option = document.createElement("option");
        option.value = "";
        option.textContent = `Could not load retreat plans: ${message}`;
        option.disabled = true;
        retreatPlanSelect.appendChild(option);
      }

      function selectedRetreatPlanValues() {
        return Array.from(retreatPlanSelect.selectedOptions)
          .map((opt) => String(opt.value || "").trim())
          .filter(Boolean);
      }

      async function loadVendors() {
        const response = await fetch(apiUrl("/api/vendors"), { credentials: "include" });
        if (!response.ok) {
          throw new Error(await parseApiError(response));
        }
        vendors = await response.json();
        renderPickupVendorOptions();
      }

      function renderPickupVendorOptions() {
        if (!(pickupListVendorSelect instanceof HTMLSelectElement)) {
          return;
        }
        const previousValue = String(pickupListVendorSelect.value || "").trim();
        pickupListVendorSelect.innerHTML = "";
        const anyOption = document.createElement("option");
        anyOption.value = "";
        anyOption.textContent = "Any source";
        pickupListVendorSelect.appendChild(anyOption);
        vendors.forEach((vendor) => {
          const option = document.createElement("option");
          option.value = String(vendor.id);
          option.textContent = vendor.name;
          pickupListVendorSelect.appendChild(option);
        });
        pickupListVendorSelect.value = previousValue;
        if (pickupListVendorSelect.value !== previousValue) {
          pickupListVendorSelect.value = "";
        }
      }

      function resetPickupListForm() {
        if (pickupListNameInput) pickupListNameInput.value = "";
        if (pickupListVendorSelect) pickupListVendorSelect.value = "";
        if (pickupListAssigneeInput) pickupListAssigneeInput.value = "";
        if (pickupListDateInput) pickupListDateInput.value = "";
        if (pickupListNotesInput) pickupListNotesInput.value = "";
      }

      function activePickupItemIdSet() {
        return new Set(
          Array.isArray(activePickupListDetail?.item_ids)
            ? activePickupListDetail.item_ids
                .map((itemId) => Number(itemId))
                .filter((itemId) => Number.isFinite(itemId) && itemId > 0)
            : []
        );
      }

      function pickupScopedItems(items) {
        const rows = Array.isArray(items) ? items : [];
        if (!activePickupListDetail) {
          return rows;
        }
        const allowedIds = activePickupItemIdSet();
        return rows.filter((item) => allowedIds.has(Number(item?.id)));
      }

      function pruneSelectedPickupItems(items) {
        const validIds = new Set(
          (Array.isArray(items) ? items : [])
            .map((item) => Number(item?.id))
            .filter((itemId) => Number.isFinite(itemId) && itemId > 0)
        );
        Array.from(selectedPickupItemIds).forEach((itemId) => {
          if (!validIds.has(Number(itemId))) {
            selectedPickupItemIds.delete(Number(itemId));
          }
        });
      }

      function itemMatchesVendor(item, vendorId) {
        const targetVendorId = Number(vendorId || 0);
        if (!Number.isFinite(targetVendorId) || targetVendorId <= 0) {
          return false;
        }
        const allocations = vendorAllocationsForItem(item);
        return allocations.some((entry) => Number(entry?.vendor_id || 0) === targetVendorId);
      }

      function visibleShoppingItems(detail = activeShoppingDetail) {
        const allItems = pickupScopedItems(Array.isArray(detail?.items) ? detail.items : []);
        return categoryFilteredItems(allItems);
      }

      function updatePickupSelectionSummary() {
        if (pickupSelectionSummary) {
          const count = selectedPickupItemIds.size;
          pickupSelectionSummary.textContent = `${count} item${count === 1 ? "" : "s"} selected`;
        }
        if (!(pickupSelectVisibleCheck instanceof HTMLInputElement)) {
          return;
        }
        const visibleIds = visibleShoppingItems(activeShoppingDetail)
          .map((item) => Number(item?.id))
          .filter((itemId) => Number.isFinite(itemId) && itemId > 0);
        const selectedVisibleCount = visibleIds.filter((itemId) => selectedPickupItemIds.has(itemId)).length;
        pickupSelectVisibleCheck.disabled = !visibleIds.length || Boolean(activePickupListDetail) || !activeListId;
        pickupSelectVisibleCheck.indeterminate = selectedVisibleCount > 0 && selectedVisibleCount < visibleIds.length;
        pickupSelectVisibleCheck.checked = visibleIds.length > 0 && selectedVisibleCount === visibleIds.length;
      }

      function renderActivePickupBanner() {
        if (!activePickupBanner || !activePickupTitle || !activePickupMeta || !activePickupMissing) {
          return;
        }
        if (!activePickupListDetail) {
          activePickupBanner.classList.add("d-none");
          activePickupTitle.textContent = "Pickup list";
          activePickupMeta.textContent = "";
          activePickupMissing.textContent = "";
          activePickupMissing.classList.add("d-none");
          return;
        }
        activePickupBanner.classList.remove("d-none");
        activePickupTitle.textContent = activePickupListDetail.name || "Pickup list";
        const metaParts = [];
        if (activePickupListDetail.vendor_name) {
          metaParts.push(activePickupListDetail.vendor_name);
        }
        if (activePickupListDetail.assignee) {
          metaParts.push(`Assigned to ${activePickupListDetail.assignee}`);
        }
        if (activePickupListDetail.pickup_date) {
          metaParts.push(`Pickup ${activePickupListDetail.pickup_date}`);
        }
        metaParts.push(`${Number(activePickupListDetail.item_count || 0)} items`);
        activePickupMeta.textContent = metaParts.join(" • ");
        const missingCount = Number(activePickupListDetail.missing_item_count || 0);
        if (missingCount > 0) {
          activePickupMissing.classList.remove("d-none");
          activePickupMissing.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i><span>${missingCount} saved item${missingCount === 1 ? "" : "s"} no longer match the master list after refresh.</span>`;
        } else {
          activePickupMissing.textContent = "";
          activePickupMissing.classList.add("d-none");
        }
      }

      function renderPickupListCards() {
        if (!pickupListCards) {
          return;
        }
        pickupListCards.innerHTML = "";
        if (!activeListId) {
          pickupListCards.innerHTML = '<div class="pickup-empty-state">Load a shopping list to manage saved pickup subsets.</div>';
          return;
        }
        if (!pickupLists.length) {
          pickupListCards.innerHTML = '<div class="pickup-empty-state">No saved pickup lists for this shopping list yet.</div>';
          return;
        }
        pickupLists.forEach((pickupList) => {
          const card = document.createElement("div");
          const isActive = Number(activePickupListDetail?.id || 0) === Number(pickupList.id);
          card.className = `pickup-card${isActive ? " is-active" : ""}`;

          const header = document.createElement("div");
          header.className = "pickup-card-header";
          const titleWrap = document.createElement("div");
          const title = document.createElement("div");
          title.className = "pickup-card-title";
          title.textContent = pickupList.name || "Pickup list";
          titleWrap.appendChild(title);

          const meta = document.createElement("div");
          meta.className = "pickup-card-meta mt-2";
          const statusChip = document.createElement("span");
          statusChip.className = "pickup-chip text-capitalize";
          statusChip.textContent = String(pickupList.status || "draft").replace(/_/g, " ");
          meta.appendChild(statusChip);
          if (pickupList.vendor_name) {
            const vendorChip = document.createElement("span");
            vendorChip.className = "pickup-chip";
            vendorChip.innerHTML = `<i class="fa-solid fa-store"></i><span>${pickupList.vendor_name}</span>`;
            meta.appendChild(vendorChip);
          }
          if (pickupList.assignee) {
            const assigneeChip = document.createElement("span");
            assigneeChip.className = "pickup-chip";
            assigneeChip.innerHTML = `<i class="fa-solid fa-user"></i><span>${pickupList.assignee}</span>`;
            meta.appendChild(assigneeChip);
          }
          if (pickupList.pickup_date) {
            const dateChip = document.createElement("span");
            dateChip.className = "pickup-chip";
            dateChip.innerHTML = `<i class="fa-solid fa-calendar-day"></i><span>${pickupList.pickup_date}</span>`;
            meta.appendChild(dateChip);
          }
          titleWrap.appendChild(meta);
          header.appendChild(titleWrap);

          const stats = document.createElement("div");
          stats.className = "pickup-card-stats";
          stats.textContent = `${Number(pickupList.item_count || 0)} items • ${Number(pickupList.ordered_count || 0)} ordered • ${Number(pickupList.received_count || 0)} received`;
          header.appendChild(stats);
          card.appendChild(header);

          if (pickupList.notes) {
            const notes = document.createElement("div");
            notes.className = "muted-note";
            notes.textContent = pickupList.notes;
            card.appendChild(notes);
          }

          if (Number(pickupList.missing_item_count || 0) > 0) {
            const warning = document.createElement("div");
            warning.className = "pickup-banner-warning";
            warning.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i><span>${pickupList.missing_item_count} missing from current master list</span>`;
            card.appendChild(warning);
          }

          const actions = document.createElement("div");
          actions.className = "pickup-card-actions";

          const openBtn = document.createElement("button");
          openBtn.type = "button";
          openBtn.className = `btn btn-sm ${isActive ? "btn-success" : "btn-outline-primary"}`;
          openBtn.innerHTML = isActive
            ? '<i class="fa-solid fa-eye me-2"></i>Viewing'
            : '<i class="fa-solid fa-eye me-2"></i>Open';
          openBtn.disabled = isActive;
          openBtn.addEventListener("click", () => {
            void openPickupList(pickupList.id);
          });
          actions.appendChild(openBtn);

          const pdfBtn = document.createElement("button");
          pdfBtn.type = "button";
          pdfBtn.className = "btn btn-outline-secondary btn-sm";
          pdfBtn.innerHTML = '<i class="fa-solid fa-file-pdf me-2"></i>PDF';
          pdfBtn.addEventListener("click", () => {
            downloadPickupListPdf(pickupList);
          });
          actions.appendChild(pdfBtn);

          const deleteBtn = document.createElement("button");
          deleteBtn.type = "button";
          deleteBtn.className = "btn btn-outline-danger btn-sm";
          deleteBtn.innerHTML = '<i class="fa-solid fa-trash me-2"></i>Delete';
          deleteBtn.addEventListener("click", () => {
            void deletePickupList(pickupList.id);
          });
          actions.appendChild(deleteBtn);

          card.appendChild(actions);
          pickupListCards.appendChild(card);
        });
      }

      function refreshWorkspaceChrome() {
        renderActivePickupBanner();
        renderPickupListCards();
        updatePickupSelectionSummary();
        const pickupViewActive = Boolean(activePickupListDetail);
        if (pickupListNameInput) pickupListNameInput.disabled = pickupViewActive || !activeListId;
        if (pickupListVendorSelect) pickupListVendorSelect.disabled = pickupViewActive || !activeListId;
        if (pickupListAssigneeInput) pickupListAssigneeInput.disabled = pickupViewActive || !activeListId;
        if (pickupListDateInput) pickupListDateInput.disabled = pickupViewActive || !activeListId;
        if (pickupListNotesInput) pickupListNotesInput.disabled = pickupViewActive || !activeListId;
        if (selectVendorPickupItemsBtn) {
          selectVendorPickupItemsBtn.disabled = (
            pickupViewActive
            || !activeListId
            || !vendors.length
            || !(pickupListVendorSelect && String(pickupListVendorSelect.value || "").trim())
          );
        }
        if (clearPickupSelectionBtn) {
          clearPickupSelectionBtn.disabled = pickupViewActive || selectedPickupItemIds.size === 0;
        }
        if (createPickupListBtn) {
          createPickupListBtn.disabled = pickupViewActive || !activeListId || selectedPickupItemIds.size === 0;
        }
        if (closePickupViewBtn) {
          closePickupViewBtn.disabled = !pickupViewActive;
        }
        if (downloadPickupPdfBtn) {
          downloadPickupPdfBtn.disabled = !pickupViewActive;
        }
        if (deletePickupListBtn) {
          deletePickupListBtn.disabled = !pickupViewActive;
        }
      }

      function vendorNameForExport(vendorId, fallbackName = "") {
        const fallback = String(fallbackName || "").trim();
        if (fallback) {
          return fallback;
        }
        const targetId = Number(vendorId || 0);
        if (!Number.isFinite(targetId) || targetId <= 0) {
          return "";
        }
        const vendor = vendors.find((entry) => Number(entry?.id) === targetId);
        return String(vendor?.name || "").trim();
      }

      function pickupItemsForExport(pickupListDetail, detail = activeShoppingDetail) {
        if (!pickupListDetail || !detail) {
          return [];
        }
        if (Number(pickupListDetail.shopping_list_id || 0) !== Number(detail.id || 0)) {
          return [];
        }
        const allowedIds = new Set(
          (Array.isArray(pickupListDetail.item_ids) ? pickupListDetail.item_ids : [])
            .map((itemId) => Number(itemId))
            .filter((itemId) => Number.isFinite(itemId) && itemId > 0)
        );
        return (Array.isArray(detail.items) ? detail.items : []).filter((item) => {
          const itemId = Number(item?.id);
          return Number.isFinite(itemId) && allowedIds.has(itemId);
        });
      }

      function pickupAllocationsForExport(item, pickupListDetail) {
        const allocations = vendorAllocationsForItem(item).filter((entry) => {
          const qty = Number(entry?.allocated_qty);
          const vendorId = Number(entry?.vendor_id || 0);
          const vendorName = String(entry?.vendor_name || "").trim();
          return (Number.isFinite(qty) && qty > 0) || vendorId > 0 || Boolean(vendorName);
        });
        if (!allocations.length) {
          return [];
        }
        const targetVendorId = Number(pickupListDetail?.vendor_id || 0);
        if (Number.isFinite(targetVendorId) && targetVendorId > 0) {
          const matching = allocations.filter((entry) => Number(entry?.vendor_id || 0) === targetVendorId);
          if (matching.length) {
            return matching;
          }
        }
        return allocations;
      }

      function pickupQuantityTextForExport(item, pickupListDetail) {
        const allocations = pickupAllocationsForExport(item, pickupListDetail);
        if (!allocations.length) {
          return formatQty(
            item?.to_buy_qty != null ? item.to_buy_qty : item?.required_qty,
            item?.to_buy_unit || item?.required_unit
          );
        }
        if (allocations.length === 1) {
          const entry = allocations[0];
          return formatQty(entry?.allocated_qty, entry?.allocated_unit);
        }
        return allocations
          .map((entry) => formatQty(entry?.allocated_qty, entry?.allocated_unit))
          .join(" + ");
      }

      function pickupSourceTextForExport(item, pickupListDetail) {
        const assignedSource = vendorNameForExport(pickupListDetail?.vendor_id, pickupListDetail?.vendor_name);
        if (assignedSource) {
          return assignedSource;
        }
        const allocations = pickupAllocationsForExport(item, pickupListDetail);
        if (!allocations.length) {
          return sourceLabel(item);
        }
        const uniqueNames = Array.from(new Set(
          allocations
            .map((entry) => vendorNameForExport(entry?.vendor_id, entry?.vendor_name) || "Unassigned Source")
            .filter(Boolean)
        ));
        return uniqueNames.join(", ");
      }

      function pdfFileSafePart(value, fallback) {
        const normalized = String(value || "")
          .trim()
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-+|-+$/g, "");
        return normalized || fallback;
      }

      function downloadPickupListPdf(pickupListDetail = activePickupListDetail) {
        if (!pickupListDetail) {
          setStatus("Open a pickup list first.", "err");
          return;
        }
        if (!activeShoppingDetail || Number(activeShoppingDetail.id || 0) !== Number(pickupListDetail.shopping_list_id || 0)) {
          setStatus("Load the parent shopping list before downloading this pickup PDF.", "err");
          return;
        }

        const jsPdfCtor = window.jspdf?.jsPDF;
        if (typeof jsPdfCtor !== "function") {
          setStatus("PDF download is unavailable right now. Reload the page and try again.", "err");
          return;
        }

        const matchedItems = pickupItemsForExport(pickupListDetail, activeShoppingDetail);
        const groupedItems = sortedCategoryEntries(matchedItems);
        const missingItems = Array.isArray(pickupListDetail.missing_items) ? pickupListDetail.missing_items : [];
        if (!groupedItems.length && !missingItems.length) {
          setStatus("This pickup list does not currently have any printable items.", "err");
          return;
        }

        try {
          setStatus("Preparing pickup PDF...", "info", { busy: true });

          const doc = new jsPdfCtor({
            orientation: "portrait",
            unit: "pt",
            format: "letter",
          });
          const pageWidth = doc.internal.pageSize.getWidth();
          const pageHeight = doc.internal.pageSize.getHeight();
          const margin = 40;
          const contentWidth = pageWidth - (margin * 2);
          const ingredientWidth = 250;
          const qtyWidth = 90;
          const gapWidth = 18;
          const sourceWidth = contentWidth - ingredientWidth - qtyWidth - gapWidth;
          const ingredientX = margin;
          const qtyRightX = margin + ingredientWidth + qtyWidth;
          const sourceX = margin + ingredientWidth + qtyWidth + gapWidth;
          const title = String(pickupListDetail.name || "Pickup List").trim() || "Pickup List";
          const orderName = String(activeShoppingDetail?.name || "Shopping List").trim() || "Shopping List";
          const sourceName = vendorNameForExport(pickupListDetail?.vendor_id, pickupListDetail?.vendor_name) || "Mixed / not specified";
          const volunteerName = String(pickupListDetail?.assignee || "").trim() || "Unassigned";
          const pickupDate = String(pickupListDetail?.pickup_date || "").trim() || "Not scheduled";
          const generatedAt = new Date().toLocaleString();
          let y = margin;

          function ensureSpace(requiredHeight, drawContinuationHeader = true) {
            if ((y + requiredHeight) <= (pageHeight - margin)) {
              return;
            }
            doc.addPage();
            y = margin;
            if (drawContinuationHeader) {
              drawHeader(false);
              drawTableHeader();
            }
          }

          function drawHeader(isFirstPage) {
            doc.setTextColor(31, 41, 55);
            doc.setFont("helvetica", "bold");
            doc.setFontSize(isFirstPage ? 18 : 14);
            doc.text(title, margin, y);
            y += isFirstPage ? 22 : 18;

            doc.setFont("helvetica", "normal");
            doc.setFontSize(10);
            doc.setTextColor(71, 85, 105);

            if (isFirstPage) {
              const metaLines = [
                `Order: ${orderName}`,
                `Source: ${sourceName}`,
                `Volunteer: ${volunteerName}`,
                `Pickup Date: ${pickupDate}`,
                `Generated: ${generatedAt}`,
              ];
              metaLines.forEach((line) => {
                doc.text(line, margin, y);
                y += 14;
              });

              if (pickupListDetail.notes) {
                const noteLines = doc.splitTextToSize(`Notes: ${pickupListDetail.notes}`, contentWidth);
                doc.text(noteLines, margin, y);
                y += (noteLines.length * 12) + 4;
              }

              if (missingItems.length) {
                const warningLines = doc.splitTextToSize(
                  `${missingItems.length} saved item${missingItems.length === 1 ? "" : "s"} no longer match the current master shopping list. They are listed at the end of this PDF.`,
                  contentWidth
                );
                doc.setTextColor(154, 52, 18);
                doc.text(warningLines, margin, y);
                y += (warningLines.length * 12) + 4;
                doc.setTextColor(71, 85, 105);
              }
            } else {
              doc.text(`Order: ${orderName}`, margin, y);
              y += 12;
              doc.text(`Source: ${sourceName} • Volunteer: ${volunteerName} • Pickup: ${pickupDate}`, margin, y);
              y += 14;
            }

            doc.setDrawColor(226, 232, 240);
            doc.line(margin, y, pageWidth - margin, y);
            y += 14;
          }

          function drawTableHeader() {
            doc.setFont("helvetica", "bold");
            doc.setFontSize(9);
            doc.setTextColor(71, 85, 105);
            doc.text("Ingredient", ingredientX, y);
            doc.text("Qty", qtyRightX, y, { align: "right" });
            doc.text("Source", sourceX, y);
            y += 10;
            doc.setDrawColor(226, 232, 240);
            doc.line(margin, y, pageWidth - margin, y);
            y += 8;
          }

          function drawCategoryHeader(category) {
            ensureSpace(24);
            doc.setFillColor(248, 250, 252);
            doc.roundedRect(margin, y, contentWidth, 18, 4, 4, "F");
            doc.setFont("helvetica", "bold");
            doc.setFontSize(10);
            doc.setTextColor(31, 41, 55);
            doc.text(String(category || "Uncategorized"), margin + 8, y + 12);
            y += 24;
          }

          function drawItemRow(item, pickupList) {
            const ingredientName = String(item?.ingredient_name || "").trim() || "Unknown ingredient";
            const qtyText = pickupQuantityTextForExport(item, pickupList) || "—";
            const sourceText = pickupSourceTextForExport(item, pickupList) || "—";
            const ingredientLines = doc.splitTextToSize(ingredientName, ingredientWidth);
            const qtyLines = doc.splitTextToSize(qtyText, qtyWidth);
            const sourceLines = doc.splitTextToSize(sourceText, sourceWidth);
            const lineCount = Math.max(ingredientLines.length, qtyLines.length, sourceLines.length, 1);
            const rowHeight = (lineCount * 12) + 10;
            ensureSpace(rowHeight);

            doc.setFont("helvetica", "normal");
            doc.setFontSize(10);
            doc.setTextColor(31, 41, 55);
            doc.text(ingredientLines, ingredientX, y + 10);
            doc.text(qtyLines, qtyRightX, y + 10, { align: "right" });
            doc.setTextColor(71, 85, 105);
            doc.text(sourceLines, sourceX, y + 10);

            y += rowHeight - 2;
            doc.setDrawColor(241, 245, 249);
            doc.line(margin, y, pageWidth - margin, y);
            y += 8;
          }

          function drawMissingItemsSection() {
            if (!missingItems.length) {
              return;
            }
            ensureSpace(40, false);
            doc.setFont("helvetica", "bold");
            doc.setFontSize(12);
            doc.setTextColor(154, 52, 18);
            doc.text("Saved Items Missing From Current Master List", margin, y);
            y += 18;

            doc.setFont("helvetica", "normal");
            doc.setFontSize(10);
            doc.setTextColor(71, 85, 105);

            missingItems.forEach((item) => {
              const unitText = String(item?.canonical_unit || "").trim();
              const line = `• ${String(item?.ingredient_name || "Unknown ingredient").trim()}${unitText ? ` (${unitText})` : ""}`;
              const wrapped = doc.splitTextToSize(line, contentWidth);
              ensureSpace((wrapped.length * 12) + 4, false);
              doc.text(wrapped, margin, y);
              y += (wrapped.length * 12) + 4;
            });
          }

          drawHeader(true);
          if (groupedItems.length) {
            drawTableHeader();

            groupedItems.forEach(([category, items]) => {
              drawCategoryHeader(category);
              items.forEach((item) => {
                drawItemRow(item, pickupListDetail);
              });
            });
          }

          drawMissingItemsSection();

          const fileName = `${pdfFileSafePart(orderName, "shopping-list")}--${pdfFileSafePart(title, "pickup-list")}.pdf`;
          doc.save(fileName);
          setStatus(`Downloaded PDF for "${title}".`, "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        }
      }

      function renderShoppingListOptions() {
        shoppingListSelect.innerHTML = "";
        if (!shoppingLists.length) {
          dropdownSelectedListId = null;
          closeInlineRenameEditor();
          const option = document.createElement("option");
          option.value = "";
          option.textContent = "No shopping lists yet";
          shoppingListSelect.appendChild(option);
          return;
        }

        const preferredSelectedId = Number(dropdownSelectedListId || activeListId || 0);
        let selectedIdInOptions = null;
        shoppingLists.forEach((list) => {
          const option = document.createElement("option");
          option.value = String(list.id);
          const label = `${list.name} • ${list.item_count} items • ${list.status}`;
          option.textContent = label;
          if (preferredSelectedId && Number(preferredSelectedId) === Number(list.id)) {
            option.selected = true;
            selectedIdInOptions = Number(list.id);
          }
          shoppingListSelect.appendChild(option);
        });

        if (!selectedIdInOptions && shoppingLists.length) {
          selectedIdInOptions = Number(shoppingLists[0].id);
          shoppingListSelect.value = String(selectedIdInOptions);
        }
        dropdownSelectedListId = selectedIdInOptions;

        const renameOption = document.createElement("option");
        renameOption.value = RENAME_SELECTED_LIST_VALUE;
        renameOption.textContent = "Rename selected list";
        shoppingListSelect.appendChild(renameOption);
      }

      function selectedListIdForActions() {
        const raw = String(shoppingListSelect.value || "").trim();
        const selected = Number(raw);
        if (Number.isFinite(selected) && selected > 0) {
          return selected;
        }
        const remembered = Number(dropdownSelectedListId || 0);
        if (Number.isFinite(remembered) && remembered > 0) {
          return remembered;
        }
        const active = Number(activeListId || 0);
        if (Number.isFinite(active) && active > 0) {
          return active;
        }
        return null;
      }

      async function loadShoppingLists(options = {}) {
        const { showBusy = false } = options;
        if (showBusy) {
          setButtonBusy(refreshListsBtn, true, "Refreshing");
        }
        try {
          const response = await fetch(apiUrl("/api/shopping-lists"), { credentials: "include" });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const payload = await response.json();
          shoppingLists = Array.isArray(payload) ? payload : [];
          if (
            activeListId &&
            !shoppingLists.some((list) => Number(list.id) === Number(activeListId))
          ) {
            activeShoppingDetail = null;
            activeListId = null;
            activeListPhase = null;
            activePickupListDetail = null;
            pickupLists = [];
            selectedPickupItemIds.clear();
            setSummary(null);
            renderShoppingRows({ items: [] });
          }
          renderShoppingListOptions();
          updateListActionStates();
          return shoppingLists.length;
        } finally {
          if (showBusy) {
            setButtonBusy(refreshListsBtn, false, "Refreshing");
          }
        }
      }

      function isInventoryEditablePhase(phase) {
        const normalized = String(phase || "").trim().toLowerCase();
        return normalized === "fresh" || normalized === "daily";
      }

      function updateApplyInventoryHint() {
        if (!applyInventoryBox || !applyInventoryHint) return;
        const items = Array.isArray(activeShoppingDetail?.items) ? activeShoppingDetail.items : [];
        const hasList = Boolean(activeListId);
        const hasStock = items.some((item) => Number(item?.in_stock_qty) > 0);
        applyInventoryBox.classList.toggle("needs-apply", hasList && items.length > 0 && !hasStock);
        if (!hasList) {
          applyInventoryHint.innerHTML =
            'Load a shopping list, then fill its on-hand stock from a dated count (managed on the <a href="kitchen-inventory.html">Inventory - Food</a> page).';
        } else if (!items.length) {
          applyInventoryHint.innerHTML = "This list has no items yet.";
        } else if (!hasStock) {
          applyInventoryHint.innerHTML =
            '<strong>No inventory applied to this list yet.</strong> Pick a dated count and click Apply so "To Buy" reflects what is already on hand.';
        } else {
          applyInventoryHint.innerHTML =
            "On-hand stock is filled. Re-apply a count anytime to overwrite it, or edit Stock values inline.";
        }
      }

      function updateListActionStates() {
        const hasList = Boolean(activeListId);
        deleteListBtn.disabled = !hasList;
        applyInventoryBtn.disabled = !(hasList && isInventoryEditablePhase(activeListPhase));
        if (applyInventoryCountBtn) {
          const hasCountSelection = Boolean(inventoryCountSelect && inventoryCountSelect.value);
          applyInventoryCountBtn.disabled = !(hasList && hasCountSelection);
        }
        [addItemNameInput, addItemQtyInput, addItemUnitSelect, addItemBtn].forEach((element) => {
          if (element) {
            element.disabled = !hasList;
          }
        });
        updateApplyInventoryHint();
      }

      function listNameById(listId) {
        const targetId = Number(listId || 0);
        if (activeShoppingDetail?.name && Number(activeShoppingDetail?.id) === targetId) {
          return String(activeShoppingDetail.name).trim();
        }
        const target = shoppingLists.find((list) => Number(list.id) === targetId);
        return target ? String(target.name || "").trim() : "";
      }

      function closeInlineRenameEditor() {
        renameEditingListId = null;
        if (inlineRenameInput) {
          inlineRenameInput.value = "";
          inlineRenameInput.disabled = false;
        }
        if (inlineRenameSaveBtn) {
          inlineRenameSaveBtn.disabled = false;
        }
        if (inlineRenameCancelBtn) {
          inlineRenameCancelBtn.disabled = false;
        }
        if (inlineRenameWrap) {
          inlineRenameWrap.classList.add("d-none");
        }
      }

      function openInlineRenameEditor(listId) {
        const targetListId = Number(listId || selectedListIdForActions() || 0);
        if (!Number.isFinite(targetListId) || targetListId <= 0) {
          setStatus("Select a shopping list first.", "err");
          return;
        }
        const currentName = listNameById(targetListId) || `Shopping List #${targetListId}`;
        renameEditingListId = targetListId;
        dropdownSelectedListId = targetListId;
        shoppingListSelect.value = String(targetListId);
        if (!inlineRenameWrap || !inlineRenameInput) {
          return;
        }
        inlineRenameInput.value = currentName;
        inlineRenameWrap.classList.remove("d-none");
        inlineRenameInput.focus();
        inlineRenameInput.select();
      }

      function setSummary(detail) {
        const summary = activePickupListDetail && Number(activePickupListDetail.shopping_list_id || 0) === Number(activeListId || 0)
          ? activePickupListDetail
          : detail;
        setMetricValue(metricItems, summary?.item_count || 0);
        setMetricValue(metricOrdered, summary?.ordered_count || 0);
        setMetricValue(metricReceived, summary?.received_count || 0);
        setMetricValue(metricStatus, String(summary?.status || "draft").replace(/_/g, " "));
        refreshWorkspaceChrome();
      }

      function setActiveShoppingDetail(detail, options = {}) {
        const { preservePickupView = false } = options;
        activeShoppingDetail = detail || null;
        activeListId = detail?.id || null;
        dropdownSelectedListId = detail?.id ? Number(detail.id) : dropdownSelectedListId;
        activeListPhase = detail?.phase ? String(detail.phase).trim().toLowerCase() : null;
        if (
          !preservePickupView
          || !activePickupListDetail
          || Number(activePickupListDetail.shopping_list_id || 0) !== Number(activeListId || 0)
        ) {
          activePickupListDetail = null;
        }
        pruneSelectedPickupItems(detail?.items || []);
        updateListActionStates();
      }

      async function loadPickupListsForActiveList(options = {}) {
        const { preserveActivePickup = false } = options;
        if (!activeListId) {
          pickupLists = [];
          activePickupListDetail = null;
          setSummary(activeShoppingDetail);
          return;
        }
        const response = await fetch(apiUrl(`/api/shopping-lists/${activeListId}/pickup-lists`), {
          credentials: "include",
        });
        if (!response.ok) {
          throw new Error(await parseApiError(response));
        }
        const payload = await response.json();
        pickupLists = Array.isArray(payload) ? payload : [];
        if (preserveActivePickup && activePickupListDetail) {
          const activePickupId = Number(activePickupListDetail.id || 0);
          const stillExists = pickupLists.some((entry) => Number(entry.id) === activePickupId);
          if (stillExists) {
            const detailResponse = await fetch(apiUrl(`/api/shopping-pickup-lists/${activePickupId}`), {
              credentials: "include",
            });
            if (!detailResponse.ok) {
              throw new Error(await parseApiError(detailResponse));
            }
            activePickupListDetail = await detailResponse.json();
          } else {
            activePickupListDetail = null;
          }
        } else {
          activePickupListDetail = null;
        }
        setSummary(activeShoppingDetail);
      }

      async function openPickupList(pickupListId) {
        if (!activeListId) {
          setStatus("Load a shopping list first.", "err");
          return;
        }
        try {
          setStatus("Opening pickup list...", "info", { busy: true });
          const response = await fetch(apiUrl(`/api/shopping-pickup-lists/${pickupListId}`), {
            credentials: "include",
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          activePickupListDetail = await response.json();
          selectedPickupItemIds.clear();
          setSummary(activeShoppingDetail);
          renderShoppingRows(activeShoppingDetail || { items: [] });
          setStatus("Pickup list loaded.", "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        }
      }

      function closePickupListView() {
        activePickupListDetail = null;
        setSummary(activeShoppingDetail);
        renderShoppingRows(activeShoppingDetail || { items: [] });
      }

      async function deletePickupList(pickupListId) {
        const target = pickupLists.find((entry) => Number(entry.id) === Number(pickupListId));
        const label = target?.name || activePickupListDetail?.name || `Pickup List #${pickupListId}`;
        const confirmed = window.confirm(`Delete "${label}"? This saved subset will be removed.`);
        if (!confirmed) {
          return;
        }
        try {
          setStatus("Deleting pickup list...", "info", { busy: true });
          const response = await fetch(apiUrl(`/api/shopping-pickup-lists/${pickupListId}`), {
            method: "DELETE",
            credentials: "include",
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          if (Number(activePickupListDetail?.id || 0) === Number(pickupListId)) {
            activePickupListDetail = null;
          }
          await loadPickupListsForActiveList();
          renderShoppingRows(activeShoppingDetail || { items: [] });
          setStatus(`Deleted "${label}".`, "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        }
      }

      async function createPickupListFromSelection() {
        if (!activeListId) {
          setStatus("Load a shopping list first.", "err");
          return;
        }
        const itemIds = Array.from(selectedPickupItemIds.values()).sort((a, b) => a - b);
        if (!itemIds.length) {
          setStatus("Select at least one shopping row first.", "err");
          return;
        }
        const payload = {
          itemIds,
          name: pickupListNameInput?.value.trim() || null,
          vendorId: pickupListVendorSelect?.value ? Number(pickupListVendorSelect.value) : null,
          assignee: pickupListAssigneeInput?.value.trim() || null,
          pickupDate: pickupListDateInput?.value || null,
          notes: pickupListNotesInput?.value.trim() || null,
        };
        try {
          setButtonBusy(createPickupListBtn, true, "Saving");
          setStatus("Saving pickup list...", "info", { busy: true });
          const response = await fetch(apiUrl(`/api/shopping-lists/${activeListId}/pickup-lists`), {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const detail = await response.json();
          selectedPickupItemIds.clear();
          resetPickupListForm();
          await loadPickupListsForActiveList();
          activePickupListDetail = detail;
          setSummary(activeShoppingDetail);
          renderShoppingRows(activeShoppingDetail || { items: [] });
          setStatus(`Saved "${detail.name}".`, "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        } finally {
          setButtonBusy(createPickupListBtn, false, "Saving");
        }
      }

      function clearPickupSelection() {
        selectedPickupItemIds.clear();
        refreshWorkspaceChrome();
        renderShoppingRows(activeShoppingDetail || { items: [] });
      }

      function selectVisibleItemsForVendor() {
        if (!activeListId) {
          setStatus("Load a shopping list first.", "err");
          return;
        }
        const vendorId = pickupListVendorSelect?.value ? Number(pickupListVendorSelect.value) : null;
        if (!vendorId) {
          setStatus("Choose a source first.", "err");
          return;
        }
        const visibleItems = visibleShoppingItems(activeShoppingDetail);
        const matching = visibleItems.filter((item) => itemMatchesVendor(item, vendorId));
        if (!matching.length) {
          setStatus("No visible items match that source.", "err");
          return;
        }
        matching.forEach((item) => {
          selectedPickupItemIds.add(Number(item.id));
        });
        refreshWorkspaceChrome();
        renderShoppingRows(activeShoppingDetail || { items: [] });
        setStatus(`${matching.length} items selected for this source.`, "ok");
      }

      function ingredientCategoryName(item) {
        return String(item?.ingredient_category || "").trim() || "Uncategorized";
      }

      function categoryFilteredItems(items) {
        let filtered = [...items];
        if (selectedIngredientCategory) {
          filtered = filtered.filter((item) => ingredientCategoryName(item) === selectedIngredientCategory);
        }
        if (hideZeroToBuyCheck && hideZeroToBuyCheck.checked) {
          filtered = filtered.filter((item) => Number(item?.to_buy_qty) > 0);
        }
        return filtered;
      }

      function renderShoppingCategoryFilter(items) {
        if (!shoppingCategoryFilter) {
          return;
        }
        const rows = Array.isArray(items) ? items : [];
        shoppingCategoryFilter.innerHTML = "";
        if (!rows.length) {
          selectedIngredientCategory = null;
          return;
        }

        const counts = new Map();
        rows.forEach((item) => {
          const category = ingredientCategoryName(item);
          counts.set(category, (counts.get(category) || 0) + 1);
        });

        if (selectedIngredientCategory !== null && !counts.has(selectedIngredientCategory)) {
          selectedIngredientCategory = null;
        }

        const allBtn = document.createElement("button");
        allBtn.type = "button";
        allBtn.className = `cat-pill${selectedIngredientCategory === null ? " active" : ""}`;
        allBtn.textContent = `All (${rows.length})`;
        allBtn.addEventListener("click", () => {
          selectedIngredientCategory = null;
          renderShoppingRows(activeShoppingDetail || { items: [] });
        });
        shoppingCategoryFilter.appendChild(allBtn);

        const sortedCategories = Array.from(counts.entries()).sort((a, b) => {
          const aName = a[0];
          const bName = b[0];
          if (aName === "Uncategorized") return 1;
          if (bName === "Uncategorized") return -1;
          return aName.localeCompare(bName);
        });

        sortedCategories.forEach(([category, count]) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = `cat-pill${selectedIngredientCategory === category ? " active" : ""}`;
          button.textContent = `${category} (${count})`;
          button.addEventListener("click", () => {
            selectedIngredientCategory = category;
            renderShoppingRows(activeShoppingDetail || { items: [] });
          });
          shoppingCategoryFilter.appendChild(button);
        });
      }

      function setGroupMode(mode) {
        currentGroupMode = mode === "source" ? "source" : "category";
        if (groupModeSelect) {
          groupModeSelect.value = currentGroupMode;
        }
      }

      function createVendorSelect(item) {
        const select = document.createElement("select");
        select.className = "form-select form-select-sm";

        const none = document.createElement("option");
        none.value = "";
        none.textContent = "Select source";
        select.appendChild(none);

        vendors.forEach((vendor) => {
          const option = document.createElement("option");
          option.value = String(vendor.id);
          option.textContent = vendor.name;
          if (item.vendor_id && Number(item.vendor_id) === Number(vendor.id)) {
            option.selected = true;
          }
          select.appendChild(option);
        });

        select.addEventListener("change", () => {
          const raw = String(select.value || "").trim();
          const vendorId = raw ? Number(raw) : null;
          void updateShoppingItem(item.id, { vendorId });
        });
        return select;
      }

      function createToggle(checked, onChange) {
        const input = document.createElement("input");
        input.type = "checkbox";
        input.className = "form-check-input";
        input.checked = Boolean(checked);
        input.addEventListener("change", () => onChange(Boolean(input.checked)));
        return input;
      }

      function inventoryInputStep(unit) {
        const normalized = normalizeUnit(unit);
        if (normalized === "kg" || normalized === "l" || normalized === "lb" || normalized === "oz" || normalized === "fl oz" || normalized === "qt" || normalized === "gal") {
          return "0.1";
        }
        return "1";
      }

      function orderedInputStep(unit) {
        const normalized = normalizeUnit(unit);
        if (normalized === "kg" || normalized === "l" || normalized === "lb" || normalized === "oz" || normalized === "fl oz" || normalized === "qt" || normalized === "gal") {
          return "0.1";
        }
        return "1";
      }

      function formatEditableQuantityValue(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
          return "";
        }
        const rounded = Math.round(numeric * 10) / 10;
        return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
      }

      function roundEditableQuantity(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
          return null;
        }
        return Math.round(numeric * 10000) / 10000;
      }

      function normalizeCountStylePurchaseUnit(unit) {
        const normalized = normalizeUnit(unit);
        if (!normalized) {
          return "";
        }
        if (normalized === "piece" || normalized === "sprig" || normalized === "leaf" || normalized === "pinch") {
          return "each";
        }
        if (
          normalized === "each"
          || normalized === "bag"
          || normalized === "box"
          || normalized === "case"
          || normalized === "can"
          || normalized === "packet"
          || normalized === "pack"
          || normalized === "bottle"
          || normalized === "jug"
          || normalized === "jar"
          || normalized === "carton"
          || normalized === "tub"
          || normalized === "package"
          || normalized === "bunch"
          || normalized === "loaf"
        ) {
          return normalized;
        }
        return "";
      }

      function convertQuantityBetweenUnits(quantity, fromUnit, toUnit) {
        const numeric = Number(quantity);
        if (!Number.isFinite(numeric)) {
          return null;
        }
        const normalizedFrom = normalizeUnit(fromUnit);
        const normalizedTo = normalizeUnit(toUnit);
        if (!normalizedFrom || !normalizedTo) {
          return null;
        }
        if (normalizedFrom === normalizedTo) {
          return numeric;
        }
        if (
          Object.prototype.hasOwnProperty.call(MASS_UNITS_TO_G, normalizedFrom)
          && Object.prototype.hasOwnProperty.call(MASS_UNITS_TO_G, normalizedTo)
        ) {
          return (numeric * MASS_UNITS_TO_G[normalizedFrom]) / MASS_UNITS_TO_G[normalizedTo];
        }
        if (
          Object.prototype.hasOwnProperty.call(VOLUME_UNITS_TO_ML, normalizedFrom)
          && Object.prototype.hasOwnProperty.call(VOLUME_UNITS_TO_ML, normalizedTo)
        ) {
          return (numeric * VOLUME_UNITS_TO_ML[normalizedFrom]) / VOLUME_UNITS_TO_ML[normalizedTo];
        }
        return null;
      }

      function suggestOrderedPurchaseAmount(quantity, unit, preferredUnit = null) {
        const numeric = Number(quantity);
        const normalizedUnit = normalizeUnit(unit);
        const normalizedPreferredUnit = normalizeUnit(preferredUnit);

        if (normalizedPreferredUnit) {
          if (Number.isFinite(numeric) && numeric > 0) {
            const converted = convertQuantityBetweenUnits(numeric, normalizedUnit, normalizedPreferredUnit);
            if (converted != null) {
              return {
                qty: roundEditableQuantity(converted),
                unit: normalizedPreferredUnit,
              };
            }
            if (normalizeCountStylePurchaseUnit(normalizedPreferredUnit)) {
              const fallbackQty = (
                Object.prototype.hasOwnProperty.call(MASS_UNITS_TO_G, normalizedUnit)
                || Object.prototype.hasOwnProperty.call(VOLUME_UNITS_TO_ML, normalizedUnit)
              )
                ? 1
                : numeric;
              return {
                qty: roundEditableQuantity(fallbackQty),
                unit: normalizedPreferredUnit,
              };
            }
            return {
              qty: roundEditableQuantity(numeric),
              unit: normalizedPreferredUnit,
            };
          }
          return { qty: null, unit: normalizedPreferredUnit };
        }

        if (Number.isFinite(numeric) && numeric > 0 && Object.prototype.hasOwnProperty.call(MASS_UNITS_TO_G, normalizedUnit)) {
          const grams = numeric * MASS_UNITS_TO_G[normalizedUnit];
          const targetUnit = grams >= MASS_UNITS_TO_G.lb ? "lb" : "oz";
          return {
            qty: roundEditableQuantity(grams / MASS_UNITS_TO_G[targetUnit]),
            unit: targetUnit,
          };
        }
        if (Number.isFinite(numeric) && numeric > 0 && Object.prototype.hasOwnProperty.call(VOLUME_UNITS_TO_ML, normalizedUnit)) {
          const ml = numeric * VOLUME_UNITS_TO_ML[normalizedUnit];
          const targetUnit = ml >= VOLUME_UNITS_TO_ML.gal
            ? "gal"
            : (ml >= VOLUME_UNITS_TO_ML.qt ? "qt" : "fl oz");
          return {
            qty: roundEditableQuantity(ml / VOLUME_UNITS_TO_ML[targetUnit]),
            unit: targetUnit,
          };
        }
        return {
          qty: Number.isFinite(numeric) && numeric > 0 ? roundEditableQuantity(numeric) : null,
          unit: normalizeCountStylePurchaseUnit(normalizedUnit) || "each",
        };
      }

      function orderedUnitOptionsForItem(item, selectedUnit) {
        const normalizedSelectedUnit = normalizeUnit(selectedUnit);
        const normalizedBaseUnit = normalizeUnit(item?.to_buy_unit || item?.required_unit || normalizedSelectedUnit);
        let options = COUNT_ORDERED_UNIT_OPTIONS;
        if (Object.prototype.hasOwnProperty.call(MASS_UNITS_TO_G, normalizedBaseUnit)) {
          options = MASS_ORDERED_UNIT_OPTIONS;
        } else if (Object.prototype.hasOwnProperty.call(VOLUME_UNITS_TO_ML, normalizedBaseUnit)) {
          options = VOLUME_ORDERED_UNIT_OPTIONS;
        }
        const merged = [...ALWAYS_AVAILABLE_ORDERED_UNITS, ...options];
        if (normalizedSelectedUnit && !merged.includes(normalizedSelectedUnit)) {
          merged.unshift(normalizedSelectedUnit);
        }
        return Array.from(new Set(merged.filter(Boolean)));
      }

      function resolveOrderedEditorState(item) {
        const hasStoredQty = item?.ordered_qty != null && Number.isFinite(Number(item.ordered_qty));
        const storedUnit = normalizeUnit(item?.ordered_unit || "");
        const planningQty = Number(item?.to_buy_qty ?? item?.required_qty);
        const planningUnit = normalizeUnit(item?.to_buy_unit || item?.required_unit || "");

        let displayUnit = storedUnit;
        if (!hasStoredQty && METRIC_ORDERED_UNITS.has(storedUnit)) {
          displayUnit = "";
        }

        if (hasStoredQty) {
          const preferredStoredUnit = storedUnit && !METRIC_ORDERED_UNITS.has(storedUnit) ? storedUnit : null;
          const storedDisplay = suggestOrderedPurchaseAmount(Number(item.ordered_qty), storedUnit || planningUnit, preferredStoredUnit);
          return {
            qty: storedDisplay.qty,
            unit: storedDisplay.unit || displayUnit || "each",
          };
        }

        if (!displayUnit) {
          const defaultDisplay = suggestOrderedPurchaseAmount(
            Number.isFinite(planningQty) ? planningQty : 0,
            planningUnit,
          );
          displayUnit = defaultDisplay.unit || "each";
        }

        return {
          qty: null,
          unit: displayUnit || "each",
        };
      }

      function formatStockEditorValue(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
          return "0";
        }
        const rounded = Math.round(numeric * 10) / 10;
        return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
      }

      function createInventoryEditor(item) {
        const wrapper = document.createElement("div");
        wrapper.className = "inventory-editor";

        const input = document.createElement("input");
        input.type = "number";
        input.className = "form-control form-control-sm";
        input.min = "0";
        input.step = inventoryInputStep(String(item.in_stock_unit || item.required_unit || "").trim());
        input.value = item.in_stock_qty != null && Number.isFinite(Number(item.in_stock_qty))
          ? formatStockEditorValue(item.in_stock_qty)
          : "0";

        let lastGoodValue = input.value;
        input.addEventListener("change", () => {
          const value = Number(input.value);
          if (!Number.isFinite(value) || value < 0) {
            input.value = lastGoodValue;
            setStatus("Current inventory must be a non-negative number.", "err");
            return;
          }
          const formatted = formatStockEditorValue(value);
          input.value = formatted;
          lastGoodValue = formatted;
          void updateShoppingItem(item.id, { inStockQty: Number(formatted) });
        });

        const unit = document.createElement("span");
        unit.className = "qty-chip";
        const displayUnit = normalizeUnit(String(item.in_stock_unit || item.required_unit || "").trim());
        unit.textContent = displayUnit === "l" ? "L" : (displayUnit || "unit");

        wrapper.appendChild(input);
        wrapper.appendChild(unit);
        return wrapper;
      }

      function createOrderedAmountEditor(item) {
        const wrapper = document.createElement("div");
        wrapper.className = "inventory-editor";

        const editorState = resolveOrderedEditorState(item);
        const input = document.createElement("input");
        input.type = "number";
        input.className = "form-control form-control-sm";
        input.min = "0";
        input.step = orderedInputStep(editorState.unit);
        input.placeholder = "0";
        input.value = formatEditableQuantityValue(editorState.qty);

        let lastGoodValue = input.value;
        const select = document.createElement("select");
        select.className = "form-select form-select-sm";
        const unitOptions = orderedUnitOptionsForItem(item, editorState.unit);
        unitOptions.forEach((unitOption) => {
          const option = document.createElement("option");
          option.value = unitOption;
          option.textContent = unitOption === "l" ? "L" : unitOption;
          if (unitOption === editorState.unit) {
            option.selected = true;
          }
          select.appendChild(option);
        });
        select.dataset.previousUnit = editorState.unit;

        input.addEventListener("change", () => {
          const raw = String(input.value || "").trim();
          const selectedUnit = normalizeUnit(select.value);
          if (!raw) {
            lastGoodValue = "";
            void updateShoppingItem(item.id, { orderedQty: null, orderedUnit: selectedUnit || null });
            return;
          }
          const value = Number(raw);
          if (!Number.isFinite(value) || value < 0) {
            input.value = lastGoodValue;
            setStatus("Amount ordered must be a non-negative number.", "err");
            return;
          }
          const formatted = formatEditableQuantityValue(value);
          const rounded = Number(formatted);
          input.value = formatted;
          lastGoodValue = formatted;
          void updateShoppingItem(item.id, { orderedQty: rounded, orderedUnit: selectedUnit || null });
        });

        select.addEventListener("change", () => {
          const previousUnit = normalizeUnit(select.dataset.previousUnit || "");
          const selectedUnit = normalizeUnit(select.value);
          const raw = String(input.value || "").trim();

          if (raw) {
            const value = Number(raw);
            if (!Number.isFinite(value) || value < 0) {
              input.value = lastGoodValue;
              if (previousUnit) {
                select.value = previousUnit;
              }
              setStatus("Amount ordered must be a non-negative number.", "err");
              return;
            }

            let nextValue = roundEditableQuantity(value);
            const converted = convertQuantityBetweenUnits(value, previousUnit, selectedUnit);
            if (converted != null) {
              nextValue = roundEditableQuantity(converted);
            } else if (normalizeCountStylePurchaseUnit(selectedUnit) && previousUnit !== selectedUnit) {
              nextValue = 1;
            }
            nextValue = Number(formatEditableQuantityValue(nextValue));

            input.value = formatEditableQuantityValue(nextValue);
            lastGoodValue = input.value;
            input.step = orderedInputStep(selectedUnit);
            select.dataset.previousUnit = selectedUnit;
            void updateShoppingItem(item.id, { orderedQty: nextValue, orderedUnit: selectedUnit || null });
            return;
          }

          input.step = orderedInputStep(selectedUnit);
          select.dataset.previousUnit = selectedUnit;
          void updateShoppingItem(item.id, { orderedUnit: selectedUnit || null });
        });

        wrapper.appendChild(input);
        wrapper.appendChild(select);
        return wrapper;
      }

      function targetShoppingQtyForItem(item) {
        const preferred = Number(item?.to_buy_qty);
        if (Number.isFinite(preferred) && preferred > 0) {
          return preferred;
        }
        const fallback = Number(item?.required_qty);
        return Number.isFinite(fallback) && fallback > 0 ? fallback : 0;
      }

      function targetShoppingUnitForItem(item) {
        return normalizeUnit(item?.to_buy_unit || item?.required_unit || "") || "each";
      }

      function vendorAllocationsForItem(item) {
        const rows = Array.isArray(item?.vendor_allocations) ? item.vendor_allocations : [];
        if (!rows.length) {
          const editorState = resolveOrderedEditorState(item);
          return [
            {
              id: null,
              vendor_id: item?.vendor_id != null ? Number(item.vendor_id) : null,
              vendor_name: String(item?.vendor_name || "").trim() || "",
              allocated_qty: editorState.qty,
              allocated_unit: normalizeUnit(editorState.unit || targetShoppingUnitForItem(item)) || "each",
              ordered: Boolean(item?.ordered),
              received: Boolean(item?.received),
            },
          ];
        }
        return rows.map((entry, index) => {
          const editorState = resolveOrderedEditorState(item);
          const numericQty = Number(entry?.allocated_qty);
          return {
            id: Number.isFinite(Number(entry?.id)) ? Number(entry.id) : null,
            vendor_id: entry?.vendor_id != null && Number.isFinite(Number(entry.vendor_id))
              ? Number(entry.vendor_id)
              : null,
            vendor_name: String(entry?.vendor_name || "").trim() || "",
            allocated_qty: Number.isFinite(numericQty) ? numericQty : editorState.qty,
            allocated_unit: normalizeUnit(entry?.allocated_unit || editorState.unit || targetShoppingUnitForItem(item)) || "each",
            ordered: Boolean(entry?.ordered),
            received: Boolean(entry?.received),
            sort_order: Number.isFinite(Number(entry?.sort_order)) ? Number(entry.sort_order) : index,
          };
        });
      }

      function cloneVendorAllocations(allocations) {
        return allocations.map((entry) => ({
          id: entry.id != null ? Number(entry.id) : null,
          vendor_id: entry.vendor_id != null ? Number(entry.vendor_id) : null,
          vendor_name: String(entry.vendor_name || "").trim() || "",
          allocated_qty: entry.allocated_qty == null ? null : Number(entry.allocated_qty),
          allocated_unit: normalizeUnit(entry.allocated_unit || "") || "each",
          ordered: Boolean(entry.ordered),
          received: Boolean(entry.received),
          sort_order: Number.isFinite(Number(entry.sort_order)) ? Number(entry.sort_order) : 0,
        }));
      }

      function buildVendorAllocationsPayload(allocations) {
        return allocations.map((entry, index) => ({
          ...(entry.id ? { id: Number(entry.id) } : {}),
          vendorId: entry.vendor_id != null && Number.isFinite(Number(entry.vendor_id)) ? Number(entry.vendor_id) : null,
          allocatedQty: roundEditableQuantity(entry.allocated_qty) || 0,
          allocatedUnit: normalizeUnit(entry.allocated_unit || "") || "each",
          ordered: Boolean(entry.ordered),
          received: Boolean(entry.received),
          sortOrder: index,
        }));
      }

      function saveVendorAllocations(item, allocations) {
        const normalized = cloneVendorAllocations(allocations).map((entry, index) => ({
          ...entry,
          allocated_unit: normalizeUnit(entry.allocated_unit || "") || targetShoppingUnitForItem(item),
          sort_order: index,
        }));
        return updateShoppingItem(item.id, {
          vendorAllocations: buildVendorAllocationsPayload(normalized),
        });
      }

      function addVendorAllocation(item, allocations) {
        const next = cloneVendorAllocations(allocations);
        const editorState = resolveOrderedEditorState(item);
        next.push({
          id: null,
          vendor_id: null,
          vendor_name: "",
          allocated_qty: null,
          allocated_unit: normalizeUnit(editorState.unit || targetShoppingUnitForItem(item)) || "each",
          ordered: false,
          received: false,
          sort_order: next.length,
        });
        void saveVendorAllocations(item, next);
      }

      function removeVendorAllocation(item, allocations, indexToRemove) {
        const next = cloneVendorAllocations(allocations).filter((_entry, index) => index !== indexToRemove);
        void saveVendorAllocations(item, next);
      }

      function summarizeVendorAllocationCoverage(item, allocations) {
        const targetQty = targetShoppingQtyForItem(item);
        const targetUnit = targetShoppingUnitForItem(item);
        let total = 0;
        let convertible = targetQty > 0 && Boolean(targetUnit);

        allocations.forEach((entry) => {
          const qty = Number(entry?.allocated_qty);
          const unit = normalizeUnit(entry?.allocated_unit || "");
          if (!Number.isFinite(qty) || qty <= 0 || !unit) {
            return;
          }
          const converted = convertQuantityBetweenUnits(qty, unit, targetUnit);
          if (converted == null) {
            convertible = false;
            return;
          }
          total += converted;
        });

        return {
          sourceCount: allocations.length,
          targetQty,
          targetUnit,
          totalQty: roundEditableQuantity(total) || 0,
          convertible,
        };
      }

      function createVendorAllocationSourceEditor(item, allocations) {
        const wrapper = document.createElement("div");
        wrapper.className = "allocation-stack";

        allocations.forEach((entry, index) => {
          const row = document.createElement("div");
          row.className = "allocation-line";

          const select = document.createElement("select");
          select.className = "form-select form-select-sm";

          const none = document.createElement("option");
          none.value = "";
          none.textContent = "Select source";
          select.appendChild(none);

          vendors.forEach((vendor) => {
            const option = document.createElement("option");
            option.value = String(vendor.id);
            option.textContent = vendor.name;
            if (entry.vendor_id != null && Number(entry.vendor_id) === Number(vendor.id)) {
              option.selected = true;
            }
            select.appendChild(option);
          });

          select.addEventListener("change", () => {
            const next = cloneVendorAllocations(allocations);
            const raw = String(select.value || "").trim();
            next[index].vendor_id = raw ? Number(raw) : null;
            void saveVendorAllocations(item, next);
          });
          row.appendChild(select);

          if (index === 0) {
            const addBtn = document.createElement("button");
            addBtn.type = "button";
            addBtn.className = "allocation-icon-btn";
            addBtn.innerHTML = '<i class="fa-solid fa-plus"></i>';
            addBtn.title = "Add source";
            addBtn.setAttribute("aria-label", "Add source");
            addBtn.addEventListener("click", () => {
              addVendorAllocation(item, allocations);
            });
            row.appendChild(addBtn);
          }

          if (allocations.length > 1 && index > 0) {
            const removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "allocation-icon-btn allocation-remove";
            removeBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
            removeBtn.title = "Remove source";
            removeBtn.setAttribute("aria-label", "Remove source");
            removeBtn.addEventListener("click", () => {
              removeVendorAllocation(item, allocations, index);
            });
            row.appendChild(removeBtn);
          }

          wrapper.appendChild(row);
        });
        return wrapper;
      }

      function createVendorAllocationAmountEditor(item, allocations) {
        const wrapper = document.createElement("div");
        wrapper.className = "allocation-stack";

        allocations.forEach((entry, index) => {
          const row = document.createElement("div");
          row.className = "allocation-line";

          const input = document.createElement("input");
          input.type = "number";
          input.className = "form-control form-control-sm";
          input.min = "0";
          input.step = orderedInputStep(entry.allocated_unit);
          input.placeholder = "0";
          input.value = formatEditableQuantityValue(entry.allocated_qty);

          let lastGoodValue = input.value;
          const select = document.createElement("select");
          select.className = "form-select form-select-sm";
          const unitOptions = orderedUnitOptionsForItem(item, entry.allocated_unit);
          unitOptions.forEach((unitOption) => {
            const option = document.createElement("option");
            option.value = unitOption;
            option.textContent = unitOption === "l" ? "L" : unitOption;
            if (unitOption === normalizeUnit(entry.allocated_unit)) {
              option.selected = true;
            }
            select.appendChild(option);
          });
          select.dataset.previousUnit = normalizeUnit(entry.allocated_unit);

          input.addEventListener("change", () => {
            const raw = String(input.value || "").trim();
            const next = cloneVendorAllocations(allocations);
            if (!raw) {
              next[index].allocated_qty = 0;
              void saveVendorAllocations(item, next);
              return;
            }
            const value = Number(raw);
            if (!Number.isFinite(value) || value < 0) {
              input.value = lastGoodValue;
              setStatus("Source amount must be a non-negative number.", "err");
              return;
            }
            const rounded = roundEditableQuantity(value);
            input.value = formatEditableQuantityValue(rounded);
            lastGoodValue = input.value;
            next[index].allocated_qty = rounded;
            next[index].allocated_unit = normalizeUnit(select.value) || targetShoppingUnitForItem(item);
            void saveVendorAllocations(item, next);
          });

          select.addEventListener("change", () => {
            const previousUnit = normalizeUnit(select.dataset.previousUnit || "");
            const selectedUnit = normalizeUnit(select.value) || targetShoppingUnitForItem(item);
            const next = cloneVendorAllocations(allocations);
            const raw = String(input.value || "").trim();

            if (raw) {
              const value = Number(raw);
              if (!Number.isFinite(value) || value < 0) {
                input.value = lastGoodValue;
                select.value = previousUnit || selectedUnit;
                setStatus("Source amount must be a non-negative number.", "err");
                return;
              }
              let nextValue = roundEditableQuantity(value);
              const converted = convertQuantityBetweenUnits(value, previousUnit, selectedUnit);
              if (converted != null) {
                nextValue = roundEditableQuantity(converted);
              } else if (normalizeCountStylePurchaseUnit(selectedUnit) && previousUnit !== selectedUnit) {
                nextValue = 1;
              }
              input.value = formatEditableQuantityValue(nextValue);
              lastGoodValue = input.value;
              next[index].allocated_qty = nextValue;
            }

            input.step = orderedInputStep(selectedUnit);
            select.dataset.previousUnit = selectedUnit;
            next[index].allocated_unit = selectedUnit;
            void saveVendorAllocations(item, next);
          });

          row.appendChild(input);
          row.appendChild(select);
          wrapper.appendChild(row);
        });

        return wrapper;
      }

      function createVendorAllocationToggleEditor(item, allocations, fieldName) {
        const wrapper = document.createElement("div");
        wrapper.className = "allocation-stack allocation-toggle-stack";

        allocations.forEach((entry, index) => {
          const row = document.createElement("div");
          row.className = "allocation-line allocation-line-center";

          const input = document.createElement("input");
          input.type = "checkbox";
          input.className = "form-check-input";
          input.checked = Boolean(entry[fieldName]);
          input.addEventListener("change", () => {
            const next = cloneVendorAllocations(allocations);
            const checked = Boolean(input.checked);
            next[index][fieldName] = checked;
            if (fieldName === "ordered" && !checked) {
              next[index].received = false;
            }
            if (fieldName === "received" && checked) {
              next[index].ordered = true;
            }
            void saveVendorAllocations(item, next);
          });

          row.appendChild(input);
          wrapper.appendChild(row);
        });

        return wrapper;
      }

      function sortItemsByIngredientNameAsc(items) {
        return [...items].sort((a, b) => {
          const aName = String(a.ingredient_name || "").trim();
          const bName = String(b.ingredient_name || "").trim();
          const byName = aName.localeCompare(bName, undefined, {
            sensitivity: "base",
            numeric: true,
          });
          if (byName !== 0) {
            return byName;
          }
          return Number(a.id || 0) - Number(b.id || 0);
        });
      }

      function meetsContributionThreshold(qty, unit) {
        const numericQty = Number(qty);
        if (!Number.isFinite(numericQty) || numericQty <= 0) {
          return false;
        }
        const normalizedUnit = normalizeUnit(unit);
        if (Object.prototype.hasOwnProperty.call(MASS_UNITS_TO_G, normalizedUnit)) {
          return (numericQty * MASS_UNITS_TO_G[normalizedUnit]) >= 2000;
        }
        if (Object.prototype.hasOwnProperty.call(VOLUME_UNITS_TO_ML, normalizedUnit)) {
          return (numericQty * VOLUME_UNITS_TO_ML[normalizedUnit]) >= 2000;
        }
        return false;
      }

      function sortedCategoryEntries(items) {
        const grouped = new Map();
        items.forEach((item) => {
          const category = ingredientCategoryName(item);
          const bucket = grouped.get(category) || [];
          bucket.push(item);
          grouped.set(category, bucket);
        });

        const categories = Array.from(grouped.entries());
        categories.sort((a, b) => {
          const aName = a[0];
          const bName = b[0];
          if (aName === "Uncategorized") return 1;
          if (bName === "Uncategorized") return -1;
          return aName.localeCompare(bName);
        });

        return categories.map(([category, rows]) => [category, sortItemsByIngredientNameAsc(rows)]);
      }

      function sourceLabel(item) {
        const allocations = vendorAllocationsForItem(item);
        if (allocations.length > 1) {
          return "Multiple Sources";
        }
        const first = allocations[0] || null;
        if (first && first.vendor_name) {
          return String(first.vendor_name).trim();
        }
        if (first && first.vendor_id != null) {
          const vendor = vendors.find((entry) => Number(entry.id) === Number(first.vendor_id));
          if (vendor && vendor.name) {
            return vendor.name;
          }
        }
        return "Unassigned Source";
      }

      function sortedSourceEntries(items) {
        const grouped = new Map();
        items.forEach((item) => {
          const source = sourceLabel(item);
          const bucket = grouped.get(source) || [];
          bucket.push(item);
          grouped.set(source, bucket);
        });

        const sources = Array.from(grouped.entries());
        sources.sort((a, b) => {
          const aName = a[0];
          const bName = b[0];
          if (aName === "Unassigned Source") return 1;
          if (bName === "Unassigned Source") return -1;
          return aName.localeCompare(bName);
        });

        return sources.map(([source, rows]) => ({
          source,
          totalItems: rows.length,
          categories: sortedCategoryEntries(rows),
        }));
      }

      function renderShoppingItemRow(item, inventoryEditable) {
        const tr = document.createElement("tr");
        tr.className = "item-row";
        const vendorAllocations = vendorAllocationsForItem(item);
        const allocationCoverage = summarizeVendorAllocationCoverage(item, vendorAllocations);

        const selectionTd = document.createElement("td");
        selectionTd.className = "selection-cell";
        const pickInput = document.createElement("input");
        pickInput.type = "checkbox";
        pickInput.className = "form-check-input pick-input";
        pickInput.checked = activePickupListDetail ? true : selectedPickupItemIds.has(Number(item.id));
        pickInput.disabled = Boolean(activePickupListDetail);
        pickInput.addEventListener("change", () => {
          const itemId = Number(item.id);
          if (pickInput.checked) {
            selectedPickupItemIds.add(itemId);
          } else {
            selectedPickupItemIds.delete(itemId);
          }
          refreshWorkspaceChrome();
        });
        selectionTd.appendChild(pickInput);
        tr.appendChild(selectionTd);

        const ingredientTd = document.createElement("td");
        ingredientTd.className = "shopping-need-cell ingredient-cell";
        const ingredientName = String(item?.ingredient_name || "").trim() || "Unknown ingredient";
        const sourceBreakdown = Array.isArray(item?.source_breakdown)
          ? item.source_breakdown
              .map((entry) => ({
                retreatPlanId: Number.isFinite(Number(entry?.retreat_plan_id)) ? Number(entry.retreat_plan_id) : null,
                retreatPlanName: String(entry?.retreat_plan_name || "").trim() || "Unknown retreat",
                requiredQty: Number(entry?.required_qty),
                requiredUnit: String(entry?.required_unit || "").trim(),
              }))
              .filter((entry) => Number.isFinite(entry.requiredQty) && entry.requiredQty > 0 && entry.requiredUnit)
          : [];

        const topSource = item?.top_source && typeof item.top_source === "object"
          ? {
              retreatPlanName: String(item.top_source.retreat_plan_name || "").trim(),
              dishName: String(item.top_source.dish_name || "").trim(),
              requiredQty: Number(item.top_source.required_qty),
              requiredUnit: String(item.top_source.required_unit || "").trim(),
            }
          : null;
        const showSourceInsights = sourceBreakdown.length > 0
          && meetsContributionThreshold(item?.required_qty, item?.required_unit);

        const topLabelParts = [];
        if (topSource?.retreatPlanName) {
          topLabelParts.push(topSource.retreatPlanName);
        }
        if (topSource?.dishName) {
          topLabelParts.push(topSource.dishName);
        }

        if (!showSourceInsights) {
          const nameDiv = document.createElement("div");
          nameDiv.className = "ingredient-name";
          nameDiv.textContent = ingredientName;
          ingredientTd.appendChild(nameDiv);
        } else {
          const details = document.createElement("details");
          details.className = "ingredient-breakdown";

          const summary = document.createElement("summary");
          summary.className = "ingredient-breakdown-summary";
          const nameSpan = document.createElement("span");
          nameSpan.className = "ingredient-name";
          nameSpan.textContent = ingredientName;
          summary.appendChild(nameSpan);

          const hoverLines = sourceBreakdown.map(
            (entry) => `${entry.retreatPlanName}: ${formatNeededQty(entry.requiredQty, entry.requiredUnit)}`
          );
          if (topLabelParts.length) {
            hoverLines.unshift(`Top contributor: ${topLabelParts.join(" / ")}`);
          }
          summary.title = hoverLines.join("\n");
          details.appendChild(summary);

          const breakdownList = document.createElement("div");
          breakdownList.className = "ingredient-breakdown-list";
          if (topLabelParts.length) {
            const topBreakdownLine = document.createElement("div");
            topBreakdownLine.className = "ingredient-breakdown-top";
            const topQtyText = Number.isFinite(topSource?.requiredQty) && topSource?.requiredUnit
              ? ` (${formatNeededQty(topSource.requiredQty, topSource.requiredUnit)})`
              : "";
            topBreakdownLine.textContent = `Top dish: ${topLabelParts.join(" / ")}${topQtyText}`;
            breakdownList.appendChild(topBreakdownLine);
          }
          sourceBreakdown.forEach((entry) => {
            const line = document.createElement("div");
            line.className = "ingredient-breakdown-entry";
            line.textContent = `${entry.retreatPlanName}: ${formatNeededQty(entry.requiredQty, entry.requiredUnit)}`;
            breakdownList.appendChild(line);
          });
          details.appendChild(breakdownList);
          ingredientTd.appendChild(details);
        }
        const ingredientMetrics = document.createElement("div");
        ingredientMetrics.className = "ingredient-metrics";

        if (vendorAllocations.length > 1) {
          const splitBadge = document.createElement("span");
          const coverageMatches = allocationCoverage.convertible
            && allocationCoverage.targetQty > 0
            && Math.abs(Number(allocationCoverage.totalQty || 0) - Number(allocationCoverage.targetQty || 0)) < 0.01;
          splitBadge.className = `badge partial-buy-badge ${coverageMatches ? "now" : "later"}`;
          if (allocationCoverage.convertible && allocationCoverage.targetQty > 0) {
            splitBadge.textContent = `${vendorAllocations.length} sources • ${formatEditableQuantityValue(allocationCoverage.totalQty)} / ${formatEditableQuantityValue(allocationCoverage.targetQty)} ${allocationCoverage.targetUnit}`;
          } else {
            splitBadge.textContent = `${vendorAllocations.length} sources`;
          }
          ingredientMetrics.appendChild(splitBadge);
        }

        const needMetric = document.createElement("div");
        needMetric.className = "ingredient-metric";
        const needLabel = document.createElement("span");
        needLabel.className = "ingredient-metric-label";
        needLabel.textContent = "Need";
        const needChip = document.createElement("span");
        needChip.className = "qty-chip";
        needChip.textContent = formatNeededQty(item.required_qty, item.required_unit);
        needMetric.appendChild(needLabel);
        needMetric.appendChild(needChip);
        ingredientMetrics.appendChild(needMetric);

        const stockMetric = document.createElement("div");
        stockMetric.className = "ingredient-metric";
        const stockLabel = document.createElement("span");
        stockLabel.className = "ingredient-metric-label";
        stockLabel.textContent = "Stock";
        stockMetric.appendChild(stockLabel);
        if (inventoryEditable) {
          stockMetric.appendChild(createInventoryEditor(item));
        } else {
          const stockChip = document.createElement("span");
          stockChip.className = "qty-chip";
          stockChip.textContent = formatNeededQty(item.in_stock_qty, item.in_stock_unit);
          stockMetric.appendChild(stockChip);
        }
        ingredientMetrics.appendChild(stockMetric);
        ingredientTd.appendChild(ingredientMetrics);
        tr.appendChild(ingredientTd);

        const buyMetricTd = document.createElement("td");
        buyMetricTd.className = "shopping-need-cell";
        buyMetricTd.innerHTML = `<span class="qty-chip buy">${formatNeededQty(item.to_buy_qty, item.to_buy_unit)}</span>`;
        tr.appendChild(buyMetricTd);

        const buyUsTd = document.createElement("td");
        buyUsTd.className = "shopping-need-cell shopping-need-end";
        buyUsTd.innerHTML = `<span class="qty-chip buy">${formatLbsQty(item.to_buy_qty, item.to_buy_unit)}</span>`;
        tr.appendChild(buyUsTd);

        const sourceTd = document.createElement("td");
        sourceTd.className = "shopping-action-cell shopping-action-start";
        sourceTd.appendChild(createVendorAllocationSourceEditor(item, vendorAllocations));
        tr.appendChild(sourceTd);

        const orderedAmountTd = document.createElement("td");
        orderedAmountTd.className = "shopping-action-cell";
        orderedAmountTd.appendChild(createVendorAllocationAmountEditor(item, vendorAllocations));
        tr.appendChild(orderedAmountTd);

        const orderedTd = document.createElement("td");
        orderedTd.className = "shopping-action-cell text-center";
        orderedTd.appendChild(createVendorAllocationToggleEditor(item, vendorAllocations, "ordered"));
        tr.appendChild(orderedTd);

        const receivedTd = document.createElement("td");
        receivedTd.className = "shopping-action-cell text-center";
        receivedTd.appendChild(createVendorAllocationToggleEditor(item, vendorAllocations, "received"));
        tr.appendChild(receivedTd);

        const notesTd = document.createElement("td");
        notesTd.className = "shopping-action-cell";
        const notesInput = document.createElement("textarea");
        notesInput.rows = 1;
        notesInput.className = "form-control form-control-sm item-note-input";
        notesInput.placeholder = "Add a note...";
        notesInput.value = item.notes || "";
        const autosizeNotes = () => {
          notesInput.style.height = "auto";
          notesInput.style.height = `${notesInput.scrollHeight}px`;
        };
        notesInput.addEventListener("input", autosizeNotes);
        notesInput.addEventListener("change", () => {
          void updateShoppingItem(item.id, { notes: notesInput.value.trim() || null });
        });
        requestAnimationFrame(autosizeNotes);
        const notesWrap = document.createElement("div");
        notesWrap.className = "d-flex align-items-start gap-1";
        notesWrap.appendChild(notesInput);
        const removeItemBtn = document.createElement("button");
        removeItemBtn.type = "button";
        removeItemBtn.className = "icon-btn is-cancel flex-shrink-0";
        removeItemBtn.title = "Remove item from list";
        removeItemBtn.setAttribute("aria-label", "Remove item from list");
        removeItemBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
        removeItemBtn.addEventListener("click", () => {
          void deleteShoppingListItemRow(item);
        });
        notesWrap.appendChild(removeItemBtn);
        notesTd.appendChild(notesWrap);
        tr.appendChild(notesTd);

        return tr;
      }

      function renderCategoryHeaderRow(category, itemCount) {
        const headerTr = document.createElement("tr");
        headerTr.className = "category-row";
        const headerTd = document.createElement("td");
        headerTd.colSpan = 9;

        const heading = document.createElement("div");
        heading.className = "category-heading";
        const name = document.createElement("span");
        name.textContent = String(category);
        const count = document.createElement("span");
        count.className = "category-count";
        count.textContent = `${Number(itemCount || 0)} items`;
        heading.appendChild(name);
        heading.appendChild(count);
        headerTd.appendChild(heading);

        headerTr.appendChild(headerTd);
        return headerTr;
      }

      function renderShoppingRows(detail) {
        shoppingBody.innerHTML = "";
        if (shoppingTableWrap) {
          shoppingTableWrap.classList.remove("is-loading");
        }
        const inventoryEditable = true;
        const allItems = Array.isArray(detail?.items) ? detail.items : [];
        pruneSelectedPickupItems(allItems);
        const scopedItems = pickupScopedItems(allItems);
        const rawBreakdownCount = scopedItems.filter(
          (item) => Array.isArray(item?.source_breakdown) && item.source_breakdown.length > 0
        ).length;
        const withBreakdownCount = scopedItems.filter(
          (item) => Array.isArray(item?.source_breakdown)
            && item.source_breakdown.length > 0
            && meetsContributionThreshold(item?.required_qty, item?.required_unit)
        ).length;
        if (sourceBreakdownHint) {
          if (!scopedItems.length) {
            sourceBreakdownHint.classList.add("d-none");
            sourceBreakdownHint.textContent = "";
          } else if (rawBreakdownCount === 0) {
            sourceBreakdownHint.classList.remove("d-none");
            sourceBreakdownHint.textContent = "Retreat contribution details are not available for this list yet.";
          } else if (withBreakdownCount === 0) {
            sourceBreakdownHint.classList.remove("d-none");
            sourceBreakdownHint.textContent = "No ingredients above 2 kg / 2 l threshold for contributor details.";
          } else {
            sourceBreakdownHint.classList.remove("d-none");
            sourceBreakdownHint.textContent = `${withBreakdownCount} ingredients include contributor details (>= 2 kg or >= 2 l).`;
          }
        }
        renderShoppingCategoryFilter(scopedItems);
        const visibleItems = categoryFilteredItems(scopedItems);

        if (!allItems.length) {
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 9;
          td.className = "text-muted small py-3";
          td.textContent = "No items found for this shopping list.";
          tr.appendChild(td);
          shoppingBody.appendChild(tr);
          triggerFadeIn(shoppingBody);
          refreshWorkspaceChrome();
          return;
        }

        if (!scopedItems.length && activePickupListDetail) {
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 9;
          td.className = "text-muted small py-3";
          td.textContent = "This pickup list does not currently match any items in the master list.";
          tr.appendChild(td);
          shoppingBody.appendChild(tr);
          triggerFadeIn(shoppingBody);
          refreshWorkspaceChrome();
          return;
        }

        if (!visibleItems.length) {
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 9;
          td.className = "text-muted small py-3";
          td.textContent = `No items in ${selectedIngredientCategory}.`;
          tr.appendChild(td);
          shoppingBody.appendChild(tr);
          triggerFadeIn(shoppingBody);
          refreshWorkspaceChrome();
          return;
        }

        if (currentGroupMode === "source") {
          sortedSourceEntries(visibleItems).forEach((sourceEntry) => {
            const sourceTr = document.createElement("tr");
            sourceTr.className = "source-row";
            const sourceTd = document.createElement("td");
            sourceTd.colSpan = 9;
            sourceTd.textContent = `Source: ${sourceEntry.source} (${sourceEntry.totalItems} items)`;
            sourceTr.appendChild(sourceTd);
            shoppingBody.appendChild(sourceTr);

            sourceEntry.categories.forEach(([category, items]) => {
              shoppingBody.appendChild(renderCategoryHeaderRow(category, items.length));

              items.forEach((item) => {
                shoppingBody.appendChild(renderShoppingItemRow(item, inventoryEditable));
              });
            });
          });
          triggerFadeIn(shoppingBody);
          refreshWorkspaceChrome();
          return;
        }

        sortedCategoryEntries(visibleItems).forEach(([category, items]) => {
          shoppingBody.appendChild(renderCategoryHeaderRow(category, items.length));

          items.forEach((item) => {
            shoppingBody.appendChild(renderShoppingItemRow(item, inventoryEditable));
          });
        });
        triggerFadeIn(shoppingBody);
        refreshWorkspaceChrome();
      }

      async function loadShoppingListDetail(listId) {
        setStatus("Loading list...", "info", { busy: true });
        renderShoppingSkeletonRows(10);
        try {
          const response = await fetch(apiUrl(`/api/shopping-lists/${listId}`), {
            credentials: "include",
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const detail = await response.json();
          setActiveShoppingDetail(detail, { preservePickupView: true });
          await loadPickupListsForActiveList({ preserveActivePickup: true });
          setSummary(detail);
          renderShoppingRows(detail);
        } catch (error) {
          if (shoppingTableWrap) {
            shoppingTableWrap.classList.remove("is-loading");
          }
          throw error;
        }
      }

      async function refreshSelectedShoppingList() {
        const targetListId = Number(selectedListIdForActions() || 0);
        if (!Number.isFinite(targetListId) || targetListId <= 0) {
          const count = await loadShoppingLists({ showBusy: true });
          setStatus(`Lists refreshed. ${count} available.`, "ok");
          return;
        }

        const targetList = shoppingLists.find((list) => Number(list.id) === targetListId);
        if (targetList && String(targetList.phase || "").toLowerCase() === "custom") {
          try {
            setButtonBusy(refreshListsBtn, true, "Refreshing");
            await loadShoppingListDetail(targetListId);
            await loadShoppingLists();
            setStatus("Manual list reloaded.", "ok");
          } catch (error) {
            setStatus(error instanceof Error ? error.message : String(error), "err");
          } finally {
            setButtonBusy(refreshListsBtn, false, "Refreshing");
          }
          return;
        }

        try {
          setButtonBusy(refreshListsBtn, true, "Refreshing");
          setStatus("Refreshing shopping list from current retreat menu...", "info", { busy: true });
          renderShoppingSkeletonRows(10);
          const response = await fetch(apiUrl(`/api/shopping-lists/${targetListId}/refresh`), {
            method: "POST",
            credentials: "include",
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }

          const detail = await response.json();
          setActiveShoppingDetail(detail, { preservePickupView: true });
          await loadPickupListsForActiveList({ preserveActivePickup: true });
          setSummary(detail);
          renderShoppingRows(detail);
          await loadShoppingLists();

          const missing = Array.isArray(detail.missing_recipes) ? detail.missing_recipes : [];
          if (missing.length) {
            setStatus(`Shopping list refreshed with ${missing.length} missing recipes.`, "err");
          } else {
            setStatus(`Shopping list refreshed. ${Number(detail.item_count || 0)} items.`, "ok");
          }
        } catch (error) {
          if (shoppingTableWrap) {
            shoppingTableWrap.classList.remove("is-loading");
          }
          setStatus(error instanceof Error ? error.message : String(error), "err");
        } finally {
          setButtonBusy(refreshListsBtn, false, "Refreshing");
        }
      }

      async function updateShoppingItem(itemId, payload) {
        if (!activeListId) return;
        try {
          setStatus("Saving item...", "info", { busy: true });
          const response = await fetch(apiUrl(`/api/shopping-lists/${activeListId}/items/${itemId}`), {
            method: "PATCH",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const detail = await response.json();
          setActiveShoppingDetail(detail, { preservePickupView: true });
          await loadPickupListsForActiveList({ preserveActivePickup: true });
          setSummary(detail);
          renderShoppingRows(detail);
          await loadShoppingLists();
          setStatus("Saved.", "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        }
      }

      async function generateShoppingList() {
        const selectedValues = selectedRetreatPlanValues();
        const allRetreats = selectedValues.includes(ALL_RETREATS_VALUE);
        const retreatPlanIds = allRetreats
          ? []
          : selectedValues
              .map((value) => Number(value))
              .filter((value) => Number.isFinite(value) && value > 0);
        if (!allRetreats && retreatPlanIds.length === 0) {
          setStatus("Select at least one retreat plan first.", "err");
          return;
        }

        const payload = {
          retreatPlanId: retreatPlanIds.length === 1 ? retreatPlanIds[0] : null,
          retreatPlanIds,
          allRetreats,
          phase: phaseSelect.value,
          subtractInventory: false,
          includeZeroToBuy: true,
        };

        try {
          setButtonBusy(generateBtn, true, "Generating");
          setStatus("Generating shopping list...", "info", { busy: true });
          renderShoppingSkeletonRows(11);
          const response = await fetch(apiUrl("/api/shopping-lists/generate"), {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const detail = await response.json();
          setActiveShoppingDetail(detail);
          await loadPickupListsForActiveList();
          setSummary(detail);
          renderShoppingRows(detail);
          await loadShoppingLists();

          const missing = Array.isArray(detail.missing_recipes) ? detail.missing_recipes : [];
          if (missing.length) {
            setStatus(`Generated with ${missing.length} missing recipes.`, "err");
          } else {
            setStatus("Shopping list generated. Now apply an inventory count to fill on-hand stock.", "ok");
          }
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
          if (shoppingTableWrap) {
            shoppingTableWrap.classList.remove("is-loading");
          }
        } finally {
          setButtonBusy(generateBtn, false, "Generating");
        }
      }

      async function renameShoppingListById(listId, nextNameRaw) {
        const targetListId = Number(listId || 0);
        if (!Number.isFinite(targetListId) || targetListId <= 0) {
          setStatus("Load a shopping list first.", "err");
          return;
        }

        const nextName = String(nextNameRaw || "").trim();
        if (!nextName) {
          setStatus("Shopping list name cannot be blank.", "err");
          if (inlineRenameInput) {
            inlineRenameInput.focus();
            inlineRenameInput.select();
          }
          return;
        }

        try {
          shoppingListSelect.disabled = true;
          if (inlineRenameInput) inlineRenameInput.disabled = true;
          if (inlineRenameSaveBtn) inlineRenameSaveBtn.disabled = true;
          if (inlineRenameCancelBtn) inlineRenameCancelBtn.disabled = true;
          setStatus("Renaming shopping list...", "info", { busy: true });
          const response = await fetch(apiUrl(`/api/shopping-lists/${targetListId}`), {
            method: "PATCH",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: nextName }),
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const detail = await response.json();
          if (Number(activeListId) === Number(targetListId)) {
            setActiveShoppingDetail(detail, { preservePickupView: true });
            await loadPickupListsForActiveList({ preserveActivePickup: true });
            setSummary(detail);
            renderShoppingRows(detail);
          }
          await loadShoppingLists();
          dropdownSelectedListId = Number(detail.id);
          shoppingListSelect.value = String(detail.id);
          closeInlineRenameEditor();
          setStatus(`Renamed to "${detail.name}".`, "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        } finally {
          shoppingListSelect.disabled = false;
          if (inlineRenameInput) inlineRenameInput.disabled = false;
          if (inlineRenameSaveBtn) inlineRenameSaveBtn.disabled = false;
          if (inlineRenameCancelBtn) inlineRenameCancelBtn.disabled = false;
        }
      }

      async function submitInlineRename() {
        const targetListId = Number(renameEditingListId || selectedListIdForActions() || 0);
        if (!Number.isFinite(targetListId) || targetListId <= 0) {
          setStatus("Select a shopping list first.", "err");
          return;
        }
        const proposedName = inlineRenameInput ? inlineRenameInput.value : "";
        await renameShoppingListById(targetListId, proposedName);
      }

      async function deleteActiveShoppingList() {
        if (!activeListId) {
          setStatus("Load a shopping list first.", "err");
          return;
        }

        const listName = listNameById(activeListId) || `Shopping List #${activeListId}`;
        const confirmed = window.confirm(`Delete "${listName}"? This cannot be undone.`);
        if (!confirmed) {
          return;
        }

        try {
          setButtonBusy(deleteListBtn, true, "Deleting");
          setStatus("Deleting shopping list...", "info", { busy: true });
          const response = await fetch(apiUrl(`/api/shopping-lists/${activeListId}`), {
            method: "DELETE",
            credentials: "include",
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const deleted = await response.json();

          activeShoppingDetail = null;
          activeListId = null;
          activeListPhase = null;
          activePickupListDetail = null;
          pickupLists = [];
          selectedPickupItemIds.clear();
          closeInlineRenameEditor();
          updateListActionStates();
          setSummary(null);
          renderShoppingRows({ items: [] });

          await loadShoppingLists();
          if (shoppingLists.length) {
            const nextId = Number(shoppingLists[0].id);
            if (nextId) {
              await loadShoppingListDetail(nextId);
            }
          }
          setStatus(`Deleted "${deleted?.name || listName}".`, "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        } finally {
          setButtonBusy(deleteListBtn, false, "Deleting");
        }
      }

      async function applyInventoryFromList() {
        if (!activeListId) {
          setStatus("Load a shopping list first.", "err");
          return;
        }
        if (!isInventoryEditablePhase(activeListPhase)) {
          setStatus("Apply inventory is available only for fresh and daily lists.", "err");
          return;
        }

        try {
          setButtonBusy(applyInventoryBtn, true, "Applying");
          setStatus("Applying current inventory...", "info", { busy: true });
          renderShoppingSkeletonRows(8);
          const response = await fetch(apiUrl(`/api/shopping-lists/${activeListId}/apply-inventory`), {
            method: "POST",
            credentials: "include",
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const result = await response.json();
          await loadShoppingListDetail(activeListId);
          const applied = Number(result.applied_count || 0);
          setStatus(`Applied inventory for ${applied} items.`, "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
          if (shoppingTableWrap) {
            shoppingTableWrap.classList.remove("is-loading");
          }
        } finally {
          setButtonBusy(applyInventoryBtn, false, "Applying");
        }
      }

      async function loadKitchenInventoryCounts() {
        if (!inventoryCountSelect) return;
        const response = await fetch(apiUrl("/api/kitchen-inventory"), { credentials: "include" });
        if (!response.ok) {
          throw new Error(await parseApiError(response));
        }
        kitchenInventoryCounts = await response.json();
        const previous = inventoryCountSelect.value;
        inventoryCountSelect.innerHTML = "";
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = kitchenInventoryCounts.length
          ? "Select a saved inventory count"
          : "No inventory counts uploaded yet";
        inventoryCountSelect.appendChild(placeholder);
        kitchenInventoryCounts.forEach((count) => {
          const option = document.createElement("option");
          option.value = String(count.id);
          option.textContent = `${count.inventory_date} — ${count.name || `Count #${count.id}`}`;
          inventoryCountSelect.appendChild(option);
        });
        if (previous && kitchenInventoryCounts.some((count) => String(count.id) === previous)) {
          inventoryCountSelect.value = previous;
        }
        updateListActionStates();
      }

      async function applyKitchenInventoryCount() {
        if (!activeListId) {
          setStatus("Load a shopping list first.", "err");
          return;
        }
        const countId = Number(inventoryCountSelect ? inventoryCountSelect.value : 0);
        if (!Number.isFinite(countId) || countId <= 0) {
          setStatus("Select a saved inventory count first.", "err");
          return;
        }
        const count = kitchenInventoryCounts.find((entry) => Number(entry.id) === countId);
        const countLabel = count
          ? `${count.inventory_date} — ${count.name || `Count #${count.id}`}`
          : `Count #${countId}`;
        const listName = listNameById(activeListId) || `Shopping List #${activeListId}`;
        const confirmed = window.confirm(
          `Apply inventory count "${countLabel}" to "${listName}"?\n\n` +
            "On-hand stock will be set for every item in the list; ingredients missing from the count are set to 0. " +
            "You can still edit stock values afterwards."
        );
        if (!confirmed) {
          return;
        }

        try {
          setButtonBusy(applyInventoryCountBtn, true, "Applying");
          setStatus("Applying inventory count...", "info", { busy: true });
          renderShoppingSkeletonRows(8);
          const response = await fetch(apiUrl(`/api/shopping-lists/${activeListId}/apply-inventory-list`), {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ inventoryListId: countId }),
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const result = await response.json();
          await loadShoppingListDetail(activeListId);
          setStatus(
            `Applied "${result.inventory_list_name}" (${result.inventory_date}): stock filled for ${result.matched_count} items, ${result.zeroed_count} set to 0.`,
            "ok"
          );
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
          if (shoppingTableWrap) {
            shoppingTableWrap.classList.remove("is-loading");
          }
        } finally {
          setButtonBusy(applyInventoryCountBtn, false, "Applying");
        }
      }

      function initAddItemUnitOptions() {
        if (!addItemUnitSelect || addItemUnitSelect.options.length) return;
        ADD_ITEM_UNITS.forEach((unitOption) => {
          const option = document.createElement("option");
          option.value = unitOption;
          option.textContent = unitOption === "l" ? "L" : unitOption;
          addItemUnitSelect.appendChild(option);
        });
      }

      async function loadIngredientCatalogOptions() {
        if (!addItemIngredientOptions) return;
        const response = await fetch(apiUrl("/api/ingredients"), { credentials: "include" });
        if (!response.ok) {
          throw new Error(await parseApiError(response));
        }
        const rows = await response.json();
        ingredientCatalogNames = rows
          .map((row) => String(row.name || "").trim())
          .filter(Boolean)
          .sort((a, b) => a.localeCompare(b));
        addItemIngredientOptions.innerHTML = "";
        ingredientCatalogNames.forEach((name) => {
          const option = document.createElement("option");
          option.value = name;
          addItemIngredientOptions.appendChild(option);
        });
      }

      async function createManualShoppingList() {
        const today = new Date().toISOString().slice(0, 10);
        const proposed = window.prompt(
          "Name for the new manual shopping list:",
          `Sir's Kitchen - ${today}`,
        );
        if (proposed === null) {
          return;
        }
        try {
          setButtonBusy(newManualListBtn, true, "Creating");
          setStatus("Creating manual shopping list...", "info", { busy: true });
          const response = await fetch(apiUrl("/api/shopping-lists"), {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: proposed.trim(), listDate: today }),
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const detail = await response.json();
          setActiveShoppingDetail(detail);
          await loadPickupListsForActiveList();
          setSummary(detail);
          renderShoppingRows(detail);
          await loadShoppingLists();
          setStatus(`Created "${detail.name}". Add items below.`, "ok");
          if (addItemNameInput) {
            addItemNameInput.focus();
          }
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        } finally {
          setButtonBusy(newManualListBtn, false, "Creating");
        }
      }

      async function addItemToActiveList() {
        if (!activeListId) {
          setStatus("Load a shopping list first.", "err");
          return;
        }
        const name = String(addItemNameInput?.value || "").trim();
        const qty = Number(addItemQtyInput?.value);
        const unit = String(addItemUnitSelect?.value || "");
        if (!name) {
          setStatus("Enter an ingredient name to add.", "err");
          return;
        }
        if (!Number.isFinite(qty) || qty <= 0) {
          setStatus("Enter an amount greater than 0.", "err");
          return;
        }
        try {
          setButtonBusy(addItemBtn, true, "Adding");
          setStatus(`Adding ${name}...`, "info", { busy: true });
          const response = await fetch(apiUrl(`/api/shopping-lists/${activeListId}/items`), {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ingredientName: name, qty, unit }),
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const detail = await response.json();
          setActiveShoppingDetail(detail, { preservePickupView: true });
          setSummary(detail);
          renderShoppingRows(detail);
          await loadShoppingLists();
          if (addItemNameInput) addItemNameInput.value = "";
          if (addItemQtyInput) addItemQtyInput.value = "";
          void loadIngredientCatalogOptions().catch(() => {});
          setStatus(`Added ${name}.`, "ok");
          if (addItemNameInput) addItemNameInput.focus();
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        } finally {
          setButtonBusy(addItemBtn, false, "Adding");
        }
      }

      async function deleteShoppingListItemRow(item) {
        if (!activeListId) return;
        const label = item?.ingredient_name || "this item";
        if (!window.confirm(`Remove "${label}" from the list?`)) {
          return;
        }
        try {
          setStatus(`Removing ${label}...`, "info", { busy: true });
          const response = await fetch(apiUrl(`/api/shopping-lists/${activeListId}/items/${item.id}`), {
            method: "DELETE",
            credentials: "include",
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const detail = await response.json();
          setActiveShoppingDetail(detail, { preservePickupView: true });
          setSummary(detail);
          renderShoppingRows(detail);
          await loadShoppingLists();
          setStatus(`Removed ${label}.`, "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
        }
      }

      async function bootstrap() {
        try {
          setStatus("Loading shopping workspace...", "info", { busy: true });
          renderShoppingSkeletonRows(10);
          setGroupMode("category");
          const loadWorkspaceData = () =>
            Promise.allSettled([
              loadRetreatPlans(),
              loadVendors(),
              loadShoppingLists(),
            ]);
          let [plansResult, vendorsResult, listsResult] = await loadWorkspaceData();
          let fellBackToDefaultApi = false;
          const hadAnyLoadFailure = [plansResult, vendorsResult, listsResult].some((result) => result.status === "rejected");
          if (hadAnyLoadFailure && usingApiOverride()) {
            switchToDefaultApiBase();
            [plansResult, vendorsResult, listsResult] = await loadWorkspaceData();
            fellBackToDefaultApi = true;
          }
          const warnings = [];

          if (plansResult.status === "rejected") {
            const planError = plansResult.reason instanceof Error ? plansResult.reason.message : String(plansResult.reason);
            renderRetreatPlanLoadError(planError);
            warnings.push(`Could not load retreat plans: ${planError}`);
          }

          if (vendorsResult.status === "rejected") {
            vendors = [];
            renderPickupVendorOptions();
            const vendorError = vendorsResult.reason instanceof Error ? vendorsResult.reason.message : String(vendorsResult.reason);
            warnings.push(`Could not load vendors: ${vendorError}`);
          }

          if (listsResult.status === "rejected") {
            throw listsResult.reason;
          }

          if (fellBackToDefaultApi) {
            warnings.unshift(`API override failed. Using ${API_BASE}.`);
          }

          if (shoppingLists.length) {
            const firstId = Number(shoppingLists[0].id);
            if (firstId) {
              try {
                await loadShoppingListDetail(firstId);
              } catch (error) {
                activeShoppingDetail = null;
                activeListId = null;
                activeListPhase = null;
                activePickupListDetail = null;
                pickupLists = [];
                selectedPickupItemIds.clear();
                updateListActionStates();
                setSummary(null);
                renderShoppingRows({ items: [] });
                warnings.push(
                  `Could not load list detail: ${error instanceof Error ? error.message : String(error)}`
                );
              }
            }
          } else {
            activeShoppingDetail = null;
            activeListId = null;
            activeListPhase = null;
            activePickupListDetail = null;
            pickupLists = [];
            selectedPickupItemIds.clear();
            updateListActionStates();
            setSummary(null);
            renderShoppingRows({ items: [] });
          }

          if (warnings.length) {
            setStatus(warnings[0], "err");
          } else {
            const loadedPlanCount = plansResult.status === "fulfilled" ? Number(plansResult.value || 0) : 0;
            const loadedListCount = listsResult.status === "fulfilled" ? Number(listsResult.value || 0) : shoppingLists.length;
            setStatus(`Ready. ${loadedPlanCount} retreat plans, ${loadedListCount} shopping lists loaded.`, "ok");
          }

          void loadKitchenInventoryCounts().catch(() => {
            /* non-fatal: the apply-count control just stays disabled */
          });
          initAddItemUnitOptions();
          void loadIngredientCatalogOptions().catch(() => {
            /* non-fatal: the add-item name field just loses its suggestions */
          });
        } catch (error) {
          if (shoppingTableWrap) {
            shoppingTableWrap.classList.remove("is-loading");
          }
          setStatus(error instanceof Error ? error.message : String(error), "err");
        }
      }

      groupModeSelect.addEventListener("change", () => {
        setGroupMode(groupModeSelect.value);
        renderShoppingRows(activeShoppingDetail || { items: [] });
      });
      if (hideZeroToBuyCheck) {
        hideZeroToBuyCheck.addEventListener("change", () => {
          renderShoppingRows(activeShoppingDetail || { items: [] });
        });
      }
      selectAllRetreatsBtn.addEventListener("click", () => {
        Array.from(retreatPlanSelect.options).forEach((opt) => {
          opt.selected = true;
        });
      });
      clearRetreatsBtn.addEventListener("click", () => {
        Array.from(retreatPlanSelect.options).forEach((opt) => {
          opt.selected = false;
        });
      });
      generateBtn.addEventListener("click", () => {
        void generateShoppingList();
      });

      loadListBtn.addEventListener("click", () => {
        const selected = selectedListIdForActions();
        if (!selected) {
          setStatus("Select a shopping list to load.", "err");
          return;
        }
        dropdownSelectedListId = Number(selected);
        shoppingListSelect.value = String(selected);
        setButtonBusy(loadListBtn, true, "Loading");
        void loadShoppingListDetail(selected)
          .then(() => setStatus("List loaded.", "ok"))
          .catch((error) => setStatus(error instanceof Error ? error.message : String(error), "err"))
          .finally(() => setButtonBusy(loadListBtn, false, "Loading"));
      });

      shoppingListSelect.addEventListener("change", () => {
        const raw = String(shoppingListSelect.value || "").trim();
        if (!raw) {
          return;
        }

        if (raw === RENAME_SELECTED_LIST_VALUE) {
          const selected = selectedListIdForActions();
          if (!selected) {
            setStatus("Select a shopping list first.", "err");
            return;
          }
          shoppingListSelect.value = String(selected);
          openInlineRenameEditor(selected);
          return;
        }

        const selected = Number(raw);
        if (Number.isFinite(selected) && selected > 0) {
          dropdownSelectedListId = selected;
          if (renameEditingListId && Number(renameEditingListId) !== selected) {
            closeInlineRenameEditor();
          }
        }
      });

      if (inlineRenameSaveBtn) {
        inlineRenameSaveBtn.addEventListener("click", () => {
          void submitInlineRename();
        });
      }

      if (inlineRenameCancelBtn) {
        inlineRenameCancelBtn.addEventListener("click", () => {
          closeInlineRenameEditor();
          setStatus("Rename canceled.", "info");
        });
      }

      if (inlineRenameInput) {
        inlineRenameInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void submitInlineRename();
            return;
          }
          if (event.key === "Escape") {
            event.preventDefault();
            closeInlineRenameEditor();
            setStatus("Rename canceled.", "info");
          }
        });
      }

      if (pickupListVendorSelect) {
        pickupListVendorSelect.addEventListener("change", () => {
          refreshWorkspaceChrome();
        });
      }

      deleteListBtn.addEventListener("click", () => {
        void deleteActiveShoppingList();
      });

      applyInventoryBtn.addEventListener("click", () => {
        void applyInventoryFromList();
      });

      if (inventoryCountSelect) {
        inventoryCountSelect.addEventListener("change", () => {
          updateListActionStates();
        });
      }

      if (applyInventoryCountBtn) {
        applyInventoryCountBtn.addEventListener("click", () => {
          void applyKitchenInventoryCount();
        });
      }

      if (newManualListBtn) {
        newManualListBtn.addEventListener("click", () => {
          void createManualShoppingList();
        });
      }

      if (addItemBtn) {
        addItemBtn.addEventListener("click", () => {
          void addItemToActiveList();
        });
      }

      if (addItemNameInput) {
        addItemNameInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void addItemToActiveList();
          }
        });
      }

      if (addItemQtyInput) {
        addItemQtyInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void addItemToActiveList();
          }
        });
      }

      refreshListsBtn.addEventListener("click", () => {
        void refreshSelectedShoppingList();
        void loadKitchenInventoryCounts().catch(() => {
          /* non-fatal */
        });
      });

      if (pickupSelectVisibleCheck) {
        pickupSelectVisibleCheck.addEventListener("change", () => {
          if (activePickupListDetail) {
            pickupSelectVisibleCheck.checked = false;
            return;
          }
          const visibleItems = visibleShoppingItems(activeShoppingDetail);
          visibleItems.forEach((item) => {
            const itemId = Number(item?.id);
            if (!Number.isFinite(itemId) || itemId <= 0) {
              return;
            }
            if (pickupSelectVisibleCheck.checked) {
              selectedPickupItemIds.add(itemId);
            } else {
              selectedPickupItemIds.delete(itemId);
            }
          });
          refreshWorkspaceChrome();
          renderShoppingRows(activeShoppingDetail || { items: [] });
        });
      }

      if (selectVendorPickupItemsBtn) {
        selectVendorPickupItemsBtn.addEventListener("click", () => {
          selectVisibleItemsForVendor();
        });
      }

      if (clearPickupSelectionBtn) {
        clearPickupSelectionBtn.addEventListener("click", () => {
          clearPickupSelection();
          setStatus("Selection cleared.", "info");
        });
      }

      if (createPickupListBtn) {
        createPickupListBtn.addEventListener("click", () => {
          void createPickupListFromSelection();
        });
      }

      if (closePickupViewBtn) {
        closePickupViewBtn.addEventListener("click", () => {
          closePickupListView();
          setStatus("Showing the master shopping list.", "ok");
        });
      }

      if (downloadPickupPdfBtn) {
        downloadPickupPdfBtn.addEventListener("click", () => {
          downloadPickupListPdf(activePickupListDetail);
        });
      }

      if (deletePickupListBtn) {
        deletePickupListBtn.addEventListener("click", () => {
          if (activePickupListDetail?.id) {
            void deletePickupList(activePickupListDetail.id);
          }
        });
      }

      void bootstrap();
