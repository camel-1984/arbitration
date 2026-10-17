const API_URL = "/api";
const FLAGS = ["major_defect", "damaged", "no_keys_or_docs", "pledge", "arrest_or_ban", "location_unknown"];
const OTHER_MODEL = "__other__";

const form = document.getElementById("lot-form");
const description = document.getElementById("description");
const rubles = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });
const CURRENT_YEAR = new Date().getFullYear();
const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
}

const makeSelect = form.elements.make;
const modelSelect = form.elements.model;
const modelOther = form.elements.model_other;
let catalog = { makes: {}, regions: [], timing_days: null };

function options(values, placeholder) {
  return [`<option value="">${placeholder}</option>`, ...values.map((v) => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`)].join("");
}

function syncOtherModel() {
  modelOther.classList.toggle("hidden", modelSelect.value !== OTHER_MODEL);
  modelOther.required = modelSelect.value === OTHER_MODEL;
}

function fillModels(selected = "") {
  const models = catalog.makes[makeSelect.value] ?? [];
  modelSelect.innerHTML = options(models, makeSelect.value ? "выберите модель" : "сначала выберите марку")
    + (makeSelect.value ? `<option value="${OTHER_MODEL}">другая модель…</option>` : "");
  modelSelect.disabled = !makeSelect.value;
  const known = models.includes(selected);
  if (known) modelSelect.value = selected;
  else modelSelect.value = selected ? OTHER_MODEL : "";
  modelOther.value = known ? "" : selected;
  syncOtherModel();
}

function setMake(make) {
  if (make && !catalog.makes[make]) {
    catalog.makes[make] = [];
    makeSelect.insertAdjacentHTML("beforeend", `<option value="${escapeHtml(make)}">${escapeHtml(make)}</option>`);
  }
  makeSelect.value = make ?? "";
}

async function loadCatalog() {
  try {
    catalog = await (await fetch("catalog.json")).json();
  } catch {
    catalog = { makes: {}, regions: [], timing_days: null };
  }
  makeSelect.innerHTML = options(Object.keys(catalog.makes), "выберите марку");
  form.elements.region.innerHTML = `<option value="">не указан</option>`
    + catalog.regions.map((r) => `<option value="${escapeHtml(r.id)}">${escapeHtml(r.name)}</option>`).join("");
  fillModels();
}

makeSelect.addEventListener("change", () => {
  fillModels();
  if (isInvalid("model")) validate("model");
});
modelSelect.addEventListener("change", () => {
  syncOtherModel();
  if (modelSelect.value === OTHER_MODEL) modelOther.focus();
});

const wholeNumber = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });

function readNumber(name) {
  const raw = form.elements[name].value.replace(/\s/g, "").replace(",", ".");
  return raw === "" || Number.isNaN(Number(raw)) ? null : Number(raw);
}

function setNumber(name, value) {
  const input = form.elements[name];
  if (value === null || value === undefined) input.value = "";
  else input.value = PRICE_FIELDS.includes(name) ? wholeNumber.format(value) : String(value);
}

const PRICE_FIELDS = ["first_price", "blind_estimate"];

function formatPriceInput(input) {
  const digits = input.value.replace(/\D/g, "");
  input.value = digits ? wholeNumber.format(Number(digits)) : "";
}

PRICE_FIELDS.forEach((name) => form.elements[name].addEventListener("input", (event) => formatPriceInput(event.target)));

function keepDecimal(value) {
  const [whole, ...rest] = value.replace(/[^\d.,]/g, "").split(/[.,]/);
  return rest.length ? `${whole},${rest.join("")}` : whole;
}

form.elements.year.addEventListener("input", (event) => {
  event.target.value = event.target.value.replace(/\D/g, "");
});
["power_hp", "engine_cc"].forEach((name) => {
  form.elements[name].addEventListener("input", (event) => {
    event.target.value = keepDecimal(event.target.value);
  });
});

const YEAR_MIN = 1960;

const MAX = { year: CURRENT_YEAR, power_hp: 1000, engine_cc: 8500, first_price: 50_000_000, blind_estimate: 50_000_000 };

function outOfRange(value, min, max, message) {
  return value === null || (value >= min && value <= max) ? "" : message;
}

const CHECKS = {
  make: () => (makeSelect.value ? "" : "Выберите марку"),
  model: () => {
    if (!makeSelect.value) return "";
    if (!modelSelect.value) return "Выберите модель";
    if (modelSelect.value !== OTHER_MODEL) return "";
    const value = modelOther.value.trim();
    if (!value) return "Укажите модель";
    return /^[\p{L}\d][\p{L}\d .\-/+]*$/u.test(value) ? "" : "Только буквы, цифры, пробел и знаки . - / +";
  },
  year: () => {
    const raw = form.elements.year.value;
    if (!raw) return "Укажите год выпуска";
    const year = Number(raw);
    return raw.length === 4 && year >= YEAR_MIN && year <= MAX.year ? "" : `Год от ${YEAR_MIN} до ${CURRENT_YEAR}`;
  },
  power_hp: () => outOfRange(readNumber("power_hp"), 30, MAX.power_hp, "Мощность от 30 до 1000 л.с."),
  engine_cc: () => {
    const value = readNumber("engine_cc");
    if (value !== null && value < 10) return "Укажите в куб. см: 1,6 л = 1600";
    return outOfRange(value, 500, MAX.engine_cc, "Объём от 500 до 8500 куб. см");
  },
  first_price: () => outOfRange(readNumber("first_price"), 1000, MAX.first_price, "Цена от 1 000 до 50 000 000 руб."),
  blind_estimate: () => outOfRange(readNumber("blind_estimate"), 1000, MAX.blind_estimate, "Цена от 1 000 до 50 000 000 руб."),
};

function controlsOf(name) {
  return name === "model" ? [modelSelect, modelOther] : [form.elements[name]];
}

function errorOf(name) {
  const field = form.elements[name].closest(".field");
  let error = field.querySelector(".field-error");
  if (!error) {
    error = document.createElement("span");
    error.className = "field-error";
    error.id = `${name}-error`;
    field.append(error);
    controlsOf(name).forEach((control) => control.setAttribute("aria-describedby", error.id));
  }
  return error;
}

function validate(name) {
  const message = CHECKS[name]();
  errorOf(name).textContent = message;
  controlsOf(name).forEach((control) => {
    if (message) control.setAttribute("aria-invalid", "true");
    else control.removeAttribute("aria-invalid");
  });
  return !message;
}

function isInvalid(name) {
  return controlsOf(name).some((control) => control.hasAttribute("aria-invalid"));
}

Object.keys(CHECKS).forEach((name) => {
  controlsOf(name).forEach((control) => {
    control.addEventListener("change", () => validate(name));
    control.addEventListener("input", () => {
      if (isInvalid(name) || (name in MAX && readNumber(name) > MAX[name])) validate(name);
    });
  });
});

function validateAll() {
  const invalid = Object.keys(CHECKS).filter((name) => !validate(name));
  if (invalid.length) {
    const control = controlsOf(invalid[0]).find((c) => !c.classList.contains("hidden"));
    control.focus();
  }
  return invalid.length === 0;
}

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
  const lot = {
    make: makeSelect.value,
    model: modelSelect.value === OTHER_MODEL ? modelOther.value.trim() : modelSelect.value,
    year: readNumber("year"),
    region: form.elements.region.value || null,
    power_hp: readNumber("power_hp"),
    engine_cc: readNumber("engine_cc"),
    first_price: readNumber("first_price"),
  };
  FLAGS.forEach((flag) => { lot[flag] = form.elements[flag].checked ? 1 : 0; });
  const source = current.source;
  if (source) Object.assign(lot, { debt_type: source.debt_type ?? null, n_images: source.n_images ?? null, arbman_sro: source.arbman_sro ?? null, trade_id: source.trade_id ?? null });
  return lot;
}

function fillForm(features) {
  setMake(features.make);
  fillModels(features.model ?? "");
  if (features.year) setNumber("year", features.year);
  if (features.region && catalog.regions.some((r) => r.id === features.region)) form.elements.region.value = features.region;
  if (features.first_price) setNumber("first_price", features.first_price);
  if (features.description) description.value = features.description;
  setNumber("power_hp", features.power_hp);
  setNumber("engine_cc", features.engine_cc);
  FLAGS.forEach((flag) => { form.elements[flag].checked = features[flag] === 1; });
  ["make", "model", "year", "power_hp", "engine_cc", "first_price"].forEach((name) => {
    if (isInvalid(name) || controlsOf(name).some((c) => c.value)) validate(name);
  });
}

function roundToThousand(value) {
  return Math.round(value / 1000) * 1000;
}

function yearsWord(n) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "год";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "года";
  return "лет";
}

const LADDER_STEPS = [0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3];

function roundPrice(value) {
  let step = 1000;
  if (value >= 200000) step = 10000;
  else if (value >= 50000) step = 5000;
  return Math.round(value / step) * step;
}

function quartiles(p50, spread) {
  return { p25: roundToThousand(p50 * (1 - spread)), p50, p75: roundToThousand(p50 * (1 + spread)) };
}

function demoPoint(market, typicalPrice, price) {
  const logit = Math.log(0.22 / 0.78) - 4 * Math.log(price / typicalPrice);
  const salePrice = roundToThousand(market.p50 * Math.pow(price / typicalPrice, 0.35));
  return { price, p_first: 1 / (1 + Math.exp(-logit)), sale: quartiles(salePrice, 0.18) };
}

function demoPrediction(lot) {
  const age = CURRENT_YEAR - lot.year;
  const base = 900000 * Math.pow(0.9, Math.max(0, age));
  const penalty = 1 - 0.25 * lot.major_defect - 0.1 * lot.damaged - 0.15 * lot.location_unknown;
  const market = quartiles(roundToThousand(base * penalty), 0.15);
  const typicalPrice = roundPrice(market.p50 * 1.4);
  const prices = new Set(LADDER_STEPS.map((k) => roundPrice(typicalPrice * k)));
  if (lot.first_price) prices.add(lot.first_price);
  const curve = [...prices].sort((a, b) => a - b).map((price) => ({
    ...demoPoint(market, typicalPrice, price),
    typical: price === typicalPrice,
    own: price === lot.first_price,
  }));
  const factors = [{ label: `Возраст автомобиля: ${age} ${yearsWord(age)}`, effect: Math.pow(0.9, age - 14) - 1 }];
  if (lot.major_defect) factors.push({ label: "Серьёзная техническая неисправность", effect: -0.25 });
  if (lot.damaged) factors.push({ label: "Повреждения кузова", effect: -0.1 });
  if (lot.location_unknown) factors.push({ label: "Местонахождение неизвестно", effect: -0.15 });
  factors.push({ label: `Марка и модель: ${lot.make} ${lot.model}`, effect: 0.08 });
  const months = ["2026-03-14", "2025-12-02", "2025-10-21", "2025-08-07"];
  return {
    demo: true,
    typical_start: { p25: roundPrice(typicalPrice * 0.9), p50: typicalPrice, p75: roundPrice(typicalPrice * 1.1) },
    market,
    curve,
    low_reliability: false,
    factors,
    comparables: months.map((date, i) => ({
      make: lot.make,
      model: lot.model,
      year: lot.year + [0, -1, 1, 0][i],
      sale_date: date,
      sale_price: roundToThousand(market.p50 * [1.04, 0.88, 1.12, 0.95][i]),
      url: null,
    })),
  };
}

async function predict(lot) {
  try {
    return await postJson("/predict", lot);
  } catch {
    return demoPrediction(lot);
  }
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
  ].map((link) => ({ ...link, query: `${lot.make} ${lot.model}, ${yearFrom}-${yearTo} г.в.` }));
}

const EXTERNAL_ICON = `<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M6 3H3v10h10v-3M9 3h4v4M13 3 7 9" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

function renderMarketLinks(lot) {
  document.getElementById("market-links").innerHTML = marketLinks(lot).map((link) => `
    <a class="market-card" href="${escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer" aria-label="${link.site}: объявления ${escapeHtml(link.query)}, откроется в новой вкладке">
      <span class="site">${link.site}${EXTERNAL_ICON}</span>
      <span class="query">${escapeHtml(link.query)}</span>
    </a>`).join("");
}

function niceStep(range) {
  const raw = range / 8;
  const power = Math.pow(10, Math.floor(Math.log10(raw)));
  return [1, 2, 5, 10].map((k) => k * power).find((step) => step >= raw);
}

function renderRuler(result, startPrice) {
  const spread = Math.max(result.p75 - result.p25, result.p50 * 0.1);
  let lo = result.p25 - spread * 0.7;
  let hi = result.p75 + spread * 0.7;
  const startOnScale = startPrice && startPrice > lo - spread * 1.5 && startPrice < hi + spread * 1.5;
  if (startOnScale) {
    lo = Math.min(lo, startPrice - spread * 0.2);
    hi = Math.max(hi, startPrice + spread * 0.2);
  }
  lo = Math.max(0, lo);
  const share = (value) => Math.min(100, Math.max(0, ((value - lo) / (hi - lo)) * 100));
  const pos = (value) => `${share(value)}%`;

  const step = niceStep(hi - lo);
  const ticks = [];
  for (let value = Math.ceil(lo / step) * step; value <= hi; value += step) {
    ticks.push(`<span class="tick" style="left:${pos(value)}"></span>`);
  }
  document.getElementById("ruler-ticks").innerHTML = ticks.join("");

  const band = document.getElementById("ruler-band");
  band.style.left = pos(result.p25);
  band.style.width = `${share(result.p75) - share(result.p25)}%`;
  document.getElementById("ruler-median").style.left = pos(result.p50);

  ["p25", "p50", "p75"].forEach((key) => {
    const label = document.getElementById(`ruler-${key}`);
    label.textContent = rubles.format(result[key]);
    label.style.left = pos(result[key]);
  });

  const start = document.getElementById("ruler-start");
  start.classList.toggle("hidden", !startPrice);
  document.getElementById("start-legend").classList.toggle("hidden", !startPrice);
  if (startPrice) {
    start.style.left = pos(startPrice);
    start.classList.toggle("off-scale", !startOnScale);
    let position = "";
    if (!startOnScale) position = startPrice > hi ? ", правее шкалы" : ", левее шкалы";
    document.getElementById("start-value").textContent = rubles.format(startPrice) + position;
  }
}

const FACTOR_KINDS = {
  plus: { sign: "+", word: "повышает цену" },
  minus: { sign: "−", word: "снижает цену" },
  "": { sign: "·", word: "не влияет" },
};

function renderFactor(factor) {
  if (typeof factor === "string") {
    return `<li class="factor"><span class="sign" aria-hidden="true">·</span><span>${escapeHtml(factor)}</span><span></span></li>`;
  }
  let kind = "";
  if (factor.effect > 0) kind = "plus";
  else if (factor.effect < 0) kind = "minus";
  const { sign, word } = FACTOR_KINDS[kind];
  const effect = `${kind ? sign : ""}${wholeNumber.format(Math.abs(factor.effect) * 100)}%`;
  return `<li class="factor ${kind}">
      <span class="sign" aria-hidden="true">${sign}</span>
      <span>${escapeHtml(factor.label)}</span>
      <span class="effect"><span class="sr-only">${word} на </span>${effect}</span>
    </li>`;
}

const dateFormat = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short", year: "numeric" });

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : dateFormat.format(date);
}

function renderComparable(lot) {
  const link = lot.url
    ? `<a href="${escapeHtml(lot.url)}" target="_blank" rel="noopener">карточка</a>`
    : "";
  return `
    <tr>
      <td class="car">${escapeHtml(`${lot.make} ${lot.model}`)}</td>
      <td class="year r">${escapeHtml(lot.year)}</td>
      <td class="date">${escapeHtml(formatDate(lot.sale_date))}</td>
      <td class="price r">${rubles.format(lot.sale_price)}</td>
      <td>${link}</td>
    </tr>`;
}

const ladder = document.getElementById("ladder");
const priceForm = document.getElementById("price-form");
const chosenInput = document.getElementById("chosen-price");
const chosenError = document.getElementById("chosen-error");
const current = { lot: null, result: null, price: null, blind: null, source: null };

function percent(share) {
  return `${Math.round(share * 100)}%`;
}

function percentHtml(share) {
  return `${Math.round(share * 100)}<span class="pct">%</span>`;
}

function renderLadder() {
  ladder.innerHTML = current.result.curve.map((point) => {
    const ownLabel = document.body.dataset.mode === "check" ? "этого лота" : "ваша";
    const tags = (point.typical ? `<span class="tag">обычная</span>` : "") + (point.own ? `<span class="tag own">${ownLabel}</span>` : "");
    return `<li>
      <button type="button" class="rung" data-price="${point.price}" aria-pressed="false">
        <span class="rung-price">${rubles.format(point.price)}${tags}</span>
        <span class="rung-bar" aria-hidden="true"><span class="rung-fill" style="width:${percent(point.p_first)}"></span></span>
        <span class="rung-share">${percentHtml(point.p_first)}<span class="sr-only"> похожих лотов продано на первых торгах</span></span>
      </button>
    </li>`;
  }).join("");
}

function renderSale(sale, price) {
  document.getElementById("p50-big").textContent = rubles.format(sale.p50);
  ["p25", "p50", "p75"].forEach((key) => { document.getElementById(key).textContent = rubles.format(sale[key]); });
  document.getElementById("range-from").textContent = rubles.format(sale.p25);
  document.getElementById("range-to").textContent = rubles.format(sale.p75);
  renderRuler(sale, price);
  const band = document.getElementById("ruler-band");
  band.style.animation = "none";
  void band.offsetWidth;
  band.style.animation = "";
}

const halfMonths = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 });

