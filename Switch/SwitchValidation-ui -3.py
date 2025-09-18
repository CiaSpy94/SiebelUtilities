# -*- coding: utf-8 -*-
"""
Git & FUT Switch Validator — Enhanced (ttkbootstrap edition)

Prerequisite:
    pip install ttkbootstrap

This version adds:
 - Thread-safe UI updates
 - Determinate progress + Cancel
 - Resizable split view
 - Sorting, zebra rows, filters
 - Context menu (copy/open)
 - Theme switcher (ttkbootstrap)
 - Settings persistence
"""

import os
import sys
import csv
import json
import time
import glob
import queue
import threading
import subprocess
import platform
import tkinter as tk
from tkinter import filedialog, messagebox
import xml.etree.ElementTree as ET
import ttkbootstrap as tb
from ttkbootstrap import ttk
from ttkbootstrap.constants import *

# --------------------- Constants and paths ---------------------
APP_TITLE = "Git & FUT Switch Validator — ttkbootstrap"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_DIR = os.getcwd()
PARENT_DIR = os.path.dirname(CURRENT_DIR)
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
SETTINGS_PATH = os.path.join(SCRIPT_DIR, "user_settings.json")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

BRANCH_CONFIG = os.path.join(SCRIPT_DIR, "branch_config.json")
REQUIRED_HEADERS = ["ADO Reference", "Release", "Switch Name", "Divisions", "Value", "Status"]

# XML XPaths
XPATH_REFERENCE = "./ListOfVfFutSwitchIo/VfFutSwitchBc/Reference"
XPATH_SWITCH = "./ListOfVfFutSwitchIo/VfFutSwitchBc/Switch"

# --------------------- Root & style ---------------------
# Choose a default theme; you can change at runtime from the menu
style = tb.Style("cosmo")
root = tb.Window(themename=style.theme.name)  # keep consistent with Style
root.title(APP_TITLE)
root.geometry("1280x800")
root.minsize(1050, 720)

# Color palette from ttkbootstrap to keep consistent branding
COL = style.colors
GOOD = COL.success            # green
BAD = COL.danger              # red
ACCENT = COL.info             # info blue
SUBTEXT = COL.secondary       # for status text
TEXT_FG = COL.fg
TEXT_BG = COL.input           # nice neutral for text widgets
PANEL_BG = COL.bg

# --------------------- State vars ---------------------
repo_var = tk.StringVar()
branch_var = tk.StringVar()
csv_path_var = tk.StringVar()
xml_path_var = tk.StringVar()

logging_enabled = tk.BooleanVar(value=False)
current_branch = tk.StringVar(value="N/A")

# Run/Thread state
is_running = tk.BooleanVar(value=False)
cancel_event = threading.Event()
ui_queue = queue.Queue()  # thread -> UI

# Results filtering
status_filter_var = tk.StringVar(value="All")           # "All" | "VALIDATED" | "FAILED"
results_search_var = tk.StringVar()                     # text filter
_all_rows = []  # cache of displayed rows for filtering
# --------------------- Utility ---------------------
def ts():
    return time.strftime("%Y%m%d_%H%M%S")

def info(msg: str):
    if threading.current_thread() is threading.main_thread():
        status_label.config(text=msg)
    else:
        ui_post({"type": "status", "msg": msg})

def run_cmd(args, cwd=None, shell=False, timeout=120):
    """Run a command and return (ok, output)."""
    try:
        out = subprocess.check_output(
            args, cwd=cwd, shell=shell,
            stderr=subprocess.STDOUT, text=True, timeout=timeout
        )
        return (True, out)
    except subprocess.CalledProcessError as e:
        return (False, e.output)
    except subprocess.TimeoutExpired:
        return (False, f"Timed out after {timeout}s: {args}")

def find_git_repos():
    if not os.path.isdir(PARENT_DIR):
        return []
    repos = []
    for f in os.listdir(PARENT_DIR):
        p = os.path.join(PARENT_DIR, f)
        if os.path.isdir(p) and os.path.isdir(os.path.join(p, ".git")):
            repos.append(f)
    return sorted(repos)

def filter_repos(term):
    all_repos = find_git_repos()
    if not term:
        return all_repos
    term_low = term.lower()
    return [r for r in all_repos if term_low in r.lower()]

def get_current_branch(repo_path):
    ok, out = run_cmd(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo_path)
    if ok:
        return out.strip()
    return "Unknown"

