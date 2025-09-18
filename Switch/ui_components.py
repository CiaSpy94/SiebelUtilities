import os
import sys
import csv
import json
import time
import glob
import shutil
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET

# ---------- Constants and paths ----------
APP_TITLE = "Git & FUT Switch Validator Dashboard"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_DIR = os.getcwd()
PARENT_DIR = os.path.dirname(CURRENT_DIR)

RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

BRANCH_CONFIG = os.path.join(SCRIPT_DIR, "branch_config.json")
REQUIRED_HEADERS = ["ADO Reference", "Release", "Switch Name", "Divisions", "Value", "Status"]

# XML XPaths
XPATH_REFERENCE = "./ListOfVfFutSwitchIo/VfFutSwitchBc/Reference"
XPATH_SWITCH = "./ListOfVfFutSwitchIo/VfFutSwitchBc/Switch"

# ---------- Tk root and styling ----------
root = tk.Tk()
root.title(APP_TITLE)
root.geometry("1200x860")
root.minsize(1000, 700)

# Use a light-friendly ttk style
style = ttk.Style()
# 'clam' is reliable across platforms; we customize it for a light feel
style.theme_use("clam")

# Base palette
BG = "#ffffff"
PANEL_BG = "#f7f7f7"
ACCENT_BG = "#e9f5ff"
TEXT = "#1f2937"
SUBTEXT = "#374151"
PRIMARY = "#0ea5e9"
PRIMARY_DARK = "#0284c7"
GOOD = "#166534"
BAD = "#b91c1c"

root.configure(bg=BG)

# TTK component styles (light)
style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
style.configure("TFrame", background=BG)
style.configure("TLabelframe", background=BG, foreground=SUBTEXT, font=("Segoe UI", 10, "bold"))
style.configure("TLabelframe.Label", background=BG, foreground=SUBTEXT, font=("Segoe UI", 10, "bold"))

