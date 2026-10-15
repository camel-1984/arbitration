const API_URL = "/api";
const FLAGS = ["major_defect", "damaged", "no_keys_or_docs", "pledge", "arrest_or_ban", "location_unknown"];
const MAKES = ["Lada", "Kia", "Hyundai", "Renault", "Toyota", "Volkswagen", "Skoda", "Chevrolet", "Ford", "Nissan",
  "Mitsubishi", "Mazda", "Opel", "Honda", "Mercedes-Benz", "BMW", "Audi", "Daewoo", "Chery", "Geely", "Haval", "UAZ"];

const form = document.getElementById("lot-form");
const description = document.getElementById("description");
const rubles = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });
const CURRENT_YEAR = new Date().getFullYear();
const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
}

document.getElementById("makes").innerHTML = MAKES.map((make) => `<option value="${make}">`).join("");

async function postJson(path, body) {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

function readForm() {
  const data = Object.fromEntries(new FormData(form));
  const lot = {
    make: data.make.trim(),
    model: data.model.trim(),
    year: Number(data.year),
    region: data.region.trim() || null,
    power_hp: data.power_hp ? Number(data.power_hp) : null,
    engine_cc: data.engine_cc ? Number(data.engine_cc) : null,
  };
  FLAGS.forEach((flag) => { lot[flag] = form.elements[flag].checked ? 1 : 0; });
  return lot;
}

function fillForm(features) {
  ["make", "model", "year", "power_hp", "engine_cc"].forEach((name) => {
    form.elements[name].value = features[name] ?? "";
  });
  FLAGS.forEach((flag) => { form.elements[flag].checked = features[flag] === 1; });
}

function roundToThousand(value) {
  return Math.round(value / 1000) * 1000;
}

function demoPrediction(lot) {
  const age = CURRENT_YEAR - lot.year;
  const base = 900000 * Math.pow(0.9, Math.max(0, age));
  const penalty = 1 - 0.25 * lot.major_defect - 0.1 * lot.damaged - 0.15 * lot.location_unknown;
  const p50 = roundToThousand(base * penalty);
  return {
    demo: true,
    p25: roundToThousand(p50 * 0.85),
    p50,
    p75: roundToThousand(p50 * 1.15),
    low_reliability: false,
    factors: [`Возраст автомобиля: ${age} лет`, `Марка и модель: ${lot.make} ${lot.model}`],
    comparables: [],
  };
}

const SLUGS = {
  drom: { "Mercedes-Benz": "mercedes-benz", "Great Wall": "great_wall", "Land Rover": "land_rover" },
  autoru: { Lada: "vaz", "Mercedes-Benz": "mercedes", "Great Wall": "great_wall", "Land Rover": "land_rover" },
};

function slug(value, site) {
  return SLUGS[site]?.[value] ?? value.trim().toLowerCase().replace(/\s+/g, "_");
}

function marketLinks(lot) {
  const yearFrom = lot.year - 1;
  const yearTo = lot.year + 1;
  const query = encodeURIComponent(`${lot.make} ${lot.model} ${lot.year}`);
  const dromMake = encodeURIComponent(slug(lot.make, "drom"));
  const dromModel = encodeURIComponent(slug(lot.model, "drom"));
  const autoruMake = encodeURIComponent(slug(lot.make, "autoru"));
  const autoruModel = encodeURIComponent(slug(lot.model, "autoru"));
  return [
    { site: "Авито", url: `https://www.avito.ru/rossiya/avtomobili?q=${query}` },
    { site: "Дром", url: `https://auto.drom.ru/${dromMake}/${dromModel}/?minyear=${yearFrom}&maxyear=${yearTo}` },
    { site: "Авто.ру", url: `https://auto.ru/rossiya/cars/${autoruMake}/${autoruModel}/used/?year_from=${yearFrom}&year_to=${yearTo}` },
  ].map((link) => ({ ...link, query: `${lot.make} ${lot.model}, ${yearFrom}–${yearTo} г.в.` }));
}

function renderMarketLinks(lot) {
  document.getElementById("market-links").innerHTML = marketLinks(lot).map((link) => `
    <a class="market-card" href="${escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer">
      <span class="site">${link.site}</span>
      <span class="query">${escapeHtml(link.query)}</span>
      <span class="open">Открыть объявления →</span>
    </a>`).join("");
}

function renderResult(result) {
  document.getElementById("p25").textContent = rubles.format(result.p25);
  document.getElementById("p50").textContent = rubles.format(result.p50);
  document.getElementById("p75").textContent = rubles.format(result.p75);
  document.getElementById("range-from").textContent = rubles.format(result.p25);
  document.getElementById("range-to").textContent = rubles.format(result.p75);
  document.getElementById("demo-note").classList.toggle("hidden", !result.demo);

  const reliability = document.getElementById("reliability");
  reliability.textContent = "Похожих лотов в истории мало, оценка ненадёжна.";
  reliability.classList.toggle("hidden", !result.low_reliability);

  document.getElementById("factors").innerHTML = result.factors.map((factor) => `<li>${escapeHtml(factor)}</li>`).join("");
  document.getElementById("comparables").innerHTML = result.comparables.length
    ? result.comparables.map((lot) => `
        <tr>
          <td>${escapeHtml(`${lot.make} ${lot.model}`)}</td>
          <td>${escapeHtml(lot.year)}</td>
          <td>${escapeHtml(lot.sale_date)}</td>
          <td>${rubles.format(lot.sale_price)}</td>
          <td><a href="${escapeHtml(lot.url)}" target="_blank" rel="noopener">карточка</a></td>
        </tr>`).join("")
    : `<tr><td colspan="5" class="hint">Появятся после подключения модели</td></tr>`;

  document.getElementById("result").classList.remove("hidden");
}

document.getElementById("extract-btn").addEventListener("click", async () => {
  if (!description.value.trim()) return;
  try {
    fillForm(await postJson("/extract", { text: description.value }));
  } catch {
    alert("Сервер разбора описания пока не подключён, заполните поля вручную.");
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const lot = readForm();
  let result;
  try {
    result = await postJson("/predict", lot);
  } catch {
    result = demoPrediction(lot);
  }
  renderResult(result);
  renderMarketLinks(lot);
});