function monthsRange(days) {
  const months = (value) => Math.max(0.5, Math.round((value / 30.4) * 2) / 2);
  const from = months(days.p25);
  const to = months(days.p75);
  return from === to ? `около ${halfMonths.format(from)} мес.` : `${halfMonths.format(from)}-${halfMonths.format(to)} мес.`;
}

function renderTiming() {
  const timing = catalog.timing_days;
  document.getElementById("time-now").textContent = timing ? `Продажа обычно через ${monthsRange(timing.first_auction)} после публикации` : "";
  document.getElementById("time-later").textContent = timing ? `Продажа обычно через ${monthsRange(timing.later)} после публикации первых торгов` : "";
}

function selectPrice(price) {
  const point = current.result.curve.find((p) => p.price === price);
  current.price = price;
  ladder.querySelectorAll(".rung").forEach((rung) => {
    rung.setAttribute("aria-pressed", String(Number(rung.dataset.price) === price));
  });
  chosenInput.value = wholeNumber.format(price);
  chosenError.textContent = "";
  chosenInput.removeAttribute("aria-invalid");
  document.getElementById("chosen-label").textContent = rubles.format(price);
  document.getElementById("share-now").innerHTML = percentHtml(point.p_first);
  document.getElementById("share-later").innerHTML = percentHtml(1 - point.p_first);
  renderSale(point.sale, price);
}