style.configure("TButton", padding=6, font=("Segoe UI", 10))
style.map("TButton",
          foreground=[('!disabled', 'white'), ('disabled', '#9ca3af')],
          background=[('active', PRIMARY_DARK), ('!disabled', PRIMARY), ('disabled', '#e5e7eb')],
          relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

style.configure("TEntry", fieldbackground="#ffffff", foreground=TEXT)
style.configure("TCombobox", fieldbackground="#ffffff", foreground=TEXT, background="#ffffff")
style.map("TCombobox", fieldbackground=[('readonly', '#ffffff')], foreground=[('readonly', TEXT)])

style.configure("Treeview",
                background="#ffffff",
                fieldbackground="#ffffff",
                foreground=TEXT,
                rowheight=24,
                bordercolor="#e5e7eb",
                borderwidth=1)
style.configure("Treeview.Heading",
                background=ACCENT_BG,
                foreground=TEXT,
                font=("Segoe UI", 10, "bold"))
style.map("Treeview", background=[('selected', '#dbeafe')], foreground=[('selected', TEXT)])

# Non-ttk Text widgets: use light-friendly colors
TEXT_BG = "#f9fafb"
TEXT_FG = TEXT

# ---------- State vars ----------
repo_var = tk.StringVar()
branch_var = tk.StringVar()
csv_path_var = tk.StringVar()
xml_path_var = tk.StringVar()
ado_ref_var = tk.StringVar(value="BUG")
ado_num_var = tk.StringVar()
modified_by_var = tk.StringVar()
search_repo_var = tk.StringVar()
logging_enabled = tk.BooleanVar(value=False)
current_branch = tk.StringVar(value="N/A")

# ---------- Utility ----------
def ts():
    return time.strftime("%Y%m%d_%H%M%S")

def info(msg):
    status_label.config(text=msg)

def append_progress(msg, ok=True):
    progress_box.configure(state="normal")
    progress_box.insert(tk.END, msg + "\n", ("ok" if ok else "err"))
    progress_box.tag_config("ok", foreground=GOOD)
    progress_box.tag_config("err", foreground=BAD)
    progress_box.see(tk.END)
    progress_box.configure(state="disabled")
    root.update_idletasks()

def show_output(msg, success=True):
    git_box.config(state="normal")
    git_box.delete("1.0", tk.END)
    git_box.insert(tk.END, msg, ("ok" if success else "err"))
    git_box.tag_config("ok", foreground=GOOD)
    git_box.tag_config("err", foreground=BAD)
    git_box.config(state="disabled")

def run_cmd(args, cwd=None, shell=False):
    try:
        if shell:
            out = subprocess.check_output(args, cwd=cwd, shell=True, stderr=subprocess.STDOUT, text=True)
        else:
            out = subprocess.check_output(args, cwd=cwd, stderr=subprocess.STDOUT, text=True)
        return (True, out)
    except subprocess.CalledProcessError as e:
        return (False, e.output)

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
    # Clean up if branch has prefix; we only set dropdown with bare version
    return name.replace("SIEBELUPG_IP23.12_ONCCSX", "").replace("SIEBELUPG_IP23.12_ONCCS_", "")

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

def on_repo_changed(event=None):
    update_current_branch_label()
    update_xml_path()

def git_switch_reset_pull(branch_short):
    repo_path = ensure_repo_selected()
    if not repo_path:
        return False
    full_name = full_branch_name(branch_short)
    show_output(f"> Switching to {full_name} ...", True)
    append_progress(f"Git: switch {full_name}", True)

    ok1, out1 = run_cmd(["git", "switch", full_name], cwd=repo_path)
    show_output(out1 if ok1 else out1, ok1)
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
    show_output(out3 if ok3 else out3, ok3)
    append_progress(out3.strip(), ok3)
    if not ok3:
        return False

    show_output("> git pull ...", True)
    ok4, out4 = run_cmd(["git", "pull"], cwd=repo_path)
    show_output(out4 if ok4 else out4, ok4)
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
    show_output(out if ok else out, ok)
    append_progress(out.strip(), ok)
    update_current_branch_label()

def browse_csv():
    f = filedialog.askopenfilename(
        title="Select the CSV",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if f:
        csv_path_var.set(f)

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
    # Case-insensitive substring search in filename
    pattern = os.path.join(xml_dir, "*.xml")
    switch_low = switch_name.lower()
    files = [p for p in glob.glob(pattern) if switch_low in os.path.basename(p).lower()]
    return files

def parse_xml_text(xml_file):
    # Read and linearize by stripping newlines/tabs; parse ElementTree
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

def ensure_root_row_tags(tree):
    # Treeview color via tags per row
    pass

def clear_results_and_pull():
    # Clear table and progress, then pull
    for i in results_tree.get_children():
        results_tree.delete(i)
    progress_box.config(state="normal")
    progress_box.delete("1.0", tk.END)
    progress_box.config(state="disabled")
    git_pull_current()
    info("Cleared results and pulled latest on current branch.")

def append_result_row(row_dict, ok, note="", color_tag=None):
    vals = [row_dict.get(h, "") for h in results_headers]
    iid = results_tree.insert("", tk.END, values=vals, tags=(color_tag,) if color_tag else ())
    return iid

def process_validation():
    path = csv_path_var.get().strip()
    xml_dir = xml_path_var.get().strip()
    repo_path = ensure_repo_selected()
    if not repo_path:
        return
    if not path or not os.path.isfile(path):
        messagebox.showwarning("CSV", "Please select a valid CSV.")
        return
    if not xml_dir or not os.path.isdir(xml_dir):
        messagebox.showwarning("XML", "XML directory not found:\n" + xml_dir)
        return
    if not validate_csv_headers():
        return

    stamp = ts()
    result_path = os.path.join(RESULTS_DIR, f"switch_validation_result_{stamp}.csv")
    log_path = os.path.join(LOGS_DIR, f"switch_validation_log_{stamp}.log")
    do_log = logging_enabled.get()

    # Read CSV dicts
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        messagebox.showerror("CSV", f"Failed to read CSV rows:\n{e}")
        return

    # Prepare UI table
    for i in results_tree.get_children():
        results_tree.delete(i)

    processed = []
    total = len(rows)
    append_progress(f"Validation started. Records: {total}", True)

    # Headers for result CSV
    out_headers = REQUIRED_HEADERS[:]
    if "Status" not in out_headers:
        out_headers.append("Status")
    if "StatusColor" not in out_headers:
        out_headers.append("StatusColor")
    if "GitXmlValue" not in out_headers:
        out_headers.append("GitXmlValue")
    if "MatchedFiles" not in out_headers:
        out_headers.append("MatchedFiles")

    log_f = open(log_path, "w", encoding="utf-8") if do_log else None
    if do_log:
        log_f.write(f"Validation Log - {stamp}\nRepo: {repo_var.get()}\nBranch: {current_branch.get()}\nXML Path: {xml_dir}\nSource CSV: {path}\n\n")

    try:
        for idx, row in enumerate(rows, start=1):
            # Normalize and uppercase CSV values for comparison
            ado_ref = (row.get("ADO Reference") or "").strip()
            release = (row.get("Release") or "").strip()
            switch_name = (row.get("Switch Name") or "").strip()
            divisions = (row.get("Divisions") or "").strip()
            csv_value_raw = (row.get("Value") or "").strip()
            csv_value_up = csv_value_raw.upper()
            status = (row.get("Status") or "").strip()

            # Logging row context
            if do_log:
                log_f.write(f"[Row {idx}] ADO:{ado_ref} Release:{release} Switch:{switch_name} Divisions:{divisions} Value(csv):{csv_value_raw}\n")

            # Find xml files
            matched_files = list_switch_xml_files(xml_dir, switch_name)
            if do_log:
                log_f.write(f"  Matched XML files: {matched_files if matched_files else 'None'}\n")

            result_status = "FAILED"
            result_color = "RED"
            git_xml_value = ""
            note = ""
            is_ok = False

            if len(matched_files) == 0:
                note = "No XML file found for Switch Name"
                append_progress(f"[{idx}/{total}] {switch_name}: {note}", False)
            elif len(matched_files) > 1:
                note = "Failed: multiple files present"
                append_progress(f"[{idx}/{total}] {switch_name}: {note} -> {', '.join(os.path.basename(x) for x in matched_files)}", False)
            else:
                xml_file = matched_files[0]
                ok_parse, root_elem, lin_or_err = parse_xml_text(xml_file)
                if not ok_parse:
                    note = f"XML parse error: {lin_or_err}"
                    append_progress(f"[{idx}/{total}] {switch_name}: {note}", False)
                else:
                    # Extract values from XPaths
                    ref_text = get_text(root_elem, XPATH_REFERENCE) or ""
                    sw_text = get_text(root_elem, XPATH_SWITCH) or ""
                    git_xml_value = sw_text

                    # uppercase compare
                    ref_ok = (switch_name.upper() == ref_text.strip().upper())
                    sw_ok = (csv_value_up == sw_text.strip().upper())

                    if do_log:
                        log_f.write(f"  XPath Reference: {XPATH_REFERENCE} -> '{ref_text}'\n")
                        log_f.write(f"  XPath Switch:    {XPATH_SWITCH} -> '{sw_text}'\n")

                    if ref_ok and sw_ok:
                        result_status = "VALIDATED"
                        result_color = "GREEN"
                        is_ok = True
                        note = "OK"
                        append_progress(f"[{idx}/{total}] {switch_name}: Validated", True)
                    else:
                        mism = []
                        if not ref_ok:
                            mism.append("Reference mismatch")
                        if not sw_ok:
                            mism.append("Switch value mismatch")
                        note = "; ".join(mism) if mism else "Mismatch"
                        append_progress(f"[{idx}/{total}] {switch_name}: {note} (GIT Switch='{sw_text}')", False)

            # Build output row
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

            # UI results table (color row)
            tag = "ok" if is_ok else "fail"
            append_result_row(out_row, is_ok, note, color_tag=tag)

            if do_log:
                log_f.write(f"  Result: {result_status}. Note: {note}. GitXmlValue: '{git_xml_value}'\n\n")

        # Write results
        write_csv(processed, result_path, headers=["ADO Reference", "Release", "Switch Name", "Divisions", "Value", "Status","GitXmlValue", "MatchedFiles"])
        append_progress(f"Validation completed. Results saved: {result_path}", True)
        if do_log:
            log_f.write(f"Completed. Results: {result_path}\n")
            append_progress(f"Log saved: {log_path}", True)

        info("Validation finished.")
    except Exception as e:
        messagebox.showerror("Validation Error", str(e))
    finally:
        if log_f:
            log_f.close()

def start_validation_thread():
    t = threading.Thread(target=process_validation, daemon=True)
    t.start()

def generate_switch_details():
    # Scan XML dir and produce CSV with Switch Name (Reference) and Value (Switch)
    xml_dir = xml_path_var.get().strip()
    if not xml_dir or not os.path.isdir(xml_dir):
        messagebox.showwarning("XML", "XML directory not found or not selected.")
        return
    # Gather all xml files
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
        append_progress(f"[{i}/{len(xml_files)}] {os.path.basename(xf)} -> {ref_text} | {sw_text}", True if status == "VALIDATED" else False)

    write_csv(rows, out_path, headers=["Switch Name", "Value", "SourceFile"])
    append_progress(f"Switch details CSV saved: {out_path}", True)
    info("Switch details generated.")

# ---------- UI layout (light-themed, refactored) ----------

# Root grid config for responsiveness
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(3, weight=1)   # Results area grows
root.grid_rowconfigure(4, weight=1)   # Consoles area grows

# Top controls: Repo & Branch
top_frame = ttk.LabelFrame(root, text="Repository & Branch")
top_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
for c in range(0, 6):
    top_frame.grid_columnconfigure(c, weight=1)

ttk.Label(top_frame, text="Repository:").grid(row=0, column=0, sticky="w", padx=(6, 6), pady=6)
repo_combo = ttk.Combobox(top_frame, textvariable=repo_var, values=find_git_repos(), width=50, state="readonly")
repo_combo.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=6)
repo_combo.bind("<<ComboboxSelected>>", on_repo_changed)

ttk.Label(top_frame, text="Search:").grid(row=0, column=2, sticky="e", padx=(6, 6), pady=6)
search_entry = ttk.Entry(top_frame, textvariable=search_repo_var)
search_entry.grid(row=0, column=3, sticky="ew", padx=(0, 6), pady=6)
ttk.Button(top_frame, text="Search", command=refresh_repo_list).grid(row=0, column=4, sticky="w", padx=(0, 6), pady=6)

ttk.Label(top_frame, text="Current branch:").grid(row=1, column=0, sticky="w", padx=(6, 6), pady=6)
cur_branch_label = ttk.Label(top_frame, textvariable=current_branch, foreground=PRIMARY, font=("Segoe UI", 10, "bold"))
cur_branch_label.grid(row=1, column=1, sticky="w", padx=(0, 6), pady=6)

ttk.Label(top_frame, text="Select branch:").grid(row=2, column=0, sticky="w", padx=(6, 6), pady=6)
branch_combo = ttk.Combobox(top_frame, textvariable=branch_var, values=load_branches_from_config(), width=20, state="readonly")
branch_combo.grid(row=2, column=1, sticky="w", padx=(0, 6), pady=6)
branch_combo.bind("<<ComboboxSelected>>", on_branch_selected)

ttk.Button(top_frame, text="Git Pull (current)", command=git_pull_current).grid(row=2, column=2, sticky="w", padx=(6, 6), pady=6)

# XML path (auto)
ttk.Label(top_frame, text="XML path (auto):").grid(row=3, column=0, sticky="w", padx=(6, 6), pady=(6, 6))
xml_entry = ttk.Entry(top_frame, textvariable=xml_path_var, width=80, state="readonly")
xml_entry.grid(row=3, column=1, columnspan=4, sticky="ew", padx=(0, 6), pady=(6, 6))

# CSV & Actions
mid_frame = ttk.LabelFrame(root, text="CSV & Actions")
mid_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
for c in range(0, 6):
    mid_frame.grid_columnconfigure(c, weight=1)

ttk.Label(mid_frame, text="CSV file:").grid(row=0, column=0, sticky="w", padx=(6, 6), pady=6)
csv_entry = ttk.Entry(mid_frame, textvariable=csv_path_var)
csv_entry.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(0, 6), pady=6)
ttk.Button(mid_frame, text="Browse", command=browse_csv).grid(row=0, column=4, sticky="w", padx=(0, 6), pady=6)
ttk.Button(mid_frame, text="Validate CSV headers", command=validate_csv_headers).grid(row=0, column=5, sticky="w", padx=(0, 6), pady=6)