def load_branches_from_config():
    try:
        with open(BRANCH_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
        branches = data.get("branches", [])
        return [str(x) for x in branches]
    except Exception:
        return []

def ensure_repo_selected():
    r = repo_var.get().strip()
    if not r:
        messagebox.showwarning("Select repository", "Please select a repository.")
        return None
    repo_path = os.path.join(PARENT_DIR, r)
    if not os.path.isdir(repo_path):
        messagebox.showerror("Repository not found", f"Path not found:\n{repo_path}")
        return None
    return repo_path

def current_branch_prefixless(name):
    # clean known prefixes
    return (
        name
        .replace("SIEBELUPG_IP23.12_ONCCSX_", "")
        .replace("SIEBELUPG_IP23.12_ONCCSX", "")
        .replace("SIEBELUPG_IP23.12_ONCCS_", "")
    )

def full_branch_name(short):
    return f"SIEBELUPG_IP23.12_ONCCSX{short}"

def update_xml_path():
    repo_path = ensure_repo_selected()
    if not repo_path:
        xml_path_var.set("")
        return
    xml_dir = os.path.join(repo_path, "build", "refdata", "FUT_Switch_Config")
    xml_path_var.set(xml_dir)

def update_current_branch_label():
    repo_path = ensure_repo_selected()
    if not repo_path:
        current_branch.set("N/A")
        return
    br = get_current_branch(repo_path)
    current_branch.set(br)

def refresh_repo_list():
    term = search_repo_var.get().strip()
    repos = filter_repos(term)
    repo_combo["values"] = repos
    if repos:
        cur = repo_var.get()
        if cur in repos:
            repo_combo.set(cur)
        else:
            repo_combo.set(repos[0])
            repo_var.set(repos[0])
            on_repo_changed()
    else:
        repo_combo.set("")
        repo_var.set("")
        current_branch.set("N/A")
        xml_path_var.set("")

def set_branch_default_from_current():
    repo_path = ensure_repo_selected()
    if not repo_path:
        return
    br_full = get_current_branch(repo_path) or ""
    if '/' in br_full:
        br_full = br_full.split('/', 1)[-1]
    short = current_branch_prefixless(br_full).strip()
    if not short:
        return
    values = list(branch_combo['values'])
    if short not in values:
        values = [short] + values
        branch_combo['values'] = values
    branch_combo.set(short)
    branch_var.set(short)

def on_repo_changed(event=None):
    update_current_branch_label()
    update_xml_path()
    set_branch_default_from_current()

# --------------------- Thread-safe UI bus ---------------------
def ui_post(payload: dict):
    ui_queue.put(payload)

def ui_pump():
    """Process queued UI updates from worker threads."""
    try:
        while True:
            payload = ui_queue.get_nowait()
            t = payload.get("type")
            if t == "progress":
                _append_progress_ui(payload["msg"], payload.get("ok", True))
            elif t == "git_output":
                _show_output_ui(payload["msg"], payload.get("success", True))
            elif t == "status":
                status_label.config(text=payload["msg"])
            elif t == "result_row":
                _append_result_row_ui(payload["row"], payload.get("tag"))
            elif t == "clear_results":
                for i in results_tree.get_children():
                    results_tree.delete(i)
            elif t == "running":
                _set_running_ui(payload["running"])
            elif t == "progressbar":
                progressbar['value'] = payload.get("value", 0)
    except queue.Empty:
        pass
    root.after(50, ui_pump)  # ~20 FPS

def _set_running_ui(running: bool):
    is_running.set(running)
    state = DISABLED if running else NORMAL
    for w in (btn_validate, btn_gen, btn_clear_pull, btn_git_pull, repo_combo, branch_combo):
        try:
            w.configure(state=state)
        except tk.TclError:
            pass
    root.configure(cursor="watch" if running else "")
    if not running:
        progressbar.stop()
        progressbar['value'] = 0

def set_running(running: bool):
    if threading.current_thread() is threading.main_thread():
        _set_running_ui(running)
    else:
        ui_post({"type":"running","running":running})

def set_progress(pct: float):
    if threading.current_thread() is threading.main_thread():
        progressbar['value'] = max(0.0, min(100.0, pct))
    else:
        ui_post({"type":"progressbar","value":pct})

# --------------------- Git operations & consoles ---------------------
def _show_output_ui(msg, success=True):
    git_box.configure(state="normal")
    git_box.delete("1.0", tk.END)
    tag = ("success" if success else "danger")
    git_box.insert(tk.END, msg)
    git_box.configure(state="disabled")

def show_output(msg, success=True):
    if threading.current_thread() is threading.main_thread():
        _show_output_ui(msg, success)
    else:
        ui_post({"type":"git_output","msg":msg,"success":success})

def _append_progress_ui(msg, ok=True):
    progress_box.configure(state="normal")
    progress_box.insert(tk.END, msg + "\n")
    progress_box.see(tk.END)
    progress_box.configure(state="disabled")

def append_progress(msg, ok=True):
    if threading.current_thread() is threading.main_thread():
        _append_progress_ui(msg, ok)
    else:
        ui_post({"type":"progress","msg":msg,"ok":ok})

def git_switch_reset_pull(branch_short):
    repo_path = ensure_repo_selected()
    if not repo_path:
        return False
    full_name = full_branch_name(branch_short)
    show_output(f"> Switching to {full_name} ...", True)
    append_progress(f"Git: switch {full_name}", True)
    ok1, out1 = run_cmd(["git", "switch", full_name], cwd=repo_path)
    show_output(out1, ok1)
    append_progress(out1.strip(), ok1)
    if not ok1:
        return False

    show_output(f"> Reset to origin/{full_name} ...", True)
    ok2, out2 = run_cmd(["git", "fetch", "origin"], cwd=repo_path)
    append_progress(("Fetched origin" if ok2 else out2.strip()), ok2)
    if not ok2:
        show_output(out2, False)
        return False
    ok3, out3 = run_cmd(["git", "reset", "--hard", f"origin/{full_name}"], cwd=repo_path)
    show_output(out3, ok3)
    append_progress(out3.strip(), ok3)
    if not ok3:
        return False

    show_output("> git pull ...", True)
    ok4, out4 = run_cmd(["git", "pull"], cwd=repo_path)
    show_output(out4, ok4)
    append_progress(out4.strip(), ok4)
    update_current_branch_label()
    return ok4

def on_branch_selected(event=None):
    b = branch_var.get().strip()
    if not b:
        return
    if not messagebox.askyesno("Confirm", f"Switch/reset/pull branch: {full_branch_name(b)}?"):
        return
    git_switch_reset_pull(b)

def git_pull_current():
    repo_path = ensure_repo_selected()
    if not repo_path:
        return
    show_output("> git pull ...", True)
    ok, out = run_cmd(["git", "pull"], cwd=repo_path)
    show_output(out, ok)
    append_progress(out.strip(), ok)
    update_current_branch_label()

# --------------------- CSV & XML helpers ---------------------
def browse_csv():
    f = filedialog.askopenfilename(
        title="Select the CSV",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if f:
        csv_path_var.set(f)
        save_settings()

def validate_csv_headers():
    path = csv_path_var.get().strip()
    if not path:
        messagebox.showwarning("CSV", "Please select a CSV first.")
        return False
    if not os.path.isfile(path):
        messagebox.showerror("CSV", f"CSV not found:\n{path}")
        return False
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration:
                messagebox.showerror("CSV", "CSV is empty.")
                return False
    except Exception as e:
        messagebox.showerror("CSV", f"Failed to read CSV:\n{e}")
        return False

    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        messagebox.showerror("CSV", f"Missing required headers: {', '.join(missing)}")
        return False
    info("CSV header validation passed.")
    append_progress("CSV header validation passed.", True)
    return True

def list_switch_xml_files(xml_dir, switch_name):
    pattern = os.path.join(xml_dir, "*.xml")
    switch_low = (switch_name or "").lower()
    files = [p for p in glob.glob(pattern) if switch_low in os.path.basename(p).lower()]
    return files

def parse_xml_text(xml_file):
    try:
        with open(xml_file, "r", encoding="utf-8") as f:
            content = f.read()
        linear = " ".join(content.split())
        root_elem = ET.fromstring(linear)
        return (True, root_elem, linear)
    except Exception as e:
        return (False, None, f"XML parse error in {os.path.basename(xml_file)}: {e}")

def get_text(root_elem, relative_xpath):
    node = root_elem.find(relative_xpath)
    if node is None:
        return None
    return (node.text or "").strip()

def write_csv(rows, path, headers):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

# --------------------- Results table helpers ---------------------
results_headers = ["ADO Reference", "Switch Name", "Value", "Status", "GitXmlValue", "MatchedFiles"]

def _append_result_row_ui(row_dict, tag=None):
    vals = [row_dict.get(h, "") for h in results_headers]
    results_tree.insert("", tk.END, values=vals, tags=(tag,) if tag else ())

def append_result_row(row_dict, ok, note="", color_tag=None):
    # cache for filtering
    row_cache = {h: row_dict.get(h, "") for h in results_headers}
    _all_rows.append(row_cache)
    if threading.current_thread() is threading.main_thread():
        _append_result_row_ui(row_cache, color_tag)
    else:
        ui_post({"type":"result_row","row":row_cache,"tag":color_tag})

def refresh_zebra():
    for i, iid in enumerate(results_tree.get_children("")):
        base_tags = list(results_tree.item(iid, "tags"))
        base_tags = [t for t in base_tags if t not in ("even", "odd")]
        base_tags.append("even" if i % 2 == 0 else "odd")
        results_tree.item(iid, tags=tuple(base_tags))

def apply_results_filter(*_):
    term = (results_search_var.get() or "").lower().strip()
    status_pick = status_filter_var.get()
    # rebuild table
    for iid in results_tree.get_children(""):
        results_tree.delete(iid)
    for r in _all_rows:
        if term:
            hay = f"{r.get('Switch Name','')} {r.get('ADO Reference','')}".lower()
            if term not in hay:
                continue
        if status_pick != "All":
            if (r.get("Status","").upper() != status_pick.upper()):
                continue
        tag = "ok" if r.get("Status","").upper() == "VALIDATED" else "fail"
        _append_result_row_ui(r, tag)
    refresh_zebra()

# --------------------- Validation worker ---------------------
def process_validation():
    try:
        path = csv_path_var.get().strip()
        xml_dir = xml_path_var.get().strip()
        repo_path = ensure_repo_selected()
        if not repo_path:
            return
        if not path or not os.path.isfile(path):
            messagebox.showwarning("CSV", "Please select a valid CSV.")
            return
        if not xml_dir or not os.path.isdir(xml_dir):
            messagebox.showwarning("XML", f"XML directory not found:\n{xml_dir}")
            return
        if not validate_csv_headers():
            return

        stamp = ts()
        result_path = os.path.join(RESULTS_DIR, f"switch_validation_result_{stamp}.csv")
        log_path = os.path.join(LOGS_DIR, f"switch_validation_log_{stamp}.log")
        do_log = logging_enabled.get()

        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            messagebox.showerror("CSV", f"Failed to read CSV rows:\n{e}")
            return

        # prepare UI table
        ui_post({"type": "clear_results"})
        _all_rows.clear()

        processed = []
        total = len(rows)
        append_progress(f"Validation started. Records: {total}", True)

        out_headers = ["ADO Reference", "Release", "Switch Name", "Divisions", "Value",
                       "Status", "GitXmlValue", "MatchedFiles"]

        log_f = open(log_path, "w", encoding="utf-8") if do_log else None
        if do_log:
            log_f.write(
                f"Validation Log - {stamp}\n"
                f"Repo: {repo_var.get()}\n"
                f"Branch: {current_branch.get()}\n"
                f"XML Path: {xml_dir}\n"
                f"Source CSV: {path}\n\n"
            )

        for idx, row in enumerate(rows, start=1):
            if cancel_event.is_set():
                append_progress("Validation cancelled by user.", False)
                break

            set_progress((idx - 1) * 100.0 / max(1, total))

            ado_ref = (row.get("ADO Reference") or "").strip()
            release = (row.get("Release") or "").strip()
            switch_name = (row.get("Switch Name") or "").strip()
            divisions = (row.get("Divisions") or "").strip()
            csv_value_raw = (row.get("Value") or "").strip()
            csv_value_up = csv_value_raw.upper()

            if do_log:
                log_f.write(
                    f"[Row {idx}] ADO:{ado_ref} Release:{release} "
                    f"Switch:{switch_name} Divisions:{divisions} Value(csv):{csv_value_raw}\n"
                )

            matched_files = list_switch_xml_files(xml_dir, switch_name)
            if do_log:
                log_f.write(f" Matched XML files: {matched_files if matched_files else 'None'}\n")

            result_status = "FAILED"
            git_xml_value = ""
            note = ""
            is_ok = False

            if len(matched_files) == 0:
                note = "No XML file found for Switch Name"
                append_progress(f"[{idx}/{total}] {switch_name}: {note}", False)
            elif len(matched_files) > 1:
                note = "Failed: multiple files present"
                files = ", ".join(os.path.basename(x) for x in matched_files)
                append_progress(f"[{idx}/{total}] {switch_name}: {note} -> {files}", False)
            else:
                xml_file = matched_files[0]
                ok_parse, root_elem, lin_or_err = parse_xml_text(xml_file)
                if not ok_parse:
                    note = f"XML parse error: {lin_or_err}"
                    append_progress(f"[{idx}/{total}] {switch_name}: {note}", False)
                else:
                    ref_text = get_text(root_elem, XPATH_REFERENCE) or ""
                    sw_text = get_text(root_elem, XPATH_SWITCH) or ""
                    git_xml_value = sw_text

                    ref_ok = (switch_name.upper() == ref_text.strip().upper())
                    sw_ok = (csv_value_up == sw_text.strip().upper())

                    if do_log:
                        log_f.write(f" XPath Reference: {XPATH_REFERENCE} -> '{ref_text}'\n")
                        log_f.write(f" XPath Switch: {XPATH_SWITCH} -> '{sw_text}'\n")

                    if ref_ok and sw_ok:
                        result_status = "VALIDATED"
                        is_ok = True
                        note = "OK"
                        append_progress(f"[{idx}/{total}] {switch_name}: Validated", True)
                    else:
                        mism = []
                        if not ref_ok: mism.append("Reference mismatch")
                        if not sw_ok: mism.append("Switch value mismatch")
                        note = "; ".join(mism) if mism else "Mismatch"
                        append_progress(
                            f"[{idx}/{total}] {switch_name}: {note} (GIT Switch='{sw_text}')", False
                        )

            out_row = {
                "ADO Reference": ado_ref,
                "Release": release,
                "Switch Name": switch_name,
                "Divisions": divisions,
                "Value": csv_value_raw,
                "Status": result_status,
                "GitXmlValue": git_xml_value,
                "MatchedFiles": ", ".join(matched_files) if matched_files else ""
            }
            processed.append(out_row)
            tag = "ok" if is_ok else "fail"
            append_result_row(out_row, is_ok, note, color_tag=tag)

            if do_log:
                log_f.write(
                    f" Result: {result_status}. Note: {note}. GitXmlValue: '{git_xml_value}'\n\n"
                )

        write_csv(processed, result_path, headers=out_headers)
        append_progress(f"Validation completed. Results saved: {result_path}", True)
        if do_log:
            log_f.write(f"Completed. Results: {result_path}\n")
        info("Validation finished.")
    except Exception as e:
        messagebox.showerror("Validation Error", str(e))
    finally:
        set_running(False)
        cancel_event.clear()
        root.after(10, refresh_zebra)

def start_validation_thread():
    cancel_event.clear()
    set_running(True)
    t = threading.Thread(target=process_validation, daemon=True)
    t.start()

def cancel_validation():
    if is_running.get():
        cancel_event.set()
        append_progress("Cancelling... please wait.", False)

# --------------------- Generate switch details ---------------------
def generate_switch_details():
    xml_dir = xml_path_var.get().strip()
    if not xml_dir or not os.path.isdir(xml_dir):
        messagebox.showwarning("XML", "XML directory not found or not selected.")
        return

    xml_files = sorted(glob.glob(os.path.join(xml_dir, "*.xml")))
    if not xml_files:
        messagebox.showinfo("Generate", "No XML files found.")
        return
    stamp = ts()
    out_path = os.path.join(RESULTS_DIR, f"switch_details_{stamp}.csv")
    rows = []
    append_progress(f"Generate Switch details started. Files: {len(xml_files)}", True)

    for i, xf in enumerate(xml_files, start=1):
        ok_parse, root_elem, lin_or_err = parse_xml_text(xf)
        if not ok_parse:
            append_progress(f"[{i}/{len(xml_files)}] {os.path.basename(xf)} parse error", False)
            continue
        ref_text = get_text(root_elem, XPATH_REFERENCE) or ""
        sw_text = get_text(root_elem, XPATH_SWITCH) or ""
        status = "VALIDATED" if ref_text and sw_text else "FAILED"
        rows.append({
            "Switch Name": ref_text,
            "Value": sw_text,
            "SourceFile": os.path.basename(xf)
        })
        append_progress(
            f"[{i}/{len(xml_files)}] {os.path.basename(xf)} -> {ref_text}\n {sw_text}",
            True if status == "VALIDATED" else False
        )
    write_csv(rows, out_path, headers=["Switch Name", "Value", "SourceFile"])
    append_progress(f"Switch details CSV saved: {out_path}", True)
    info("Switch details generated.")

# --------------------- Settings persistence ---------------------
def load_settings():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings():
    data = {
        "repo": repo_var.get(),
        "csv_path": csv_path_var.get()
    }
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
def on_close():
    cancel_event.set()
    save_settings()
    root.destroy()

# --------------------- UI layout ---------------------
root.grid_columnconfigure(0, weight=1)

# --- Menu bar with theme switcher ---
menubar = tk.Menu(root)
root.config(menu=menubar)

file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Open CSV…", accelerator="Ctrl+O", command=browse_csv)
file_menu.add_command(label="Validate", accelerator="F5", command=start_validation_thread)
file_menu.add_separator()
file_menu.add_command(label="Exit", accelerator="Alt+F4", command=root.quit)
menubar.add_cascade(label="File", menu=file_menu)

git_menu = tk.Menu(menubar, tearoff=0)
git_menu.add_command(label="Git Pull (current)", command=git_pull_current)
menubar.add_cascade(label="Git", menu=git_menu)

def open_results_folder():
    try:
        if platform.system() == "Windows":
            os.startfile(RESULTS_DIR)  # type: ignore
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", RESULTS_DIR])
        else:
            subprocess.Popen(["xdg-open", RESULTS_DIR])
    except Exception as e:
        messagebox.showerror("Open folder", str(e))

view_menu = tk.Menu(menubar, tearoff=0)
view_menu.add_command(label="Open results folder", command=open_results_folder)
menubar.add_cascade(label="View", menu=view_menu)

# Theme menu
theme_menu = tk.Menu(menubar, tearoff=0)
def set_theme(name):
    style.theme_use(name)
    # update palette-dependent colors
    global COL, GOOD, BAD, ACCENT, SUBTEXT, TEXT_FG, TEXT_BG, PANEL_BG
    COL = style.colors
    GOOD = COL.success
    BAD = COL.danger
    ACCENT = COL.info
    SUBTEXT = COL.secondary
    TEXT_FG = COL.fg
    TEXT_BG = COL.input
    PANEL_BG = COL.bg
    # retag zebra
    refresh_zebra()

for name in style.theme_names():
    theme_menu.add_command(label=name, command=lambda n=name: set_theme(n))
menubar.add_cascade(label="Theme", menu=theme_menu)

help_menu = tk.Menu(menubar, tearoff=0)
help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
    "About", "Git & FUT Switch Validator — ttkbootstrap edition\n"
             "Responsive UI, cancellable validation, sorting & filters."
))
menubar.add_cascade(label="Help", menu=help_menu)