function defaultPrice(result) {
  const own = result.curve.find((p) => p.own);
  const typical = result.curve.find((p) => p.typical);
  if (own) return own.price;
  if (typical) return typical.price;
  return result.curve[Math.floor(result.curve.length / 2)].price;
}

function renderResult(result, lot) {
  current.lot = lot;
  current.result = result;
  document.getElementById("demo-note").classList.toggle("hidden", !result.demo);
  document.getElementById("typical-p50").textContent = rubles.format(result.typical_start.p50);
  document.getElementById("typical-from").textContent = rubles.format(result.typical_start.p25);
  document.getElementById("typical-to").textContent = rubles.format(result.typical_start.p75);
  document.getElementById("market-from").textContent = rubles.format(result.market.p25);
  document.getElementById("market-to").textContent = rubles.format(result.market.p75);
  document.getElementById("market-p50").textContent = rubles.format(result.market.p50);

  const reliability = document.getElementById("reliability");
  reliability.innerHTML = "<strong>Оценки приблизительные.</strong> Продаж этой модели с близким годом выпуска в истории нет, поэтому модель опирается на машины той же марки и похожего возраста.";
  const abstain = Boolean(result.abstain);
  document.getElementById("s6").textContent = abstain ? "Прогноз не строим" : "Начальная цена";
  reliability.classList.toggle("hidden", !result.low_reliability || abstain);
  const abstainNote = document.getElementById("abstain-note");
  document.getElementById("abstain-reason").textContent = result.abstain ?? "";
  abstainNote.classList.toggle("hidden", !abstain);
  ["forecast-block", "sale-step", "model-basis", "pilot-actions"].forEach((id) => {
    document.getElementById(id).classList.toggle("hidden", abstain);
  });

  document.getElementById("factors").innerHTML = result.factors.map(renderFactor).join("");
  document.getElementById("comparables").innerHTML = result.comparables.length
    ? result.comparables.map(renderComparable).join("")
    : `<tr><td colspan="5" class="empty">Похожих проданных лотов не найдено.</td></tr>`;

  renumberSteps();
  document.getElementById("result").classList.remove("hidden");
  if (abstain) return;
  renderLadder();
  renderTiming();
  resetPilotSave();
  selectPrice(defaultPrice(result));
}

