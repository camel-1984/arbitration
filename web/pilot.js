const rubles = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });
const wholeNumber = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
const dateFormat = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short", year: "numeric" });
const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const list = document.getElementById("pilot-list");
let entries = [];

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
}

function money(value) {
  return value ? rubles.format(value) : "не указана";
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function atPrice(forecast, price) {
  const curve = forecast.curve ?? [forecast.chosen];
  if (!price || curve.length === 1) return forecast.chosen;
  const exact = curve.find((p) => p.price === price);
  if (exact) return exact;
  const upper = curve.findIndex((p) => p.price > price);
  if (upper <= 0) return curve[upper === 0 ? 0 : curve.length - 1];
  const a = curve[upper - 1];
  const b = curve[upper];
  const w = (Math.log(price) - Math.log(a.price)) / (Math.log(b.price) - Math.log(a.price));
  const mix = (x, y) => Math.exp((1 - w) * Math.log(x) + w * Math.log(y));
  return {
    price,
    p_first: (1 - w) * a.p_first + w * b.p_first,
    sale: { p25: mix(a.sale.p25, b.sale.p25), p50: mix(a.sale.p50, b.sale.p50), p75: mix(a.sale.p75, b.sale.p75) },
  };
}

function forecastFor(entry) {
  return atPrice(entry.forecast, entry.outcome.actual_start_price ?? entry.chosen_price);
}

function percentHtml(share) {
  return `${Math.round(share * 100)}<span class="pct">%</span>`;
}

function lotsWord(n) {
  return n % 10 === 1 && n % 100 !== 11 ? "лоту" : "лотам";
}

function setShare(id, share, noteId, note) {
  document.getElementById(id).innerHTML = share === null ? "-" : percentHtml(share);
  if (noteId) document.getElementById(noteId).textContent = note;
}

function renderSummary() {
  const sold = entries.filter((e) => e.outcome.sale_price);
  const withBlind = sold.filter((e) => e.blind_estimate);
  const error = (estimate, price) => Math.abs(estimate - price) / price;
  setShare("err-manager", withBlind.length ? median(withBlind.map((e) => error(e.blind_estimate, e.outcome.sale_price))) : null,
    "err-manager-note", `По ${withBlind.length} ${lotsWord(withBlind.length)} с вашей оценкой и ценой продажи.`);
  setShare("err-model", sold.length ? median(sold.map((e) => error(forecastFor(e).sale.p50, e.outcome.sale_price))) : null,
    "err-model-note", `По ${sold.length} ${lotsWord(sold.length)}: медиана прогноза при фактической начальной цене (если указана).`);
  const known = entries.filter((e) => e.outcome.sold_first !== null);
  const mean = (values) => values.reduce((a, b) => a + b, 0) / values.length;
  setShare("first-predicted", known.length ? mean(known.map((e) => forecastFor(e).p_first)) : null);
  setShare("first-observed", known.length ? mean(known.map((e) => (e.outcome.sold_first ? 1 : 0))) : null,
    "first-observed-note", `По ${known.length} ${lotsWord(known.length)} с известным исходом первых торгов.`);
}

function soldFirstValue(value) {
  if (value === true) return "yes";
  if (value === false) return "no";
  return "";
}

function renderEntry(entry) {
  const { lot, forecast, outcome } = entry;
  const chosen = forecast.chosen;
  const demo = forecast.demo ? `<span class="tag">демо</span>` : "";
  const link = entry.trade_url ? ` <a href="${escapeHtml(entry.trade_url)}" target="_blank" rel="noopener noreferrer">лот на ЦДТ</a>` : "";
  const price = (value) => (value ? wholeNumber.format(value) : "");
  return `<li class="pilot-entry" data-id="${escapeHtml(entry.id)}">
    <div class="pilot-head">
      <p class="pilot-car">${escapeHtml(`${lot.make} ${lot.model}, ${lot.year}`)} ${demo}${link}</p>
      <p class="pilot-date">${escapeHtml(dateFormat.format(new Date(entry.created_at)))}</p>
    </div>
    <dl class="pilot-facts">
      <div><dt>Ваша оценка</dt><dd>${money(entry.blind_estimate)}</dd></div>
      <div><dt>Начальная цена</dt><dd>${money(entry.chosen_price)}</dd></div>
      <div><dt>Прогноз продажи</dt><dd>${money(chosen.sale.p50)}</dd></div>
      <div><dt>Шанс продажи сразу</dt><dd>${percentHtml(chosen.p_first)}</dd></div>
    </dl>
    <details class="pilot-more"${outcome.sale_price || outcome.note || outcome.sold_first !== null ? " open" : ""}>
      <summary>${entry.trade_url ? "" : "Ссылка на лот, "}${entry.trade_url ? "Исход" : "исход"} и комментарий <span class="optional">необязательно</span></summary>
      <form class="pilot-outcome" novalidate>
      <label class="field note-field"><span class="field-name">Ссылка на лот ЦДТ</span>
        <input name="trade_url" maxlength="300" placeholder="когда выставите лот: https://torgi.cdtrf.ru/trades/..." autocomplete="off" value="${escapeHtml(entry.trade_url ?? "")}">
      </label>
      <label class="field"><span class="field-name">Фактическая начальная цена, руб.</span>
        <input name="actual_start_price" class="num" inputmode="numeric" maxlength="11" placeholder="${price(entry.chosen_price)}" autocomplete="off" value="${price(outcome.actual_start_price)}">
      </label>
      <label class="field"><span class="field-name">Продан на первых торгах</span>
        <select name="sold_first">
          <option value="">пока не известно</option>
          <option value="yes">да</option>
          <option value="no">нет</option>
        </select>
      </label>
      <label class="field"><span class="field-name">Цена продажи, руб.</span>
        <input name="sale_price" class="num" inputmode="numeric" maxlength="11" placeholder="не продан" autocomplete="off" value="${price(outcome.sale_price)}">
      </label>
      <label class="field"><span class="field-name">Дата продажи</span>
        <input name="sale_date" type="date" min="2020-01-01" max="${new Date().toISOString().slice(0, 10)}" value="${escapeHtml(outcome.sale_date ?? "")}">
      </label>
      <label class="field note-field"><span class="field-name">Комментарий</span>
        <textarea name="note" rows="2" maxlength="2000" placeholder="почему отступили от прогноза, в каком состоянии автомобиль был на самом деле">${escapeHtml(outcome.note ?? "")}</textarea>
      </label>
      <button type="submit" class="secondary">Сохранить исход</button>
      <p class="status" role="status"></p>
    </form>
    </details>
  </li>`;
}

function render() {
  document.getElementById("pilot-empty").classList.toggle("hidden", entries.length > 0);
  list.innerHTML = [...entries].reverse().map(renderEntry).join("");
  list.querySelectorAll(".pilot-entry").forEach((item) => {
    const entry = entries.find((e) => e.id === item.dataset.id);
    item.querySelector("select").value = soldFirstValue(entry.outcome.sold_first);
  });
  renderSummary();
}

list.addEventListener("input", (event) => {
  if (!["sale_price", "actual_start_price"].includes(event.target.name)) return;
  const digits = event.target.value.replace(/\D/g, "");
  event.target.value = digits ? wholeNumber.format(Number(digits)) : "";
});

const LOT_LINK_RE = /torgi\.cdtrf\.ru\/(?:[\w-]+\/)*trades\/\d{1,9}(?!\d)/i;

function outcomeError(formEl) {
  const price = (name) => Number(formEl.elements[name].value.replace(/\D/g, "")) || null;
  for (const name of ["actual_start_price", "sale_price"]) {
    const value = price(name);
    if (value !== null && (value < 1000 || value > 50_000_000)) return "Цена должна быть от 1 000 до 50 000 000 руб.";
  }
  const link = formEl.elements.trade_url.value.trim();
  if (link && !LOT_LINK_RE.test(link)) return "Нужна ссылка на карточку лота вида https://torgi.cdtrf.ru/trades/361833";
  const day = formEl.elements.sale_date.value;
  if (day && (day < "2020-01-01" || day > new Date().toISOString().slice(0, 10))) return "Дата продажи не может быть в будущем";
  return "";
}

list.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formEl = event.target;
  const problem = outcomeError(formEl);
  if (problem) {
    const box = formEl.querySelector(".status");
    box.textContent = problem;
    box.classList.add("error");
    return;
  }
  const id = formEl.closest(".pilot-entry").dataset.id;
  const status = formEl.querySelector(".status");
  const soldFirst = { yes: true, no: false }[formEl.elements.sold_first.value] ?? null;
  const number = (name) => Number(formEl.elements[name].value.replace(/\D/g, "")) || null;
  try {
    const response = await fetch(`/api/pilot/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        trade_url: formEl.elements.trade_url.value.trim() || null,
        actual_start_price: number("actual_start_price"),
        sold_first: soldFirst,
        sale_price: number("sale_price"),
        sale_date: formEl.elements.sale_date.value || null,
        note: formEl.elements.note.value.trim() || null,
      }),
    });
    if (response.status === 422) throw new Error("Проверьте поля: сервер не принял значения.");
    if (!response.ok) throw new Error("Не удалось сохранить.");
    const record = await response.json();
    entries = entries.map((e) => (e.id === id ? record : e));
    renderSummary();
    const car = formEl.closest(".pilot-entry").querySelector(".pilot-car");
    if (record.trade_url && !car.querySelector("a")) {
      car.insertAdjacentHTML("beforeend", ` <a href="${escapeHtml(record.trade_url)}" target="_blank" rel="noopener noreferrer">лот на ЦДТ</a>`);
    }
    status.textContent = "Сохранено.";
    status.classList.remove("error");
  } catch (error) {
    status.textContent = error.message.startsWith("Проверьте") ? error.message : "Не удалось сохранить.";
    status.classList.add("error");
  }
});

document.getElementById("export-btn").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(entries, null, 1)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `pilot-journal-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
});

async function load() {
  try {
    const response = await fetch("/api/pilot");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    entries = await response.json();
  } catch {
    document.getElementById("pilot-error").classList.remove("hidden");
    entries = [];
  }
  render();
}

load();
