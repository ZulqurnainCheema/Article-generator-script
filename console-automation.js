(() => {
  /************************************************************
   * SEOwriting.ai 1-Click Blog Post Automation (Console/Userscript)
   * - UI-click only (no hidden input hacks)
   * - CSV-driven + reload-safe
   * - Skips empty CSV fields (keeps defaults)
   ************************************************************/

  /**************** CONFIG ****************/
  const APP = {
    TOOL_URL: "https://app.seowriting.ai/article/1-click-blog-post",
    GENERATION_URL: "https://seowriting.ai/tools/generation",
    RETURN_TO_TOOL_AFTER_RUN: true,
    RETURN_DELAY_MS: 2000,
    RELOAD_IF_NO_NAV: false,
    DAY_MS: 86400000,
    MAX_WAIT_MS: 20 * 60 * 1000,
    STEP_DELAY_MS: 350,
    AFTER_FILL_DELAY_MS: 800,
    DEBUG: true
  };

  // Paste your CSV here:
  const CSV_TEXT = ``;
  // First scheduled date (YYYY-MM-DD):
  const START_DATE_ISO = "2026-02-13";
  // Start from row index (0-based):
  const START_INDEX = 0;

  /**************** UTILS ****************/
  const log = (...a) => APP.DEBUG && console.log(...a);
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  const waitFor = async (fn, timeout = APP.MAX_WAIT_MS, poll = 350) => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try { if (fn()) return true; } catch {}
      await sleep(poll);
    }
    throw new Error("Timeout waiting for condition");
  };

  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => [...root.querySelectorAll(sel)];

  const clickEl = (el) => {
    if (!el) throw new Error("clickEl: element not found");
    el.scrollIntoView({ block: "center" });
    el.click();
  };

  const setInputValue = (el, value) => {
    if (!el) throw new Error("setInputValue: element not found");
    el.scrollIntoView({ block: "center" });
    el.focus();
    el.value = value ?? "";
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const normalize = (s) =>
    (s ?? "")
      .toString()
      .replace(/\u00A0/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();

  const hasValue = (v) => v !== undefined && v !== null && String(v).trim() !== "";

  /**************** CSV ****************/
  function parseCSV(text) {
    const rows = [];
    let row = [];
    let field = "";
    let inQuotes = false;

    const pushField = () => {
      row.push(field);
      field = "";
    };

    const pushRow = () => {
      if (row.length || field) {
        pushField();
        rows.push(row);
        row = [];
      }
    };

    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (inQuotes) {
        if (c === '"') {
          if (text[i + 1] === '"') {
            field += '"';
            i++;
          } else {
            inQuotes = false;
          }
        } else {
          field += c;
        }
      } else {
        if (c === '"') {
          inQuotes = true;
        } else if (c === ',') {
          pushField();
        } else if (c === '\n') {
          pushRow();
        } else if (c === '\r') {
          continue;
        } else {
          field += c;
        }
      }
    }
    pushRow();

    if (!rows.length) return [];
    const headers = rows.shift().map(h => h.trim());
    return rows
      .filter(r => r.some(v => String(v).trim() !== ""))
      .map(r => Object.fromEntries(headers.map((h, i) => [h, (r[i] ?? "").trim()])));
  }

  /**************** SELECT-MENU HANDLER ****************/
  async function openMenu(menu) {
    const btn = qs(".select-btn", menu);
    clickEl(btn);
    await waitFor(() => qs("ul li", menu));
  }

  function getOptionLabel(li) {
    return li.getAttribute("data-text") || li.dataset.text || li.innerText || "";
  }

  async function selectMenuByLabel(menuId, label) {
    if (!hasValue(label)) return;

    const menu = qs(`#${menuId}`);
    if (!menu) throw new Error(`Menu not found: ${menuId}`);

    await openMenu(menu);
    await sleep(APP.STEP_DELAY_MS);

    const searchInput =
      qs('input[type="text"][data-search]', menu) ||
      qs('input[type="text"]', menu);

    if (searchInput && !searchInput.hasAttribute("readonly")) {
      searchInput.focus();
      searchInput.value = "";
      searchInput.dispatchEvent(new Event("input", { bubbles: true }));
      await sleep(150);

      searchInput.value = label;
      searchInput.dispatchEvent(new Event("input", { bubbles: true }));
      await sleep(350);
    }

    const options = qsa("ul li", menu);
    const targetNorm = normalize(label);

    let opt =
      options.find(li => normalize(getOptionLabel(li)) === targetNorm) ||
      options.find(li => normalize(getOptionLabel(li)).includes(targetNorm));

    if (!opt) {
      console.error(`❌ Option not found in ${menuId} for "${label}"`);
      console.error("Available:", options.map(li => getOptionLabel(li)).filter(Boolean));
      throw new Error(`Option "${label}" not found in ${menuId}`);
    }

    clickEl(opt);
    await sleep(APP.STEP_DELAY_MS);
  }

  /**************** PAGE ACTIONS ****************/
  async function ensureToolPage() {
    if (!location.href.includes("/article/1-click-blog-post")) {
      location.href = APP.TOOL_URL;
      await waitFor(() => location.href.includes("/article/1-click-blog-post"), 60000);
    }
    await waitFor(() => qs("#main_keyword"));
  }

  async function clickGenerateTitleAndWait() {
    await waitFor(() => qs("#gen_title"));
    clickEl(qs("#gen_title"));
    await waitFor(() => (qs("#inp_title")?.value || "").trim().length > 2);
  }

  async function clickNlpKeywordsAndWait() {
    await waitFor(() => qs("#gen_keywords"));
    clickEl(qs("#gen_keywords"));
    await waitFor(() => !qs("#gen_keywords")?.disabled);
  }

  async function enableOutlineCheckbox() {
    await waitFor(() => qs("#cc_outline_cb"));
    const cb = qs("#cc_outline_cb");
    if (!cb.checked) cb.click();
    await waitFor(() => qs("#magic_bag") && !qs("#magic_bag").disabled);
  }

  async function clickMagicBagAndWait() {
    await enableOutlineCheckbox();
    clickEl(qs("#magic_bag"));
    await waitFor(() => !normalize(qs("#magic_bag").innerText).includes("generation"));
  }

  function computeNextDateISO(baseISO, offsetDays) {
    const d = new Date(baseISO + "T00:00:00");
    return new Date(d.getTime() + offsetDays * APP.DAY_MS)
      .toISOString()
      .slice(0, 10);
  }

  async function setScheduleDate(dateISO) {
    await waitFor(() => qs('input[name="pc_date"]'));
    setInputValue(qs('input[name="pc_date"]'), dateISO);
  }

  async function clickHookButton(label) {
    if (!hasValue(label)) return;
    const btn = qsa(".tf-hook-btn").find(b => normalize(b.innerText) === normalize(label));
    if (btn) clickEl(btn);
  }

  async function clickRun() {
    await waitFor(() => qs(".tf-btn-run"));
    await sleep(APP.AFTER_FILL_DELAY_MS);
    clickEl(qs(".tf-btn-run"));
  }

  async function afterRunNavigate() {
    const before = location.href;
    let changed = false;
    try {
      await waitFor(() => location.href !== before, 45000);
      changed = true;
    } catch {}

    if (changed && APP.RETURN_TO_TOOL_AFTER_RUN) {
      await sleep(APP.RETURN_DELAY_MS);
      if (!location.href.includes("/article/1-click-blog-post")) {
        location.href = APP.TOOL_URL;
      }
      return;
    }

    if (!changed && APP.RELOAD_IF_NO_NAV) {
      location.reload();
    }
  }

  /**************** ONE ROW RUN ****************/
  async function runRow(row, state) {
    await waitFor(() => qs("#main_keyword"));
    setInputValue(qs("#main_keyword"), row.keyword);
    await clickGenerateTitleAndWait();

    await selectMenuByLabel("sm_lang", row.lang);
    await selectMenuByLabel("sm_type", row.type);
    await selectMenuByLabel("sm_size", row.size);
    await selectMenuByLabel("sm_tone", row.tone);
    await selectMenuByLabel("sm_quality", row.ai_model);
    await selectMenuByLabel("sm_point_view", row.point_view);
    await selectMenuByLabel("sm_readability", row.readability);
    await selectMenuByLabel("sm_target_country", row.target_country);

    try { await selectMenuByLabel("sm_rm_words", row.rm_words); } catch {}

    await selectMenuByLabel("sm_brand_voice", row.brand_voice);
    await selectMenuByLabel("sm_images", row.images);
    await selectMenuByLabel("sm_img_quantity", row.img_quantity);
    await selectMenuByLabel("sm_img_size", row.img_size);

    if (hasValue(row.img_style)) await selectMenuByLabel("sm_img_style", row.img_style);
    if (hasValue(row.img_prompt)) setInputValue(qs("#img_prompt"), row.img_prompt);
    if (hasValue(row.img_brand_name)) setInputValue(qs("#img_brand_name"), row.img_brand_name);

    if (hasValue(row.mk_alt)) {
      const cb = qs("#cc_mk_alt");
      if (cb) {
        const want = normalize(row.mk_alt) === "yes" || normalize(row.mk_alt) === "true";
        if (cb.checked !== want) cb.click();
      }
    }

    await clickNlpKeywordsAndWait();
    await clickHookButton(row.hook_type);
    await clickMagicBagAndWait();

    if (hasValue(row.il_site)) await selectMenuByLabel("sm_il_site", row.il_site);

    if (hasValue(row.web_source_date)) {
      await selectMenuByLabel("sm_web", "Yes");
      await waitFor(() => qs("#sm_web_source_date"), 10000);
      await selectMenuByLabel("sm_web_source_date", row.web_source_date);
    }

    if (hasValue(row.pc_site)) await selectMenuByLabel("sm_pc_site_id", row.pc_site);

    if (hasValue(row.pc_status)) {
      await waitFor(() => qs("#sm_pc_status"), 10000);
      await selectMenuByLabel("sm_pc_status", row.pc_status);
    }

    const shouldSchedule = !hasValue(row.pc_status) || normalize(row.pc_status) === "schedule";
    if (shouldSchedule) {
      const dateISO = computeNextDateISO(state.startDateISO, state.index);
      await setScheduleDate(dateISO);
    }

    await clickRun();
  }

  /**************** RUNNER ****************/
  async function runFrom(index = START_INDEX) {
    const rows = parseCSV(CSV_TEXT);
    if (!rows.length) {
      throw new Error("CSV_TEXT is empty. Paste your CSV into CSV_TEXT.");
    }
    if (!START_DATE_ISO) {
      throw new Error("START_DATE_ISO is required (YYYY-MM-DD).");
    }

    for (let i = index; i < rows.length; i++) {
      await ensureToolPage();
      await runRow(rows[i], { startDateISO: START_DATE_ISO, index: i });
      await afterRunNavigate();
    }
    console.log("✅ All rows completed");
  }

  // expose helper
  window.seoRun = runFrom;
  console.log("Ready: call seoRun() or seoRun(startIndex)");
})();
