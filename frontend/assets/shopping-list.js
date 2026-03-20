      const retreatPlanSelect = document.getElementById("retreatPlanSelect");
      const selectAllRetreatsBtn = document.getElementById("selectAllRetreatsBtn");
      const clearRetreatsBtn = document.getElementById("clearRetreatsBtn");
      const phaseSelect = document.getElementById("phaseSelect");
      const subtractInventoryCheck = document.getElementById("subtractInventoryCheck");
      const includeZeroCheck = document.getElementById("includeZeroCheck");
      const generateBtn = document.getElementById("generateBtn");
      const shoppingListSelect = document.getElementById("shoppingListSelect");
      const inlineRenameWrap = document.getElementById("inlineRenameWrap");
      const inlineRenameInput = document.getElementById("inlineRenameInput");
      const inlineRenameSaveBtn = document.getElementById("inlineRenameSaveBtn");
      const inlineRenameCancelBtn = document.getElementById("inlineRenameCancelBtn");
      const loadListBtn = document.getElementById("loadListBtn");
      const deleteListBtn = document.getElementById("deleteListBtn");
      const applyInventoryBtn = document.getElementById("applyInventoryBtn");
      const refreshListsBtn = document.getElementById("refreshListsBtn");
      const shoppingBody = document.getElementById("shoppingBody");
      const shoppingTableWrap = document.querySelector(".shopping-table-wrap");
      const statusPill = document.getElementById("statusPill");
      const metricItems = document.getElementById("metricItems");
      const metricOrdered = document.getElementById("metricOrdered");
      const metricReceived = document.getElementById("metricReceived");
      const metricStatus = document.getElementById("metricStatus");
      const groupModeSelect = document.getElementById("groupModeSelect");
      const shoppingCategoryFilter = document.getElementById("shoppingCategoryFilter");
      const sourceBreakdownHint = document.getElementById("sourceBreakdownHint");

      let API_BASE = resolveApiBase();
      const DEFAULT_API_BASE = window.location.origin.replace(/\/+$/, "");
      const ALL_RETREATS_VALUE = "__ALL_RETREATS__";
      const RENAME_SELECTED_LIST_VALUE = "__RENAME_SELECTED_LIST__";
      let vendors = [];
      let shoppingLists = [];
      let activeListId = null;
      let activeListPhase = null;
      let activeShoppingDetail = null;
      let currentGroupMode = "category";
      let dropdownSelectedListId = null;
      let renameEditingListId = null;
      let selectedIngredientCategory = null;
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

          for (let j = 0; j < 8; j += 1) {
            const td = document.createElement("td");
            const line = document.createElement("div");
            line.className = "ui-skeleton-line skeleton-cell";
            if (j === 0 || j === 1 || j === 8) {
              line.classList.add("long");
            } else if (j === 7 || j === 8) {
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
        if (normalizedUnit === "tsp" || normalizedUnit === "tbsp" || normalizedUnit === "cup") {
          return `${numeric.toFixed(1)} ${unit}`;
        }
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
        const normalizedUnit = normalizeUnit(unit);
        if (normalizedUnit === "tsp" || normalizedUnit === "tbsp" || normalizedUnit === "cup") {
          return `${numeric.toFixed(1)} ${unit}`;
        }
        return `${Math.round(numeric)} ${unit}`;
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

      function updateListActionStates() {
        const hasList = Boolean(activeListId);
        deleteListBtn.disabled = !hasList;
        applyInventoryBtn.disabled = !(hasList && isInventoryEditablePhase(activeListPhase));
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
        setMetricValue(metricItems, detail?.item_count || 0);
        setMetricValue(metricOrdered, detail?.ordered_count || 0);
        setMetricValue(metricReceived, detail?.received_count || 0);
        setMetricValue(metricStatus, String(detail?.status || "draft").replace(/_/g, " "));
      }

      function ingredientCategoryName(item) {
        return String(item?.ingredient_category || "").trim() || "Uncategorized";
      }

      function categoryFilteredItems(items) {
        if (!selectedIngredientCategory) {
          return [...items];
        }
        return items.filter((item) => ingredientCategoryName(item) === selectedIngredientCategory);
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

      function inventoryInputStep(_unit) {
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
        if (Math.abs(numeric - Math.round(numeric)) < 1e-9) {
          return String(Math.round(numeric));
        }
        return String(Math.round(numeric * 100) / 100);
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
        const merged = [...options];
        if (normalizedSelectedUnit && !merged.includes(normalizedSelectedUnit)) {
          merged.unshift(normalizedSelectedUnit);
        }
        return Array.from(new Set(merged.filter(Boolean)));
      }

      function orderedUnitLabel(unit) {
        const normalized = normalizeUnit(unit);
        if (normalized === "kg") {
          return "kilograms";
        }
        if (normalized === "l") {
          return "liters";
        }
        return unit;
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
          option.textContent = orderedUnitLabel(unitOption);
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
          const rounded = roundEditableQuantity(value);
          input.value = formatEditableQuantityValue(rounded);
          lastGoodValue = input.value;
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
        ingredientTd.className = "shopping-need-cell";
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
        sourceTd.appendChild(createVendorSelect(item));
        tr.appendChild(sourceTd);

        const orderedAmountTd = document.createElement("td");
        orderedAmountTd.className = "shopping-action-cell";
        orderedAmountTd.appendChild(createOrderedAmountEditor(item));
        tr.appendChild(orderedAmountTd);

        const orderedTd = document.createElement("td");
        orderedTd.className = "shopping-action-cell text-center";
        orderedTd.appendChild(createToggle(item.ordered, (value) => {
          void updateShoppingItem(item.id, { ordered: value });
        }));
        tr.appendChild(orderedTd);

        const receivedTd = document.createElement("td");
        receivedTd.className = "shopping-action-cell text-center";
        receivedTd.appendChild(createToggle(item.received, (value) => {
          void updateShoppingItem(item.id, { received: value });
        }));
        tr.appendChild(receivedTd);

        const notesTd = document.createElement("td");
        notesTd.className = "shopping-action-cell";
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
        const allItems = Array.isArray(detail?.items) ? detail.items : [];
        const rawBreakdownCount = allItems.filter(
          (item) => Array.isArray(item?.source_breakdown) && item.source_breakdown.length > 0
        ).length;
        const withBreakdownCount = allItems.filter(
          (item) => Array.isArray(item?.source_breakdown)
            && item.source_breakdown.length > 0
            && meetsContributionThreshold(item?.required_qty, item?.required_unit)
        ).length;
        if (sourceBreakdownHint) {
          if (!allItems.length) {
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
        renderShoppingCategoryFilter(allItems);
        const visibleItems = categoryFilteredItems(allItems);

        if (!allItems.length) {
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

        if (!visibleItems.length) {
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 8;
          td.className = "text-muted small py-3";
          td.textContent = `No items in ${selectedIngredientCategory}.`;
          tr.appendChild(td);
          shoppingBody.appendChild(tr);
          triggerFadeIn(shoppingBody);
          return;
        }

        if (currentGroupMode === "source") {
          sortedSourceEntries(visibleItems).forEach((sourceEntry) => {
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

        sortedCategoryEntries(visibleItems).forEach(([category, items]) => {
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
          dropdownSelectedListId = Number(detail.id);
          activeListPhase = String(detail.phase || "").trim().toLowerCase() || null;
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

      async function refreshSelectedShoppingList() {
        const targetListId = Number(selectedListIdForActions() || 0);
        if (!Number.isFinite(targetListId) || targetListId <= 0) {
          const count = await loadShoppingLists({ showBusy: true });
          setStatus(`Lists refreshed. ${count} available.`, "ok");
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
          activeShoppingDetail = detail;
          activeListId = detail.id;
          dropdownSelectedListId = Number(detail.id);
          activeListPhase = String(detail.phase || "").trim().toLowerCase() || null;
          updateListActionStates();
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
          activeShoppingDetail = detail;
          activeListPhase = String(detail.phase || "").trim().toLowerCase() || null;
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
            activeShoppingDetail = detail;
            activeListId = detail.id;
            activeListPhase = String(detail.phase || "").trim().toLowerCase() || null;
            updateListActionStates();
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

      deleteListBtn.addEventListener("click", () => {
        void deleteActiveShoppingList();
      });

      applyInventoryBtn.addEventListener("click", () => {
        void applyInventoryFromList();
      });

      refreshListsBtn.addEventListener("click", () => {
        void refreshSelectedShoppingList();
      });

      void bootstrap();