ladder.addEventListener("click", (event) => {
  const rung = event.target.closest(".rung");
  if (rung) selectPrice(Number(rung.dataset.price));
});

chosenInput.addEventListener("input", () => formatPriceInput(chosenInput));

priceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const price = Number(chosenInput.value.replace(/\D/g, "")) || null;
  const message = price ? outOfRange(price, 1000, MAX.first_price, "Цена от 1 000 до 50 000 000 руб.") : "Укажите начальную цену";
  chosenError.textContent = message;
  if (message) {
    chosenInput.setAttribute("aria-invalid", "true");
    chosenInput.focus();
    return;
  }
  if (current.result.curve.some((p) => p.price === price)) {
    selectPrice(price);
    return;
  }
  const button = priceForm.querySelector("button");
  setBusy(button, true);
  const lot = { ...current.lot, first_price: price };
  setNumber("first_price", price);
  const result = await predict(lot);
  setBusy(button, false);
  renderResult(result, lot);
});

const FLAG_NAMES = {
  major_defect: "серьёзная техническая неисправность",
  damaged: "повреждения кузова",
  no_keys_or_docs: "нет ключей или документов",
  location_unknown: "местонахождение неизвестно",
  pledge: "залог",
  arrest_or_ban: "арест или запрет",
};

function lotSummary(lot) {
  const region = catalog.regions.find((r) => r.id === lot.region)?.name;
  const engine = [lot.power_hp && `${wholeNumber.format(lot.power_hp)} л.с.`, lot.engine_cc && `${wholeNumber.format(lot.engine_cc)} куб. см`].filter(Boolean);
  return [`${lot.make} ${lot.model}, ${lot.year} г.в.`, ...engine, region].filter(Boolean).join(", ");
}