# --- Top controls: Repo & Branch ---
top_frame = ttk.Labelframe(root, text="Repository & Branch", bootstyle=INFO)
top_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
for c in range(0, 6):
    top_frame.grid_columnconfigure(c, weight=1)

ttk.Label(top_frame, text="Repository:").grid(row=0, column=0, sticky="w", padx=(6, 6), pady=6)
repo_combo = ttk.Combobox(top_frame, textvariable=repo_var, values=find_git_repos(), width=50, state=READONLY)
repo_combo.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=6)
repo_combo.bind("<<ComboboxSelected>>", on_repo_changed)

search_repo_var = tk.StringVar()
ttk.Label(top_frame, text="Search:").grid(row=0, column=2, sticky="e", padx=(6, 6), pady=6)
search_entry = ttk.Entry(top_frame, textvariable=search_repo_var)
search_entry.grid(row=0, column=3, sticky="ew", padx=(0, 6), pady=6)
ttk.Button(top_frame, text="Search", bootstyle=PRIMARY, command=refresh_repo_list)\
   .grid(row=0, column=4, sticky="w", padx=(0, 6), pady=6)

ttk.Label(top_frame, text="Current branch:").grid(row=1, column=0, sticky="w", padx=(6, 6), pady=6)
cur_branch_label = ttk.Label(top_frame, textvariable=current_branch, bootstyle=INFO)
cur_branch_label.grid(row=1, column=1, sticky="w", padx=(0, 6), pady=6)
cur_branch_label.configure(cursor="hand2")
def copy_branch_to_clipboard(event=None):
    root.clipboard_clear()
    root.clipboard_append(current_branch.get())
    info("Branch name copied.")