log_chk = ttk.Checkbutton(mid_frame, text="Enable logging", variable=logging_enabled)
log_chk.grid(row=1, column=0, sticky="w", padx=(6, 6), pady=(0, 6))

ttk.Button(mid_frame, text="Validate", command=start_validation_thread).grid(row=1, column=1, sticky="w", padx=(0, 6), pady=(0, 6))
ttk.Button(mid_frame, text="Generate switch details", command=generate_switch_details).grid(row=1, column=2, sticky="w", padx=(0, 6), pady=(0, 6))
ttk.Button(mid_frame, text="Clear & Pull", command=clear_results_and_pull).grid(row=1, column=3, sticky="w", padx=(0, 6), pady=(0, 6))

# Results Table
results_frame = ttk.LabelFrame(root, text="Results")
results_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=(6, 6))
results_frame.grid_columnconfigure(0, weight=1)
results_frame.grid_rowconfigure(0, weight=1)

results_headers = ["ADO Reference", "Release", "Switch Name", "Divisions", "Value", "Status", "GitXmlValue", "MatchedFiles"]

tree_container = ttk.Frame(results_frame)
tree_container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
tree_container.grid_columnconfigure(0, weight=1)
tree_container.grid_rowconfigure(0, weight=1)

results_tree = ttk.Treeview(tree_container, columns=results_headers, show="headings")
for h in results_headers:
    results_tree.heading(h, text=h)
    w = 140
    if h in ("Status", "StatusColor"): w = 110
    if h in ("GitXmlValue",): w = 200
    if h in ("MatchedFiles",): w = 260
    results_tree.column(h, width=w, anchor="w")