function fillPrintHeader() {
  const lot = current.lot;
  const flags = FLAGS.filter((flag) => lot[flag]).map((flag) => FLAG_NAMES[flag]);
  document.getElementById("print-lot").textContent = lotSummary(lot);
  document.getElementById("print-flags").textContent = flags.length ? `Отмечено: ${flags.join(", ")}.` : "Неисправности и обременения не отмечены.";
  const stamp = new Intl.DateTimeFormat("ru-RU", { dateStyle: "long", timeStyle: "short" }).format(new Date());
  document.getElementById("print-meta").textContent = `Расчёт от ${stamp}${current.result.demo ? ", демо-данные" : ""}.`;
}

window.addEventListener("beforeprint", () => {
  if (current.result) fillPrintHeader();
});
document.getElementById("print-btn").addEventListener("click", () => window.print());

const pilotSave = document.getElementById("pilot-save");
const pilotStatus = document.getElementById("pilot-status");
const PILOT_HINT = pilotStatus.textContent;

function resetPilotSave() {
  pilotSave.disabled = false;
  pilotSave.textContent = "Сохранить в журнал";
  pilotStatus.textContent = PILOT_HINT;
  pilotStatus.classList.remove("error");
}

pilotSave.addEventListener("click", async () => {
  const point = current.result.curve.find((p) => p.price === current.price);
  const { demo = false, typical_start: typicalStart, market } = current.result;
  setBusy(pilotSave, true);
  try {
    const record = await postJson("/pilot", {
      lot: current.lot,
      blind_estimate: current.blind,
      chosen_price: current.price,
      trade_url: current.source?.url ?? null,
      forecast: { demo, typical_start: typicalStart, market, chosen: point, curve: current.result.curve },
    });
    pilotSave.textContent = "Сохранено";
    pilotStatus.textContent = `Запись ${record.id}${current.blind ? "" : ", без вашей оценки"}.`;
  } catch {
    pilotSave.disabled = false;
    pilotStatus.textContent = "Журнал недоступен: сайт открыт без сервера.";
    pilotStatus.classList.add("error");
    return;
  } finally {
    pilotSave.setAttribute("aria-busy", "false");
  }
  pilotSave.disabled = true;
});

