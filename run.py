#!/usr/bin/env python3
import csv
import json
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = "config.json"
HTML_FORM_FLOW = [
    ("required_input", "#main_keyword"),
    ("click", "#gen_title"),
    ("select", "#sm_lang"),
    ("select", "#sm_type"),
    ("select", "#sm_size"),
    ("select", "#sm_tone"),
    ("select", "#sm_quality"),
    ("select", "#sm_point_view"),
    ("select", "#sm_readability"),
    ("select", "#sm_target_country"),
    ("select", "#sm_rm_words"),
    ("select", "#sm_brand_voice"),
    ("input", "#tf_details"),
    ("select", "#sm_images"),
    ("select", "#sm_img_quantity"),
    ("select", "#sm_img_size"),
    ("select", "#sm_img_style"),
    ("input", "#img_prompt"),
    ("input", "#img_brand_name"),
    ("checkbox", "#cc_mk_alt"),
    ("checkbox", "#cc_img_alt_text"),
    ("select", "#sm_youtube"),
    ("select", "#sm_video_quantity"),
    ("select", "#sm_placing_scheme"),
    ("click", ".tfk-erase-btn"),
    ("click", "#gen_keywords"),
    ("click", "button.tf-hook-btn"),
    ("select", "#sm_il_site"),
    ("select", "#sm_web"),
    ("wait", "#sm_web_source_date"),
    ("select_after", "#sm_web_source_date"),
    ("checkbox", "#cc_outline_cb"),
    ("click", "#magic_bag"),
    ("select", "#sm_pc_site_id"),
    ("wait", "#sm_pc_status"),
    ("select", "#sm_pc_status"),
    ("date", "input[name='pc_date']"),
    ("click", "button.tf-btn-run"),
]


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_path(path_value: str) -> Path:
    p = Path(path_value).expanduser()
    if not p.is_absolute():
        p = (BASE_DIR / p).resolve()
    return p


def read_csv(csv_cfg: Dict[str, Any]) -> List[Dict[str, str]]:
    csv_path = resolve_path(csv_cfg["path"])
    delimiter = csv_cfg.get("delimiter", ",")
    encoding = csv_cfg.get("encoding", "utf-8")
    with csv_path.open("r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = [
            {str(k or "").strip(): str(v or "").strip() for k, v in row.items()}  # type: ignore
            for row in reader
        ]
    return rows


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_delay_range(value: Any) -> Optional[tuple[float, float]]:
    if value is None:
        return None
    if isinstance(value, dict):
        try:
            return float(value.get("min", 0)), float(value.get("max", 0))
        except (TypeError, ValueError):
            return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
    return None


def random_sleep(delay_cfg: Optional[Dict[str, Any]], key: str) -> None:
    if not delay_cfg:
        return
    rng = parse_delay_range(delay_cfg.get(key))
    if not rng:
        return
    low, high = rng
    if high <= 0:
        return
    if low < 0:
        low = 0
    if high < low:
        low, high = high, low
    time.sleep(random.uniform(low, high) / 1000.0)


def prompt_start_date(default_date: Optional[str]) -> str:
    prompt = "Enter starting schedule date (YYYY-MM-DD)"
    if default_date:
        prompt += f" [default: {default_date}]"
    prompt += ": "
    while True:
        value = input(prompt).strip()
        if not value and default_date:
            return default_date
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            log("Invalid date. Use YYYY-MM-DD.")


def normalize_select_value(sel_value: Any) -> Dict[str, Optional[str]]:
    if isinstance(sel_value, dict):
        return {
            "text": sel_value.get("text"),
            "value": sel_value.get("value"),
            "search": sel_value.get("search"),
            "force": sel_value.get("force"),
            "has_value": "value" in sel_value,
        }
    if isinstance(sel_value, str):
        return {
            "text": sel_value,
            "value": None,
            "search": None,
            "force": None,
            "has_value": False,
        }
    return {
        "text": None,
        "value": None,
        "search": None,
        "force": None,
        "has_value": False,
    }


def open_select_menu(page, menu_selector: str, force: bool) -> None:
    menu = page.locator(menu_selector)
    menu.scroll_into_view_if_needed()
    menu.locator(".select-btn").click(force=force)