# Tag colors on light background
results_tree.tag_configure("ok", foreground=GOOD)
results_tree.tag_configure("fail", foreground=BAD)

# Scrollbars for Treeview
tree_vsb = ttk.Scrollbar(tree_container, orient="vertical", command=results_tree.yview)
tree_hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=results_tree.xview)
results_tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)

results_tree.grid(row=0, column=0, sticky="nsew")
tree_vsb.grid(row=0, column=1, sticky="ns")
tree_hsb.grid(row=1, column=0, sticky="ew")

# Consoles: Git & Validation progress
console_frame = ttk.LabelFrame(root, text="Consoles")
console_frame.grid(row=4, column=0, sticky="nsew", padx=12, pady=(6, 12))
console_frame.grid_columnconfigure(0, weight=1)
console_frame.grid_columnconfigure(1, weight=1)
console_frame.grid_rowconfigure(1, weight=1)

ttk.Label(console_frame, text="Git progress").grid(row=0, column=0, sticky="w", padx=6, pady=(6, 0))
ttk.Label(console_frame, text="Validation progress").grid(row=0, column=1, sticky="w", padx=6, pady=(6, 0))

# Git output box with scrollbars
git_container = ttk.Frame(console_frame)
git_container.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
git_container.grid_columnconfigure(0, weight=1)
git_container.grid_rowconfigure(0, weight=1)