cur_branch_label.bind("<Button-1>", copy_branch_to_clipboard)

ttk.Label(top_frame, text="Select branch:").grid(row=2, column=0, sticky="w", padx=(6, 6), pady=6)
branch_combo = ttk.Combobox(top_frame, textvariable=branch_var, values=load_branches_from_config(), width=20, state=READONLY)
branch_combo.grid(row=2, column=1, sticky="w", padx=(0, 6), pady=6)
branch_combo.bind("<<ComboboxSelected>>", on_branch_selected)

btn_git_pull = ttk.Button(top_frame, text="Git Pull (current)", bootstyle=SECONDARY, command=git_pull_current)
btn_git_pull.grid(row=2, column=2, sticky="w", padx=(6, 6), pady=6)

# XML path (auto)
ttk.Label(top_frame, text="XML path (auto):").grid(row=3, column=0, sticky="w", padx=(6, 6), pady=(6, 6))
xml_entry = ttk.Entry(top_frame, textvariable=xml_path_var, width=80, state=READONLY)
xml_entry.grid(row=3, column=1, columnspan=4, sticky="ew", padx=(0, 6), pady=(6, 6))

# --- CSV & Actions ---
mid_frame = ttk.Labelframe(root, text="CSV & Actions", bootstyle=INFO)
mid_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
for c in range(0, 6):
    mid_frame.grid_columnconfigure(c, weight=1)

