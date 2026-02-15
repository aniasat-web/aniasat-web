const API_BASE = "http://localhost:8000";

const body = document.getElementById("ingredient-body");
const output = document.getElementById("output");

function addRow(name = "", qty = "", unit = "") {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input type="text" class="name" value="${name}" placeholder="e.g. Rice (Sona Masoori)" required /></td>
    <td><input type="number" class="qty" value="${qty}" min="0.001" step="0.001" required /></td>
    <td><input type="text" class="unit" value="${unit}" placeholder="cup, g, kg, tbsp..." required /></td>
    <td><button type="button" class="remove">Remove</button></td>
  `;
  tr.querySelector(".remove").addEventListener("click", () => tr.remove());
  body.appendChild(tr);
}

addRow("Rice (Sona Masoori)", "2", "cup");
addRow("Toor Dal", "1.5", "cup");
addRow("Cilantro", "4", "bunches");


document.getElementById("add-row").addEventListener("click", () => addRow());

document.getElementById("scale-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const baseServings = Number(document.getElementById("base-servings").value);
  const targetServings = Number(document.getElementById("target-servings").value);

  const ingredients = Array.from(body.querySelectorAll("tr")).map((tr) => ({
    name: tr.querySelector(".name").value.trim(),
    quantity: Number(tr.querySelector(".qty").value),
    unit: tr.querySelector(".unit").value.trim(),
  }));

  const payload = {
    base_servings: baseServings,
    target_servings: targetServings,
    ingredients,
  };

  try {
    const res = await fetch(`${API_BASE}/api/scale-preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Request failed: ${res.status}`);
    }

    const data = await res.json();
    output.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    output.textContent = `Error: ${err.message}`;
  }
});
