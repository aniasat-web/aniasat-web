(function () {
  function escapeHtml(value) {
    var div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  function getNumericAttr(input, name, fallback) {
    var raw = input.getAttribute(name);
    if (raw == null || raw === "") return fallback;
    var parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function formatValue(value) {
    if (!Number.isFinite(value)) return "0";
    if (Math.abs(value - Math.round(value)) < 0.000001) return String(Math.round(value));
    return String(Math.round(value * 1000) / 1000);
  }

  function clampValue(input, value) {
    var min = getNumericAttr(input, "min", -Infinity);
    var max = getNumericAttr(input, "max", Infinity);
    var next = value;
    if (Number.isFinite(min) && next < min) next = min;
    if (Number.isFinite(max) && next > max) next = max;
    return next;
  }

  function adjustInputValue(input, direction) {
    if (!(input instanceof HTMLInputElement)) return;
    if (input.disabled || input.readOnly) return;

    var step = getNumericAttr(input, "step", 1);
    if (!(step > 0)) step = 1;
    var current = Number(input.value);
    if (!Number.isFinite(current)) current = getNumericAttr(input, "min", 0);
    if (!Number.isFinite(current)) current = 0;
    var delta = direction === "down" ? -step : step;
    var next = clampValue(input, current + delta);
    input.value = formatValue(next);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.focus();
    input.select();
  }

  function buildInputMarkup(options) {
    var opts = options || {};
    var wrapperClasses = ["inventory-stepper"];
    if (opts.compact) wrapperClasses.push("inventory-stepper--compact");
    if (opts.inline) wrapperClasses.push("inventory-stepper--inline");

    var inputClasses = ["form-control", "inventory-stepper-input"];
    if (opts.small !== false) inputClasses.push("form-control-sm");
    if (opts.inputClassName) inputClasses.push(String(opts.inputClassName));

    var attrs = ['type="' + escapeHtml(opts.type || "number") + '"'];
    if (opts.id) attrs.push('id="' + escapeHtml(opts.id) + '"');
    if (opts.min != null) attrs.push('min="' + escapeHtml(opts.min) + '"');
    attrs.push('step="' + escapeHtml(opts.step != null ? opts.step : "1") + '"');
    attrs.push('inputmode="' + escapeHtml(opts.inputMode || "numeric") + '"');
    if (opts.max != null) attrs.push('max="' + escapeHtml(opts.max) + '"');
    if (opts.value != null) attrs.push('value="' + escapeHtml(opts.value) + '"');
    if (opts.placeholder) attrs.push('placeholder="' + escapeHtml(opts.placeholder) + '"');
    if (opts.title) attrs.push('title="' + escapeHtml(opts.title) + '"');
    if (opts.disabled) attrs.push("disabled");
    if (opts.readOnly) attrs.push("readonly");
    if (opts.required) attrs.push("required");
    if (opts.extraAttributes && typeof opts.extraAttributes === "object") {
      Object.keys(opts.extraAttributes).forEach(function (name) {
        var value = opts.extraAttributes[name];
        if (value === false || value == null) return;
        if (value === true) {
          attrs.push(escapeHtml(name));
          return;
        }
        attrs.push(escapeHtml(name) + '="' + escapeHtml(value) + '"');
      });
    }

    var buttonDisabled = opts.disabled || opts.readOnly ? " disabled" : "";
    var decrementLabel = escapeHtml(opts.decrementLabel || "Decrease value");
    var incrementLabel = escapeHtml(opts.incrementLabel || "Increase value");

    return (
      '<div class="' + escapeHtml(wrapperClasses.join(" ")) + '">' +
        '<button type="button" class="btn btn-outline-secondary inventory-stepper-btn" data-inventory-stepper-action="down" aria-label="' + decrementLabel + '"' + buttonDisabled + '>-</button>' +
        '<input class="' + escapeHtml(inputClasses.join(" ")) + '" ' + attrs.join(" ") + ">" +
        '<button type="button" class="btn btn-outline-secondary inventory-stepper-btn" data-inventory-stepper-action="up" aria-label="' + incrementLabel + '"' + buttonDisabled + '>+</button>' +
      "</div>"
    );
  }

  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!(target instanceof Element)) return;
    var button = target.closest("button[data-inventory-stepper-action]");
    if (!(button instanceof HTMLButtonElement)) return;
    var wrapper = button.closest(".inventory-stepper");
    if (!(wrapper instanceof HTMLElement)) return;
    var input = wrapper.querySelector(".inventory-stepper-input");
    if (!(input instanceof HTMLInputElement)) return;
    event.preventDefault();
    adjustInputValue(input, button.getAttribute("data-inventory-stepper-action") === "down" ? "down" : "up");
  });

  document.addEventListener("wheel", function (event) {
    var target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    if (!target.classList.contains("inventory-stepper-input")) return;
    if (document.activeElement !== target) return;
    event.preventDefault();
  }, { passive: false });

  window.InventoryQuantityControls = {
    renderInput: buildInputMarkup,
    adjustInputValue: adjustInputValue,
  };
})();