ttk.Label(mid_frame, text="CSV file:").grid(row=0, column=0, sticky="w", padx=(6, 6), pady=6)
csv_entry = ttk.Entry(mid_frame, textvariable=csv_path_var)
csv_entry.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(0, 6), pady=6)
ttk.Button(mid_frame, text="Browse", bootstyle=PRIMARY, command=browse_csv).grid(row=0, column=4, sticky="w", padx=(0, 6), pady=6)
ttk.Button(mid_frame, text="Validate CSV headers", bootstyle=SECONDARY, command=validate_csv_headers)\
   .grid(row=0, column=5, sticky="w", padx=(0, 6), pady=6)

log_chk = ttk.Checkbutton(mid_frame, text="Enable logging", variable=logging_enabled)
log_chk.grid(row=1, column=0, sticky="w", padx=(6, 6), pady=(0, 6))
btn_validate = ttk.Button(mid_frame, text="Validate", bootstyle=SUCCESS, command=start_validation_thread)
btn_validate.grid(row=1, column=1, sticky="w", padx=(0, 6), pady=(0, 6))
btn_gen = ttk.Button(mid_frame, text="Generate switch details", bootstyle=INFO, command=generate_switch_details)
btn_gen.grid(row=1, column=2, sticky="w", padx=(0, 6), pady=(0, 6))