function setBusy(button, busy) {
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
}

function setStatus(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle("error", isError);
}

description.addEventListener("input", () => { current.source = null; });

function sourceStatus(features) {
  if (!features.source.passenger) {
    return `Лот ${features.source.trade_id} не из категории «Легковой транспорт». Модели обучены только на легковых автомобилях, поэтому оценка будет ненадёжной.`;
  }
  const price = features.first_price
    ? " Начальная цена взята из карточки."
    : " Лот на публичном предложении: начальная цена первого аукциона неизвестна.";
  const next = document.body.dataset.mode === "check"
    ? " Расчёт ниже. Неверное поле можно поправить и нажать «Оценить»."
    : " Проверьте поля.";
  return `Заполнено по карточке лота ${features.source.trade_id} (${features.source.trade_type.toLowerCase()}).${price}${next}`;
}

async function extractInto(text, button, status) {
  setStatus(status, "Распознаём поля...");
  setBusy(button, true);
  try {
    const features = await postJson("/extract", { text });
    current.source = features.source ?? null;
    fillForm(features);
    setStatus(status, features.source ? sourceStatus(features) : "Поля заполнены, проверьте их.",
      Boolean(features.source && !features.source.passenger));
    return features;
  } catch (error) {
    setStatus(status, error.message === "HTTP 502"
      ? "Не удалось загрузить лот с ЦДТ. Проверьте ссылку."
      : "Сервер не отвечает, заполните поля вручную.", true);
    return null;
  } finally {
    setBusy(button, false);
  }
}