def select_menu_option(page, menu_selector: str, sel_value: Any, timeout_ms: int) -> None:
    sel = normalize_select_value(sel_value)
    has_value = bool(sel.get("has_value"))
    if sel["text"] is None and not has_value:
        return
    force = bool(sel.get("force"))

    menu = page.locator(menu_selector)
    try:
        menu.wait_for(state="visible", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        if not force:
            log(f"  Skip {menu_selector}: not visible")
            return

    class_attr = menu.get_attribute("class") or ""
    if "disabled" in class_attr and not force:
        log(f"  Skip {menu_selector}: disabled")
        return
    open_select_menu(page, menu_selector, force)

    # If a searchable input exists, use it to filter options.
    if sel["search"] or sel["text"]:
        search_input = menu.locator("input[data-search]")
        if search_input.count() > 0:
            search_input.fill(sel["search"] or sel["text"] or "")

    if sel["value"] is not None:
        option = menu.locator(f"ul li[data-value=\"{sel['value']}\"]")
    else:
        option = menu.locator("ul li", has_text=sel["text"])  # type: ignore

    if not force:
        option.first.wait_for(state="visible", timeout=timeout_ms)
        option.first.click()
    else:
        option.first.click(force=True)


def fill_input(page, selector: str, value: str, timeout_ms: int) -> None:
    if value is None:
        return
    locator = page.locator(selector)
    locator.scroll_into_view_if_needed()
    locator.wait_for(state="visible", timeout=timeout_ms)
    locator.fill("")
    locator.fill(value)


def set_checkbox(page, selector: str, checked: bool, timeout_ms: int) -> None:
    locator = page.locator(selector)
    locator.scroll_into_view_if_needed()
    locator.wait_for(state="visible", timeout=timeout_ms)
    locator.set_checked(checked, force=True)


def add_keywords(page, input_selector: str, keywords: str, delimiter: str, timeout_ms: int) -> None:
    if not keywords:
        return
    items = [k.strip() for k in keywords.split(delimiter) if k.strip()]
    if not items:
        return
    input_box = page.locator(input_selector)
    input_box.scroll_into_view_if_needed()
    input_box.wait_for(state="visible", timeout=timeout_ms)
    for kw in items:
        input_box.fill(kw)
        page.keyboard.press("Enter")


def is_empty(value: Optional[str]) -> bool:
    return value is None or str(value).strip() == ""


def parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    val = str(value).strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    return None


def resolve_csv_value(
    row: Dict[str, str], column: Optional[str], map_dict: Optional[Dict[str, Any]]
) -> Optional[str]:
    if not column:
        return None
    raw = row.get(column, "")
    if is_empty(raw):
        return None
    value = raw
    if map_dict:
        if value in map_dict:
            value = map_dict[value]
        else:
            value_lower = str(value).lower()
            for k, v in map_dict.items():
                if str(k).lower() == value_lower:
                    value = v
                    break
    return str(value)


def build_select_from_csv(sel_cfg: Any, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    if isinstance(sel_cfg, str):
        column = sel_cfg
        match = "text"
        force = False
        search = None
        map_dict = None
    else:
        column = sel_cfg.get("column")
        match = sel_cfg.get("match", "text")
        force = bool(sel_cfg.get("force", False))
        search = sel_cfg.get("search")
        map_dict = sel_cfg.get("map")

    value = resolve_csv_value(row, column, map_dict)
    if value is None:
        return None

    sel_value: Dict[str, Any] = {"text": value} if match == "text" else {"value": value}
    if force:
        sel_value["force"] = True
    if isinstance(search, bool) and search:
        sel_value["search"] = value
    elif isinstance(search, str):
        sel_value["search"] = search
    return sel_value


def iter_effective_selects(
    static_cfg: Dict[str, Any], csv_cfg: Dict[str, Any], row: Dict[str, str]
):
    seen: set[str] = set()
    for selector, sel_value in static_cfg.items():
        seen.add(selector)
        csv_sel_cfg = csv_cfg.get(selector)
        if csv_sel_cfg is not None:
            csv_value = build_select_from_csv(csv_sel_cfg, row)
            if csv_value is not None:
                yield selector, csv_value
                continue
        yield selector, sel_value

    for selector, sel_cfg in csv_cfg.items():
        if selector in seen:
            continue
        csv_value = build_select_from_csv(sel_cfg, row)
        if csv_value is not None:
            yield selector, csv_value


def iter_required_csv_inputs(inputs_cfg: Dict[str, str], row: Dict[str, str]):
    for selector, column in inputs_cfg.items():
        value = row.get(column, "")
        if is_empty(value):
            raise ValueError(f"Missing required CSV value for column '{column}'")
        yield selector, value, f"{column} -> {value}"


def iter_optional_and_static_inputs(step: Dict[str, Any], row: Dict[str, str]):
    optional_cfg = step.get("inputs_from_csv", {})
    static_cfg = step.get("inputs_static", {})
    processed: set[str] = set()

    for selector in optional_cfg:
        if selector in processed:
            continue
        column = optional_cfg[selector]
        value = row.get(column, "")
        if not is_empty(value):
            processed.add(selector)
            yield selector, value, f"{column} -> {value}"
            continue
        if selector in static_cfg:
            processed.add(selector)
            yield selector, static_cfg[selector], "[static]"

    for selector, value in static_cfg.items():
        if selector in processed or selector in optional_cfg:
            continue
        yield selector, value, "[static]"


def iter_effective_checkboxes(
    static_cfg: Dict[str, Any], csv_cfg: Dict[str, str], row: Dict[str, str]
):
    seen: set[str] = set()
    for selector, checked in static_cfg.items():
        seen.add(selector)
        column = csv_cfg.get(selector)
        if column:
            parsed = parse_bool(row.get(column, ""))
            if parsed is not None:
                yield selector, parsed, f"{column} -> {parsed}"
                continue
        yield selector, bool(checked), str(bool(checked))

    for selector, column in csv_cfg.items():
        if selector in seen:
            continue
        parsed = parse_bool(row.get(column, ""))
        if parsed is not None:
            yield selector, parsed, f"{column} -> {parsed}"


def get_effective_select_value(
    step: Dict[str, Any], selector: str, row: Dict[str, str], after: bool = False
) -> Optional[Any]:
    static_key = "selects_after" if after else "selects"
    csv_key = "selects_from_csv_after" if after else "selects_from_csv"
    static_cfg = step.get(static_key, {})
    csv_cfg = step.get(csv_key, {})

    if selector in csv_cfg:
        csv_value = build_select_from_csv(csv_cfg[selector], row)
        if csv_value is not None:
            return csv_value

    return static_cfg.get(selector)


def get_required_input_value(
    step: Dict[str, Any], selector: str, row: Dict[str, str]
) -> Optional[tuple[str, str]]:
    column = step.get("inputs_from_csv_required", {}).get(selector)
    if not column:
        return None
    value = row.get(column, "")
    if is_empty(value):
        raise ValueError(f"Missing required CSV value for column '{column}'")
    return value, f"{column} -> {value}"


def get_optional_input_value(
    step: Dict[str, Any], selector: str, row: Dict[str, str]
) -> Optional[tuple[str, str]]:
    optional_cfg = step.get("inputs_from_csv", {})
    static_cfg = step.get("inputs_static", {})

    if selector in optional_cfg:
        column = optional_cfg[selector]
        value = row.get(column, "")
        if not is_empty(value):
            return value, f"{column} -> {value}"

    if selector in static_cfg:
        return static_cfg[selector], "[static]"

    return None


def get_effective_checkbox_value(
    step: Dict[str, Any], selector: str, row: Dict[str, str]
) -> Optional[tuple[bool, str]]:
    csv_cfg = step.get("checkboxes_from_csv", {})
    static_cfg = step.get("checkboxes", {})

    if selector in csv_cfg:
        column = csv_cfg[selector]
        parsed = parse_bool(row.get(column, ""))
        if parsed is not None:
            return parsed, f"{column} -> {parsed}"

    if selector in static_cfg:
        checked = bool(static_cfg[selector])
        return checked, str(checked)

    return None


def wait_for_input_value(page, selector: str, min_length: int, timeout_ms: int) -> None:
    page.wait_for_function(
        """({selector, minLength}) => {
            const el = document.querySelector(selector);
            return !!el && typeof el.value === "string" && el.value.length >= minLength;
        }""",
        arg={"selector": selector, "minLength": min_length},
        timeout=timeout_ms,
    )


def wait_for_enabled(page, selector: str, timeout_ms: int) -> None:
    page.wait_for_function(
        """(selector) => {
            const el = document.querySelector(selector);
            return !!el && !el.disabled;
        }""",
        arg=selector,
        timeout=timeout_ms,
    )


def wait_for_url_change(page, timeout_ms: int) -> bool:
    current = page.url
    try:
        page.wait_for_function(
            """(url) => window.location.href !== url""",
            arg=current,
            timeout=timeout_ms,
        )
        return True
    except PlaywrightTimeoutError:
        return False


def wait_for_button_state(
    page, selector: str, disabled: bool, timeout_ms: int
) -> None:
    page.wait_for_function(
        """({sel, disabled}) => {
            const el = document.querySelector(sel);
            if (!el) return false;
            const cls = (el.className || "").toString().toLowerCase();
            const isDisabled =
                !!el.disabled ||
                el.getAttribute("disabled") !== null ||
                cls.includes("disabled") ||
                cls.includes("loading") ||
                el.getAttribute("aria-busy") === "true";
            return disabled ? isDisabled : !isDisabled;
        }""",
        arg={"sel": selector, "disabled": disabled},
        timeout=timeout_ms,
    )


def click_item(page, click_cfg: Any, timeout_ms: int) -> None:
    if isinstance(click_cfg, str):
        log(f"  Click {click_cfg}")
        page.locator(click_cfg).scroll_into_view_if_needed()
        page.click(click_cfg)
        return

    if not isinstance(click_cfg, dict):
        return

    selector = click_cfg.get("selector")
    if not selector:
        return

    text = click_cfg.get("text")
    force = bool(click_cfg.get("force", False))
    locator = page.locator(selector, has_text=text) if text else page.locator(selector)
    log(f"  Click {selector}" + (f" (text={text})" if text else ""))
    wait_enabled_before = click_cfg.get("wait_for_enabled_before")
    if wait_enabled_before:
        wait_for_enabled(
            page,
            wait_enabled_before["selector"],
            int(wait_enabled_before.get("timeout_ms", timeout_ms)),
        )

    wait_button_enabled_before = click_cfg.get("wait_for_button_enabled_before")
    if wait_button_enabled_before:
        wait_for_button_state(
            page,
            wait_button_enabled_before["selector"],
            False,
            int(wait_button_enabled_before.get("timeout_ms", timeout_ms)),
        )
    wait_sel_before = click_cfg.get("wait_for_selector_before")
    if wait_sel_before:
        page.wait_for_selector(
            wait_sel_before["selector"],
            state=wait_sel_before.get("state", "visible"),
            timeout=int(wait_sel_before.get("timeout_ms", timeout_ms)),
        )
    locator.scroll_into_view_if_needed()
    locator.click(force=force)

    wait_button_enabled_after = click_cfg.get("wait_for_button_enabled_after")
    if wait_button_enabled_after:
        wait_for_button_state(
            page,
            wait_button_enabled_after["selector"],
            False,
            int(wait_button_enabled_after.get("timeout_ms", timeout_ms)),
        )

    wait_input = click_cfg.get("wait_for_input_value")
    if wait_input:
        wait_for_input_value(
            page,
            wait_input["selector"],
            int(wait_input.get("min_length", 1)),
            int(wait_input.get("timeout_ms", timeout_ms)),
        )

    wait_sel = click_cfg.get("wait_for_selector")
    if wait_sel:
        page.wait_for_selector(
            wait_sel["selector"],
            state=wait_sel.get("state", "visible"),
            timeout=int(wait_sel.get("timeout_ms", timeout_ms)),
        )

    wait_enabled = click_cfg.get("wait_for_enabled")
    if wait_enabled:
        wait_for_enabled(
            page,
            wait_enabled["selector"],
            int(wait_enabled.get("timeout_ms", timeout_ms)),
        )

    wait_disabled = click_cfg.get("wait_for_button_disabled")
    if wait_disabled:
        selector = wait_disabled["selector"]
        timeout = int(wait_disabled.get("timeout_ms", timeout_ms))
        retry_click = bool(wait_disabled.get("retry_click", False))
        try:
            wait_for_button_state(page, selector, True, timeout)
        except PlaywrightTimeoutError:
            if retry_click:
                log(f"  Retry click {selector}")
                locator.click(force=True)
                try:
                    wait_for_button_state(page, selector, True, timeout)
                except PlaywrightTimeoutError:
                    log(f"  Warning: {selector} did not become disabled.")

    wait_nav = click_cfg.get("wait_for_url_change")
    if wait_nav:
        changed = wait_for_url_change(
            page, int(wait_nav.get("timeout_ms", timeout_ms))
        )
        if changed:
            return_url = wait_nav.get("return_url")
            return_delay = int(wait_nav.get("return_delay_ms", 0))
            if return_delay:
                time.sleep(return_delay / 1000.0)
            if return_url:
                page.goto(return_url, wait_until="domcontentloaded")
        else:
            if wait_nav.get("reload_if_no_nav"):
                page.reload(wait_until="domcontentloaded")

    sleep_ms = click_cfg.get("sleep_ms")
    if sleep_ms:
        time.sleep(float(sleep_ms) / 1000.0)


def resolve_click_cfg(click_cfg: Any, row: Dict[str, str]) -> Optional[Any]:
    if not isinstance(click_cfg, dict):
        return click_cfg

    if "column" in click_cfg or "text_from_csv" in click_cfg:
        column = click_cfg.get("column") or click_cfg.get("text_from_csv")
        map_dict = click_cfg.get("map")
        text_value = resolve_csv_value(row, column, map_dict)
        if text_value is None:
            text_value = click_cfg.get("default_text")
        if is_empty(text_value):
            return None
        resolved_cfg = dict(click_cfg)
        resolved_cfg.pop("column", None)
        resolved_cfg.pop("text_from_csv", None)
        resolved_cfg.pop("map", None)
        resolved_cfg.pop("default_text", None)
        resolved_cfg["text"] = text_value
        return resolved_cfg

    return click_cfg


def find_click_cfg(step: Dict[str, Any], selector: str) -> Optional[Any]:
    for click_cfg in step.get("clicks", []):
        if isinstance(click_cfg, str) and click_cfg == selector:
            return click_cfg
        if isinstance(click_cfg, dict) and click_cfg.get("selector") == selector:
            return click_cfg
    return None


def find_wait_cfg(step: Dict[str, Any], selector: str) -> Optional[Dict[str, Any]]:
    for wait_cfg in step.get("wait_for_selectors", []):
        if wait_cfg.get("selector") == selector:
            return wait_cfg
    return None


def find_date_cfg(step: Dict[str, Any], selector: str) -> Optional[Dict[str, Any]]:
    for date_cfg in step.get("date_increment", []):
        if date_cfg.get("selector") == selector:
            return date_cfg
    return None


def run_clicks(
    page,
    clicks: List[Any],
    row: Dict[str, str],
    phase: str,
    timeout_ms: int,
    delay_cfg: Optional[Dict[str, Any]],
) -> None:
    for click_cfg in clicks:
        click_phase = "late"
        if isinstance(click_cfg, dict):
            click_phase = str(click_cfg.get("phase", "late")).lower()
        if click_phase != phase:
            continue

        resolved_cfg = resolve_click_cfg(click_cfg, row)
        if resolved_cfg is None:
            continue
        click_item(page, resolved_cfg, timeout_ms)
        random_sleep(delay_cfg, "between_actions_ms")


def apply_date_increment(
    page,
    date_cfg: Dict[str, Any],
    row: Dict[str, str],
    row_index: int,
    timeout_ms: int,
) -> None:
    only_if = date_cfg.get("only_if")
    if only_if:
        cond_col = only_if.get("column")
        expected = only_if.get("value")
        if cond_col and expected is not None:
            allow_empty = bool(only_if.get("allow_empty", False))
            actual = resolve_csv_value(row, cond_col, only_if.get("map"))
            if actual is None:
                if not allow_empty:
                    return
            elif str(actual).lower() != str(expected).lower():
                return
    selector = date_cfg.get("selector")
    base_date_str = date_cfg.get("base_date")
    if not selector or not base_date_str:
        return
    fmt = date_cfg.get("format", "%Y-%m-%d")
    offset_days = int(date_cfg.get("offset_days", 1))
    start_at = int(date_cfg.get("start_at", 1))
    base_date = datetime.strptime(base_date_str, "%Y-%m-%d")
    delta_days = max(0, row_index - start_at) * offset_days
    target_date = base_date + timedelta(days=delta_days)
    fill_input(page, selector, target_date.strftime(fmt), timeout_ms)


def run_step(
    page,
    step: Dict[str, Any],
    row: Dict[str, str],
    row_index: int,
    timeout_ms: int,
    delay_cfg: Optional[Dict[str, Any]],
) -> None:
    url = step.get("url")
    if url:
        log(f"  Navigating: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                log(f"  Page URL: {page.url}")
                log(f"  Page Title: {page.title()}")
            except Exception:
                pass
        except PlaywrightTimeoutError:
            log(f"  Navigation timeout: {url}")

    for action_type, selector in HTML_FORM_FLOW:
        if action_type == "required_input":
            resolved = get_required_input_value(step, selector, row)
            if resolved is None:
                continue
            value, source = resolved
            log(f"  Fill {selector}: {source}")
            fill_input(page, selector, value, timeout_ms)
            random_sleep(delay_cfg, "between_actions_ms")
            continue

        if action_type == "input":
            resolved = get_optional_input_value(step, selector, row)
            if resolved is None:
                continue
            value, source = resolved
            log(f"  Fill {selector}: {source}")
            fill_input(page, selector, value, timeout_ms)
            random_sleep(delay_cfg, "between_actions_ms")
            continue

        if action_type == "select":
            sel_value = get_effective_select_value(step, selector, row, after=False)
            if sel_value is None:
                continue
            log(f"  Select {selector}: {sel_value}")
            select_menu_option(page, selector, sel_value, timeout_ms)
            random_sleep(delay_cfg, "between_actions_ms")
            continue

        if action_type == "select_after":
            sel_value = get_effective_select_value(step, selector, row, after=True)
            if sel_value is None:
                continue
            log(f"  Select {selector}: {sel_value}")
            select_menu_option(page, selector, sel_value, timeout_ms)
            random_sleep(delay_cfg, "between_actions_ms")
            continue

        if action_type == "checkbox":
            resolved = get_effective_checkbox_value(step, selector, row)
            if resolved is None:
                continue
            checked, source = resolved
            log(f"  Checkbox {selector}: {source}")
            set_checkbox(page, selector, checked, timeout_ms)
            random_sleep(delay_cfg, "between_actions_ms")
            continue

        if action_type == "wait":
            wait_cfg = find_wait_cfg(step, selector)
            if wait_cfg is None:
                continue
            log(f"  Waiting for {selector} ({wait_cfg.get('state', 'visible')})")
            page.wait_for_selector(
                selector,
                state=wait_cfg.get("state", "visible"),
                timeout=int(wait_cfg.get("timeout_ms", timeout_ms)),
            )
            random_sleep(delay_cfg, "between_actions_ms")
            continue

        if action_type == "date":
            date_cfg = find_date_cfg(step, selector)
            if date_cfg is None:
                continue
            log(f"  Date increment for {selector}")
            apply_date_increment(page, date_cfg, row, row_index, timeout_ms)
            random_sleep(delay_cfg, "between_actions_ms")
            continue

        if action_type == "click":
            click_cfg = find_click_cfg(step, selector)
            if click_cfg is None:
                continue
            resolved_cfg = resolve_click_cfg(click_cfg, row)
            if resolved_cfg is None:
                continue
            click_item(page, resolved_cfg, timeout_ms)
            random_sleep(delay_cfg, "between_actions_ms")
            if selector == "#gen_keywords":
                kw_cfg = step.get("keywords_from_csv")
                if kw_cfg:
                    kw_col = kw_cfg.get("column")
                    kw_delim = kw_cfg.get("delimiter", ";")
                    kw_input = kw_cfg.get("input_selector", ".kic-add textarea")
                    if kw_col:
                        log(f"  Keywords from {kw_col}")
                        add_keywords(
                            page, kw_input, row.get(kw_col, ""), kw_delim, timeout_ms
                        )
                        random_sleep(delay_cfg, "between_actions_ms")
            continue

    # Wait for selector if configured
    wait_cfg = step.get("wait_for")
    if wait_cfg:
        wait_selector = wait_cfg.get("selector")
        wait_state = wait_cfg.get("state", "visible")
        wait_timeout = int(wait_cfg.get("timeout_ms", timeout_ms))
        if wait_selector:
            log(f"  Waiting for {wait_selector} ({wait_state})")
            page.wait_for_selector(wait_selector, state=wait_state, timeout=wait_timeout)

    # Optional sleep
    sleep_ms = step.get("sleep_ms")
    if sleep_ms:
        time.sleep(float(sleep_ms) / 1000.0)


def main() -> int:
    config_path = resolve_path(DEFAULT_CONFIG)
    if not config_path.exists():
        log(f"Missing config file: {config_path}")
        return 1

    cfg = load_config(config_path)
    timeout_ms = int(cfg.get("timeout_ms", 30000))
    delay_cfg = cfg.get("random_delay_ms")

    rows = read_csv(cfg["csv"]) if cfg.get("csv") else []
    if not rows:
        log("No CSV rows found. Check csv.path in config.json.")
        return 1

    start = int(cfg.get("row_start", 1))
    end = int(cfg.get("row_end", len(rows)))
    rows = rows[start - 1 : end]
    log(f"Rows to process: {len(rows)}")

    browser_cfg = cfg.get("browser", {})
    user_data_dir = browser_cfg.get("user_data_dir")
    if not user_data_dir:
        log("browser.user_data_dir is required in config.json")
        return 1

    user_data_dir = str(resolve_path(user_data_dir))
    executable_path = browser_cfg.get("executable_path")
    headless = bool(browser_cfg.get("headless", False))
    slow_mo = int(browser_cfg.get("slow_mo_ms", 0))
    profile_dir = browser_cfg.get("profile_dir")
    browser_type = (browser_cfg.get("type") or "chromium").lower()

    steps = cfg.get("steps", [])
    if not steps:
        log("No steps configured in config.json")
        return 1

    # Prompt for schedule start date if any date_increment is configured
    date_cfgs: List[Dict[str, Any]] = []
    for step in steps:
        for date_cfg in step.get("date_increment", []):
            date_cfgs.append(date_cfg)
    if date_cfgs:
        default_date = date_cfgs[0].get("base_date")
        base_date = prompt_start_date(default_date)
        for date_cfg in date_cfgs:
            date_cfg["base_date"] = base_date

    args = []
    if profile_dir and browser_type == "chromium":
        args.append(f"--profile-directory={profile_dir}")
    elif profile_dir and browser_type != "chromium":
        log("profile_dir is set but ignored for non-chromium browsers.")

    log(f"Launching Playwright (browser={browser_type}, profile={user_data_dir})")
    with sync_playwright() as p:
        if browser_type == "firefox":
            browser = p.firefox
        elif browser_type == "webkit":
            browser = p.webkit
        else:
            browser = p.chromium

        log("Launching persistent context...")
        context = browser.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            executable_path=executable_path,
            slow_mo=slow_mo,
            args=args,
        )
        log("Context launched.")
        log(f"Existing pages: {len(context.pages)}")
        # Always create a fresh tab to control, then bring it to front.
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        page.set_default_navigation_timeout(timeout_ms)
        try:
            page.bring_to_front()
        except PlaywrightTimeoutError:
            pass
        log(f"Using page: {page.url}")

        total = len(rows)
        for idx, row in enumerate(rows, start=1):
            log(f"Row {idx}/{total}")
            for step in steps:
                repeat = step.get("repeat", "per_row")
                if repeat == "once" and idx != 1:
                    continue
                run_step(page, step, row, idx, timeout_ms, delay_cfg)
            random_sleep(delay_cfg, "between_rows_ms")

        log("Done.")
        context.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