git_box = tk.Text(git_container, height=12, bg=TEXT_BG, fg=TEXT, insertbackground=TEXT, font=("Consolas", 10), relief="solid", bd=1)
git_vsb = ttk.Scrollbar(git_container, orient="vertical", command=git_box.yview)
git_hsb = ttk.Scrollbar(git_container, orient="horizontal", command=git_box.xview)
git_box.configure(yscrollcommand=git_vsb.set, xscrollcommand=git_hsb.set)
git_box.grid(row=0, column=0, sticky="nsew")
git_vsb.grid(row=0, column=1, sticky="ns")
git_hsb.grid(row=1, column=0, sticky="ew")
git_box.config(state="disabled")

# Progress box with scrollbars
progress_container = ttk.Frame(console_frame)
progress_container.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)
progress_container.grid_columnconfigure(0, weight=1)
progress_container.grid_rowconfigure(0, weight=1)

progress_box = tk.Text(progress_container, height=12, bg=TEXT_BG, fg=TEXT, insertbackground=TEXT, font=("Consolas", 10), relief="solid", bd=1)
prog_vsb = ttk.Scrollbar(progress_container, orient="vertical", command=progress_box.yview)
prog_hsb = ttk.Scrollbar(progress_container, orient="horizontal", command=progress_box.xview)
progress_box.configure(yscrollcommand=prog_vsb.set, xscrollcommand=prog_hsb.set)
progress_box.grid(row=0, column=0, sticky="nsew")
prog_vsb.grid(row=0, column=1, sticky="ns")
prog_hsb.grid(row=1, column=0, sticky="ew")
progress_box.config(state="disabled")

# Status line
status_bar = ttk.Frame(root)
status_bar.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 8))
status_bar.grid_columnconfigure(0, weight=1)
status_label = ttk.Label(status_bar, text="", foreground=SUBTEXT)
status_label.grid(row=0, column=0, sticky="w")

# ---------- Initialize ----------
repos = find_git_repos()
repo_combo['values'] = repos
if repos:
    repo_combo.set(repos[0])
    repo_var.set(repos[0])
    on_repo_changed()

branches = load_branches_from_config()
branch_combo["values"] = branches
if branches:
    branch_combo.set(branches[0])

info("Ready.")

root.mainloop()