const extractStatus = document.getElementById("extract-status");
document.getElementById("extract-btn").addEventListener("click", (event) => {
  if (!description.value.trim()) {
    setStatus(extractStatus, "Сначала вставьте текст описания.", true);
    description.focus();
    return;
  }
  extractInto(description.value, event.currentTarget, extractStatus);
});

const LOT_LINK_RE = /torgi\.cdtrf\.ru\/(?:[\w-]+\/)*trades\/\d+/i;
const lotLink = document.getElementById("lot-link");
const linkStatus = document.getElementById("link-status");

async function loadLink() {
  if (!LOT_LINK_RE.test(lotLink.value)) {
    setStatus(linkStatus, "Вставьте ссылку на карточку лота ЦДТ, например https://torgi.cdtrf.ru/trades/361833", true);
    lotLink.focus();
    return;
  }
  const features = await extractInto(lotLink.value, document.getElementById("link-btn"), linkStatus);
  if (features?.source && validateAll()) form.requestSubmit();
}

document.getElementById("link-btn").addEventListener("click", loadLink);
lotLink.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    loadLink();
  }
});

function renumberSteps() {
  const mode = document.body.dataset.mode;
  const visible = [...document.querySelectorAll("main .step")].filter((step) => !step.matches(mode === "check" ? ".prepare-only" : ".check-only") && !step.matches(".hidden"));
  visible.forEach((step, i) => { step.querySelector(".step-num").textContent = i + 1; });
}

function setMode(mode) {
  document.body.dataset.mode = mode;
  renumberSteps();
  setNumber("first_price", null);
  document.querySelectorAll(".mode-switch [role=tab]").forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.mode === mode));
  });
  document.getElementById("result").classList.add("hidden");
  current.source = null;
  setStatus(extractStatus, "");
  setStatus(linkStatus, "");
}

document.querySelector(".mode-switch").addEventListener("click", (event) => {
  const tab = event.target.closest("[role=tab]");
  if (tab && tab.getAttribute("aria-selected") !== "true") setMode(tab.dataset.mode);
});

const heroVideo = document.getElementById("hero-video");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function playHeroVideo() {
  if (heroVideo.paused) heroVideo.play().catch(() => {});
}

heroVideo.muted = true;
for (const name of ["canplay", "pause", "stalled"]) heroVideo.addEventListener(name, playHeroVideo);
document.addEventListener("visibilitychange", playHeroVideo);
window.addEventListener("pageshow", playHeroVideo);
for (const name of ["pointerdown", "keydown", "scroll", "touchstart"]) window.addEventListener(name, playHeroVideo, { passive: true });
playHeroVideo();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector('button[type="submit"]');
  if (button.disabled || !validateAll()) return;
  const lot = readForm();
  current.blind = document.body.dataset.mode === "prepare" ? readNumber("blind_estimate") : null;
  setBusy(button, true);
  const result = await predict(lot);
  setBusy(button, false);
  renderResult(result, lot);
  renderMarketLinks(lot);
  const section = document.getElementById("result");
  const smooth = !reducedMotion.matches;
  section.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
  section.focus({ preventScroll: true });
});

loadCatalog();