def clear_results_and_pull():
    _all_rows.clear()
    for i in results_tree.get_children():
        results_tree.delete(i)
    progress_box.config(state="normal")
    progress_box.delete("1.0", tk.END)
    progress_box.config(state="disabled")
    git_pull_current()
    info("Cleared results and pulled latest on current branch.")
btn_clear_pull = ttk.Button(mid_frame, text="Clear & Pull", bootstyle=WARNING, command=clear_results_and_pull)
btn_clear_pull.grid(row=1, column=3, sticky="w", padx=(0, 6), pady=(0, 6))

# --- Split view (Results ⇕ Consoles) ---
split = ttk.Panedwindow(root, orient=VERTICAL)
split.grid(row=3, column=0, rowspan=2, sticky="nsew", padx=12, pady=(6, 12))
root.grid_rowconfigure(3, weight=1)

# Results frame
results_frame = ttk.Labelframe(split, text="Results", bootstyle=INFO)
results_frame.grid_columnconfigure(0, weight=1)
# Consoles frame
console_frame = ttk.Labelframe(split, text="Consoles", bootstyle=INFO)
console_frame.grid_columnconfigure(0, weight=1)
console_frame.grid_columnconfigure(1, weight=1)
console_frame.grid_rowconfigure(1, weight=1)

