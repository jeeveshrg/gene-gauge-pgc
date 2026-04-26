/* GeneGauge calculator - small, defensive, no dependencies.
 *
 * We intentionally keep the DOM updates simple and always go through
 * textContent (never innerHTML) so user-facing labels from the server
 * cannot be interpreted as markup.
 */

(function () {
  "use strict";

  const form = document.getElementById("score-form");
  if (!form) return;

  const resultEl = document.getElementById("result");
  const emptyEl = document.getElementById("empty-state");
  const scoreValueEl = document.getElementById("score-value");
  const scoreBandEl = document.getElementById("score-band");
  const compareTextEl = document.getElementById("compare-text");
  const compareFillEl = document.getElementById("compare-fill");
  const compareMarkerEl = document.getElementById("compare-marker");
  const topUpEl = document.getElementById("top-up");
  const topDownEl = document.getElementById("top-down");
  const detailsBodyEl = document.getElementById("details-body");
  const errorBanner = document.getElementById("error-banner");
  const errorText = document.getElementById("error-text");

  function showError(message) {
    errorText.textContent = message;
    errorBanner.hidden = false;
  }
  function clearError() {
    errorBanner.hidden = true;
    errorText.textContent = "";
  }

  function readValues() {
    const out = {};
    const rows = form.querySelectorAll(".signal-row");
    rows.forEach(function (row) {
      const sid = row.getAttribute("data-signal-id");
      const checked = row.querySelector("input[type=radio]:checked");
      if (sid && checked) {
        // Normalize to integer. The server also validates.
        const v = parseInt(checked.value, 10);
        if (v === 0 || v === 1 || v === 2) {
          out[sid] = v;
        }
      }
    });
    return out;
  }

  function setValues(values) {
    const rows = form.querySelectorAll(".signal-row");
    rows.forEach(function (row) {
      const sid = row.getAttribute("data-signal-id");
      const v = values[sid];
      if (v === 0 || v === 1 || v === 2) {
        const input = row.querySelector(
          'input[type=radio][value="' + String(v) + '"]'
        );
        if (input) input.checked = true;
      }
    });
  }

  function resetValues() {
    const rows = form.querySelectorAll(".signal-row");
    rows.forEach(function (row) {
      const zero = row.querySelector('input[type=radio][value="0"]');
      if (zero) zero.checked = true;
    });
  }

  function bandLabel(band) {
    switch (band) {
      case "low": return "Lower than most";
      case "elevated": return "Higher than most";
      case "typical":
      default: return "Typical range";
    }
  }

  function plainPercentile(pct) {
    const rounded = Math.round(pct);
    if (rounded <= 1) return "Your score is lower than about 99 out of 100 sample people.";
    if (rounded >= 99) return "Your score is higher than about 99 out of 100 sample people.";
    return "Your score is higher than about " + rounded + " out of 100 sample people.";
  }

  function fmtSigned(n) {
    const v = Math.round(n * 100) / 100;
    return (v >= 0 ? "+" : "") + v.toFixed(2);
  }

  function renderReasons(listEl, items, direction) {
    listEl.textContent = "";
    if (!items || items.length === 0) {
      const li = document.createElement("li");
      li.className = "reason-chip";
      const label = document.createElement("span");
      label.className = "reason-label";
      label.textContent = "No strong reasons here.";
      li.appendChild(label);
      listEl.appendChild(li);
      return;
    }
    items.forEach(function (c) {
      const li = document.createElement("li");
      li.className = "reason-chip " + (direction === "up" ? "is-up" : "is-down");
      const label = document.createElement("span");
      label.className = "reason-label";
      label.textContent = c.plain_label;
      const value = document.createElement("span");
      value.className = "reason-value";
      value.textContent = fmtSigned(c.contribution);
      li.appendChild(label);
      li.appendChild(value);
      listEl.appendChild(li);
    });
  }

  function renderDetails(contribs) {
    detailsBodyEl.textContent = "";
    contribs.forEach(function (c) {
      const tr = document.createElement("tr");
      const tdLabel = document.createElement("td");
      tdLabel.textContent = c.plain_label;
      const tdValue = document.createElement("td");
      tdValue.textContent = String(c.value);
      const tdWeight = document.createElement("td");
      tdWeight.textContent = fmtSigned(c.weight);
      const tdContrib = document.createElement("td");
      tdContrib.textContent = fmtSigned(c.contribution);
      tr.appendChild(tdLabel);
      tr.appendChild(tdValue);
      tr.appendChild(tdWeight);
      tr.appendChild(tdContrib);
      detailsBodyEl.appendChild(tr);
    });
  }

  function renderResult(data) {
    emptyEl.hidden = true;
    resultEl.hidden = false;
    scoreValueEl.textContent = (Math.round(data.score * 100) / 100).toFixed(2);
    scoreBandEl.textContent = bandLabel(data.band);
    scoreBandEl.classList.remove("band-low", "band-typical", "band-elevated");
    scoreBandEl.classList.add("band-" + data.band);
    compareTextEl.textContent = plainPercentile(data.percentile);
    const pct = Math.max(0, Math.min(100, data.percentile));
    compareFillEl.style.width = pct + "%";
    compareMarkerEl.style.left = pct + "%";
    renderReasons(topUpEl, data.top_up, "up");
    renderReasons(topDownEl, data.top_down, "down");
    renderDetails(data.contributions);
  }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!res.ok) {
      let msg = "Something went wrong. Please try again.";
      try {
        const data = await res.json();
        if (data && typeof data.detail === "string") msg = data.detail;
      } catch (_e) { /* ignore */ }
      throw new Error(msg);
    }
    return res.json();
  }

  async function getJSON(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { "Accept": "application/json" },
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!res.ok) throw new Error("Request failed.");
    return res.json();
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    clearError();
    try {
      const values = readValues();
      const data = await postJSON("/api/score", { values: values });
      renderResult(data);
    } catch (err) {
      showError(err.message || "Something went wrong.");
    }
  });

  const demoBtn = document.getElementById("load-demo");
  if (demoBtn) {
    demoBtn.addEventListener("click", async function () {
      clearError();
      try {
        const data = await getJSON("/api/demo");
        setValues(data.values || {});
      } catch (err) {
        showError("Could not load a demo person. Please try again.");
      }
    });
  }

  const resetBtn = document.getElementById("reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      clearError();
      resetValues();
      resultEl.hidden = true;
      emptyEl.hidden = false;
    });
  }
})();
