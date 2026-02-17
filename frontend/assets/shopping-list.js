      const retreatPlanSelect = document.getElementById("retreatPlanSelect");
      const selectAllRetreatsBtn = document.getElementById("selectAllRetreatsBtn");
      const clearRetreatsBtn = document.getElementById("clearRetreatsBtn");
      const phaseSelect = document.getElementById("phaseSelect");
      const purchaseTierSelect = document.getElementById("purchaseTierSelect");
      const listNameInput = document.getElementById("listNameInput");
      const subtractInventoryCheck = document.getElementById("subtractInventoryCheck");
      const includeZeroCheck = document.getElementById("includeZeroCheck");
      const generateBtn = document.getElementById("generateBtn");
      const shoppingListSelect = document.getElementById("shoppingListSelect");
      const loadListBtn = document.getElementById("loadListBtn");
      const applyInventoryBtn = document.getElementById("applyInventoryBtn");
      const carryForwardBtn = document.getElementById("carryForwardBtn");
      const refreshListsBtn = document.getElementById("refreshListsBtn");
      const shoppingBody = document.getElementById("shoppingBody");
      const shoppingTableWrap = document.querySelector(".shopping-table-wrap");
      const statusPill = document.getElementById("statusPill");
      const metricItems = document.getElementById("metricItems");
      const metricOrdered = document.getElementById("metricOrdered");
      const metricReceived = document.getElementById("metricReceived");
      const metricStatus = document.getElementById("metricStatus");
      const groupModeSelect = document.getElementById("groupModeSelect");
      const stepTwoModalEl = document.getElementById("stepTwoModal");
      const stepTwoNameInput = document.getElementById("stepTwoNameInput");
      const confirmStepTwoBtn = document.getElementById("confirmStepTwoBtn");
      function createStepTwoModalInstance(element) {
        if (!element || !window.bootstrap || !window.bootstrap.Modal) {
          return null;
        }
        const modalApi = window.bootstrap.Modal;
        if (typeof modalApi.getOrCreateInstance === "function") {
          try {
            return modalApi.getOrCreateInstance(element);
          } catch (_error) {
            return null;
          }
        }
        if (typeof modalApi === "function") {
          try {
            return new modalApi(element);
          } catch (_error) {
            return null;
          }
        }
        return null;
      }
      const stepTwoModal = createStepTwoModalInstance(stepTwoModalEl);
      if (stepTwoModalEl && stepTwoNameInput) {
        stepTwoModalEl.addEventListener("shown.bs.modal", () => {
          stepTwoNameInput.focus();
          stepTwoNameInput.select();
        });
      }

      let API_BASE = resolveApiBase();
      const DEFAULT_API_BASE = window.location.origin.replace(/\/+$/, "");
      const ALL_RETREATS_VALUE = "__ALL_RETREATS__";
      let vendors = [];
      let shoppingLists = [];
      let activeListId = null;
      let activeListPhase = null;
      let activeShoppingDetail = null;
      let currentGroupMode = "category";

      function resolveApiBase() {
        const queryValue = new URLSearchParams(window.location.search).get("api");
        const base = queryValue && queryValue.trim() ? queryValue.trim() : window.location.origin;
        return base.replace(/\/+$/, "");
      }

      function apiUrl(path) {
        return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
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

          for (let j = 0; j < 8; j += 1) {
            const td = document.createElement("td");
            const line = document.createElement("div");
            line.className = "ui-skeleton-line skeleton-cell";
            if (j === 0 || j === 7) {
              line.classList.add("long");
            } else if (j === 5 || j === 6) {
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
        if (unit === "kg" || unit === "l") {
          return `${numeric.toFixed(2).replace(/\.00$/, "")} ${unit}`;
        }
        if (Math.abs(numeric - Math.round(numeric)) < 1e-9) {
          return `${Math.round(numeric)} ${unit}`;
        }
        return `${numeric.toFixed(1).replace(/\.0$/, "")} ${unit}`;
      }

      function formatNeededQty(qty, unit) {
        if (qty == null || !unit) return "—";
        const numeric = Number(qty);
        if (!Number.isFinite(numeric)) return "—";
        return `${Math.round(numeric)} ${unit}`;
      }

      function syncTierSelectionForPhase() {
        const phase = phaseSelect.value;
        if (phase === "bulk" || phase === "fresh" || phase === "daily") {
          Array.from(purchaseTierSelect.options).forEach((opt) => {
            opt.selected = opt.value === phase;
          });
          purchaseTierSelect.disabled = true;
          return;
        }
        purchaseTierSelect.disabled = false;
      }

      function selectedPurchaseTiers() {
        return Array.from(purchaseTierSelect.selectedOptions)
          .map((opt) => String(opt.value || "").trim())
          .filter(Boolean);
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
      }

      function renderShoppingListOptions() {
        shoppingListSelect.innerHTML = "";
        if (!shoppingLists.length) {
          const option = document.createElement("option");
          option.value = "";
          option.textContent = "No shopping lists yet";
          shoppingListSelect.appendChild(option);
          return;
        }

        shoppingLists.forEach((list) => {
          const option = document.createElement("option");
          option.value = String(list.id);
          const label = `${list.name} • ${list.item_count} items • ${list.status}`;
          option.textContent = label;
          if (activeListId && Number(activeListId) === Number(list.id)) {
            option.selected = true;
          }
          shoppingListSelect.appendChild(option);
        });
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
          renderShoppingListOptions();
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

      function updateListActionStates() {
        const hasList = Boolean(activeListId);
        carryForwardBtn.disabled = !hasList;
        applyInventoryBtn.disabled = !(hasList && isInventoryEditablePhase(activeListPhase));
      }

      function setSummary(detail) {
        setMetricValue(metricItems, detail?.item_count || 0);
        setMetricValue(metricOrdered, detail?.ordered_count || 0);
        setMetricValue(metricReceived, detail?.received_count || 0);
        setMetricValue(metricStatus, String(detail?.status || "draft").replace(/_/g, " "));
      }

      function setGroupMode(mode) {
        currentGroupMode = mode === "source" ? "source" : "category";
        if (groupModeSelect) {
          groupModeSelect.value = currentGroupMode;
        }
      }

      function isStepTwoList(detail) {
        const name = String(detail?.name || "").trim().toLowerCase();
        return name.includes("step 2");
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

      function inventoryInputStep(_unit) {
        return "1";
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
          ? String(Math.round(Number(item.in_stock_qty)))
          : "0";

        let lastGoodValue = input.value;
        input.addEventListener("change", () => {
          const value = Number(input.value);
          if (!Number.isFinite(value) || value < 0) {
            input.value = lastGoodValue;
            setStatus("Current inventory must be a non-negative number.", "err");
            return;
          }
          const rounded = Math.round(value);
          input.value = String(rounded);
          lastGoodValue = String(rounded);
          void updateShoppingItem(item.id, { inStockQty: rounded });
        });

        const unit = document.createElement("span");
        unit.className = "qty-chip";
        unit.textContent = String(item.in_stock_unit || item.required_unit || "").trim() || "unit";

        wrapper.appendChild(input);
        wrapper.appendChild(unit);
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

      function sortedCategoryEntries(items) {
        const grouped = new Map();
        items.forEach((item) => {
          const category = String(item.ingredient_category || "").trim() || "Uncategorized";
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
        return String(item.vendor_name || "").trim() || "Unassigned Source";
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

        const ingredientTd = document.createElement("td");
        ingredientTd.innerHTML = `<div class="ingredient-name">${item.ingredient_name}</div>`;
        tr.appendChild(ingredientTd);

        const requiredTd = document.createElement("td");
        requiredTd.innerHTML = `<span class="qty-chip">${formatNeededQty(item.required_qty, item.required_unit)}</span>`;
        tr.appendChild(requiredTd);

        const stockTd = document.createElement("td");
        if (inventoryEditable) {
          stockTd.appendChild(createInventoryEditor(item));
        } else {
          stockTd.innerHTML = `<span class="qty-chip">${formatNeededQty(item.in_stock_qty, item.in_stock_unit)}</span>`;
        }
        tr.appendChild(stockTd);

        const buyTd = document.createElement("td");
        buyTd.innerHTML = `<span class="qty-chip buy">${formatNeededQty(item.to_buy_qty, item.to_buy_unit)}</span>`;
        tr.appendChild(buyTd);

        const sourceTd = document.createElement("td");
        sourceTd.appendChild(createVendorSelect(item));
        tr.appendChild(sourceTd);

        const orderedTd = document.createElement("td");
        orderedTd.className = "text-center";
        orderedTd.appendChild(createToggle(item.ordered, (value) => {
          void updateShoppingItem(item.id, { ordered: value });
        }));
        tr.appendChild(orderedTd);

        const receivedTd = document.createElement("td");
        receivedTd.className = "text-center";
        receivedTd.appendChild(createToggle(item.received, (value) => {
          void updateShoppingItem(item.id, { received: value });
        }));
        tr.appendChild(receivedTd);

        const notesTd = document.createElement("td");
        const notesInput = document.createElement("input");
        notesInput.type = "text";
        notesInput.className = "form-control form-control-sm";
        notesInput.placeholder = "optional";
        notesInput.value = item.notes || "";
        notesInput.addEventListener("change", () => {
          void updateShoppingItem(item.id, { notes: notesInput.value.trim() || null });
        });
        notesTd.appendChild(notesInput);
        tr.appendChild(notesTd);

        return tr;
      }

      function renderCategoryHeaderRow(category, itemCount) {
        const headerTr = document.createElement("tr");
        headerTr.className = "category-row";
        const headerTd = document.createElement("td");
        headerTd.colSpan = 8;

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
        const inventoryEditable = isInventoryEditablePhase(detail?.phase || activeListPhase);

        if (!detail?.items?.length) {
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 8;
          td.className = "text-muted small py-3";
          td.textContent = "No items found for this shopping list.";
          tr.appendChild(td);
          shoppingBody.appendChild(tr);
          triggerFadeIn(shoppingBody);
          return;
        }

        if (currentGroupMode === "source") {
          sortedSourceEntries(detail.items).forEach((sourceEntry) => {
            const sourceTr = document.createElement("tr");
            sourceTr.className = "source-row";
            const sourceTd = document.createElement("td");
            sourceTd.colSpan = 8;
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
          return;
        }

        sortedCategoryEntries(detail.items).forEach(([category, items]) => {
          shoppingBody.appendChild(renderCategoryHeaderRow(category, items.length));

          items.forEach((item) => {
            shoppingBody.appendChild(renderShoppingItemRow(item, inventoryEditable));
          });
        });
        triggerFadeIn(shoppingBody);
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
          activeShoppingDetail = detail;
          activeListId = detail.id;
          activeListPhase = String(detail.phase || "").trim().toLowerCase() || null;
          if (isStepTwoList(detail)) {
            setGroupMode("source");
          }
          updateListActionStates();
          setSummary(detail);
          renderShoppingRows(detail);
        } catch (error) {
          if (shoppingTableWrap) {
            shoppingTableWrap.classList.remove("is-loading");
          }
          throw error;
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
          activeShoppingDetail = detail;
          activeListPhase = String(detail.phase || "").trim().toLowerCase() || null;
          if (isStepTwoList(detail)) {
            setGroupMode("source");
          }
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
          name: listNameInput.value.trim() || null,
          phase: phaseSelect.value,
          purchaseTiers: selectedPurchaseTiers(),
          subtractInventory: Boolean(subtractInventoryCheck.checked),
          includeZeroToBuy: Boolean(includeZeroCheck.checked),
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
          activeShoppingDetail = detail;
          activeListId = detail.id;
          activeListPhase = String(detail.phase || "").trim().toLowerCase() || null;
          if (isStepTwoList(detail)) {
            setGroupMode("source");
          }
          updateListActionStates();
          setSummary(detail);
          renderShoppingRows(detail);
          await loadShoppingLists();

          const missing = Array.isArray(detail.missing_recipes) ? detail.missing_recipes : [];
          if (missing.length) {
            setStatus(`Generated with ${missing.length} missing recipes.`, "err");
          } else {
            setStatus("Shopping list generated.", "ok");
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

      async function createStepTwoOrderWithName(customName) {
        if (!activeListId) {
          setStatus("Load a shopping list first.", "err");
          return;
        }

        const payload = {
          name: String(customName || "").trim() || null,
        };

        try {
          setButtonBusy(carryForwardBtn, true, "Creating");
          setButtonBusy(confirmStepTwoBtn, true, "Creating");
          setStatus("Creating Step 2 order...", "info", { busy: true });
          renderShoppingSkeletonRows(8);
          const response = await fetch(apiUrl(`/api/shopping-lists/${activeListId}/carry-forward`), {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!response.ok) {
            throw new Error(await parseApiError(response));
          }
          const detail = await response.json();
          activeShoppingDetail = detail;
          activeListId = detail.id;
          activeListPhase = String(detail.phase || "").trim().toLowerCase() || null;
          setGroupMode("source");
          updateListActionStates();
          setSummary(detail);
          renderShoppingRows(detail);
          await loadShoppingLists();
          const carried = Number(detail.carried_item_count || 0);
          setStatus(`Step 2 order created (${carried} items).`, "ok");
        } catch (error) {
          setStatus(error instanceof Error ? error.message : String(error), "err");
          if (shoppingTableWrap) {
            shoppingTableWrap.classList.remove("is-loading");
          }
        } finally {
          setButtonBusy(carryForwardBtn, false, "Creating");
          setButtonBusy(confirmStepTwoBtn, false, "Creating");
        }
      }

      function openStepTwoModal() {
        if (!activeListId) {
          setStatus("Load a shopping list first.", "err");
          return;
        }
        if (stepTwoNameInput) {
          stepTwoNameInput.value = "";
        }
        if (stepTwoModal) {
          stepTwoModal.show();
          return;
        }
        void createStepTwoOrderWithName("");
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

      async function bootstrap() {
        try {
          setStatus("Loading shopping workspace...", "info", { busy: true });
          renderShoppingSkeletonRows(10);
          setGroupMode("category");
          syncTierSelectionForPhase();
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
        } catch (error) {
          if (shoppingTableWrap) {
            shoppingTableWrap.classList.remove("is-loading");
          }
          setStatus(error instanceof Error ? error.message : String(error), "err");
        }
      }

      phaseSelect.addEventListener("change", syncTierSelectionForPhase);
      groupModeSelect.addEventListener("change", () => {
        setGroupMode(groupModeSelect.value);
        renderShoppingRows(activeShoppingDetail || { items: [] });
      });
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
        const selected = Number(shoppingListSelect.value || 0);
        if (!selected) {
          setStatus("Select a shopping list to load.", "err");
          return;
        }
        setButtonBusy(loadListBtn, true, "Loading");
        void loadShoppingListDetail(selected)
          .then(() => setStatus("List loaded.", "ok"))
          .catch((error) => setStatus(error instanceof Error ? error.message : String(error), "err"))
          .finally(() => setButtonBusy(loadListBtn, false, "Loading"));
      });

      carryForwardBtn.addEventListener("click", openStepTwoModal);

      if (confirmStepTwoBtn) {
        confirmStepTwoBtn.addEventListener("click", () => {
          const customName = stepTwoNameInput ? stepTwoNameInput.value : "";
          if (stepTwoModal) {
            stepTwoModal.hide();
          }
          void createStepTwoOrderWithName(customName);
        });
      }

      applyInventoryBtn.addEventListener("click", () => {
        void applyInventoryFromList();
      });

      refreshListsBtn.addEventListener("click", () => {
        void loadShoppingLists({ showBusy: true })
          .then(() => setStatus("Lists refreshed.", "ok"))
          .catch((error) => setStatus(error instanceof Error ? error.message : String(error), "err"));
      });

      void bootstrap();