split.add(results_frame, weight=3)
split.add(console_frame, weight=2)

# Filter bar
filter_bar = ttk.Frame(results_frame)
filter_bar.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
filter_bar.grid_columnconfigure(1, weight=1)
ttk.Label(filter_bar, text="Filter:").grid(row=0, column=0, sticky="w", padx=(0,6))
filter_entry = ttk.Entry(filter_bar, textvariable=results_search_var)
filter_entry.grid(row=0, column=1, sticky="ew")
ttk.Label(filter_bar, text="Status:").grid(row=0, column=2, sticky="e", padx=(12,6))
status_combo = ttk.Combobox(filter_bar, state=READONLY,
                            values=["All", "VALIDATED", "FAILED"],
                            textvariable=status_filter_var, width=12)
status_combo.grid(row=0, column=3, sticky="w")

# Results Treeview
tree_container = ttk.Frame(results_frame)
tree_container.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
results_frame.grid_rowconfigure(1, weight=1)
results_frame.grid_columnconfigure(0, weight=1)

results_tree = ttk.Treeview(tree_container, columns=results_headers, show="headings", selectmode="extended", bootstyle=INFO)
for h in results_headers:
    results_tree.heading(h, text=h)
    w = 140
    if h in ("Status",):
        w = 110
    if h in ("GitXmlValue",):
        w = 200
    if h in ("MatchedFiles",):
        w = 260
    results_tree.column(h, width=w, anchor="w")

# Tag styles
results_tree.tag_configure("ok", foreground=str(GOOD))
results_tree.tag_configure("fail", foreground=str(BAD))
results_tree.tag_configure("even", background=str(PANEL_BG))
results_tree.tag_configure("odd", background=str(COL.bg))

# Scrollbars
tree_vsb = ttk.Scrollbar(tree_container, orient=VERTICAL, command=results_tree.yview)
tree_hsb = ttk.Scrollbar(tree_container, orient=HORIZONTAL, command=results_tree.xview)
results_tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)
results_tree.grid(row=0, column=0, sticky="nsew")
tree_vsb.grid(row=0, column=1, sticky="ns")
tree_hsb.grid(row=1, column=0, sticky="ew")

# Click-to-sort
def treeview_sort_by(col, descending=False):
    data = [(results_tree.set(k, col), k) for k in results_tree.get_children("")]
    try:
        data.sort(key=lambda t: (t[0] or "").lower(), reverse=descending)
    except Exception:
        data.sort(reverse=descending)
    for idx, (_, k) in enumerate(data):
        results_tree.move(k, "", idx)
    results_tree.heading(col, command=lambda c=col: treeview_sort_by(c, not descending))

for h in results_headers:
    results_tree.heading(h, text=h, command=lambda c=h: treeview_sort_by(c, False))

# Context menu
def copy_selected_rows():
    sel = results_tree.selection()
    if not sel:
        return
    lines = []
    for item in sel:
        vals = results_tree.item(item, "values")
        lines.append("\t".join(map(str, vals)))
    root.clipboard_clear()
    root.clipboard_append("\n".join(lines))

def open_matched_file():
    sel = results_tree.selection()
    if not sel:
        return
    vals = results_tree.item(sel[0], "values")
    matched = ""
    if vals:
        try:
            matched = vals[results_headers.index("MatchedFiles")]
        except Exception:
            matched = ""
    if not matched:
        messagebox.showinfo("Open", "No matched file recorded for this row.")
        return
    first = matched.split(",")[0].strip()
    if not os.path.isabs(first):
        guess = os.path.join(xml_path_var.get().strip(), os.path.basename(first))
        if os.path.isfile(guess):
            first = guess
    if os.path.isfile(first):
        try:
            if platform.system() == "Windows":
                os.startfile(first)  # type: ignore
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", first])
            else:
                subprocess.Popen(["xdg-open", first])
        except Exception as e:
            messagebox.showerror("Open", str(e))
    else:
        messagebox.showerror("Open", f"File not found:\n{first}")

tree_menu = tk.Menu(results_tree, tearoff=0)
tree_menu.add_command(label="Copy row(s)", command=copy_selected_rows)
tree_menu.add_command(label="Open matched XML", command=open_matched_file)
def on_tree_right_click(event):
    iid = results_tree.identify_row(event.y)
    if iid:
        results_tree.selection_set(iid)
        tree_menu.tk_popup(event.x_root, event.y_root)
results_tree.bind("<Button-3>", on_tree_right_click)

# Consoles: Git & Validation progress (ScrolledText)
git_label = ttk.Label(console_frame, text="Git progress", bootstyle=INFO)
git_label.grid(row=0, column=0, sticky="w", padx=6, pady=(6, 0))
val_label = ttk.Label(console_frame, text="Validation progress", bootstyle=INFO)
val_label.grid(row=0, column=1, sticky="w", padx=6, pady=(6, 0))

git_container = ttk.Frame(console_frame)
git_container.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
git_container.grid_columnconfigure(0, weight=1)
git_container.grid_rowconfigure(0, weight=1)

progress_container = ttk.Frame(console_frame)
progress_container.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)
progress_container.grid_columnconfigure(0, weight=1)
progress_container.grid_rowconfigure(0, weight=1)

git_box = tk.Text(git_container, height=12, bg=str(TEXT_BG), fg=str(TEXT_FG),
                  insertbackground=str(TEXT_FG), font=("Consolas", 10), relief="solid", bd=1)
git_vsb = ttk.Scrollbar(git_container, orient=VERTICAL, command=git_box.yview)
git_hsb = ttk.Scrollbar(git_container, orient=HORIZONTAL, command=git_box.xview)
git_box.configure(yscrollcommand=git_vsb.set, xscrollcommand=git_hsb.set)
git_box.grid(row=0, column=0, sticky="nsew")
git_vsb.grid(row=0, column=1, sticky="ns")
git_hsb.grid(row=1, column=0, sticky="ew")
git_box.config(state="disabled")

progress_box = tk.Text(progress_container, height=12, bg=str(TEXT_BG), fg=str(TEXT_FG),
                       insertbackground=str(TEXT_FG), font=("Consolas", 10), relief="solid", bd=1)
prog_vsb = ttk.Scrollbar(progress_container, orient=VERTICAL, command=progress_box.yview)
prog_hsb = ttk.Scrollbar(progress_container, orient=HORIZONTAL, command=progress_box.xview)
progress_box.configure(yscrollcommand=prog_vsb.set, xscrollcommand=prog_hsb.set)
progress_box.grid(row=0, column=0, sticky="nsew")
prog_vsb.grid(row=0, column=1, sticky="ns")
prog_hsb.grid(row=1, column=0, sticky="ew")
progress_box.config(state="disabled")

# Status line with progress and cancel
status_bar = ttk.Frame(root)
status_bar.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 8))
status_bar.grid_columnconfigure(0, weight=1)
status_label = ttk.Label(status_bar, text="", bootstyle=SECONDARY)
status_label.grid(row=0, column=0, sticky="w")

cancel_btn = ttk.Button(status_bar, text="Cancel", bootstyle=DANGER, command=cancel_validation)
cancel_btn.grid(row=0, column=1, sticky="e", padx=(8, 8))
progressbar = ttk.Progressbar(status_bar, orient=HORIZONTAL, mode="determinate", length=240, bootstyle=INFO_STRIPED)
progressbar.grid(row=0, column=2, sticky="e")

# --------------------- Initialization ---------------------
# Load repos and branch defaults
repos = find_git_repos()
repo_combo['values'] = repos

# restore settings
_settings = load_settings()
if repos:
    default_repo = _settings.get("repo", repos[0])
    if default_repo in repos:
        repo_combo.set(default_repo)
        repo_var.set(default_repo)
        on_repo_changed()
else:
    info("No Git repositories found in parent folder.")

branches = load_branches_from_config()
branch_combo["values"] = branches

if _settings.get("csv_path"):
    csv_path_var.set(_settings["csv_path"])

info("Ready.")

# Keyboard shortcuts
root.bind_all("<Control-o>", lambda e: browse_csv())
root.bind_all("<F5>", lambda e: start_validation_thread())
root.bind_all("<Escape>", lambda e: cancel_validation())

# Start the UI pump and set close handler
root.after(50, ui_pump)
root.protocol("WM_DELETE_WINDOW", on_close)

# Main loop
root.mainloop()
