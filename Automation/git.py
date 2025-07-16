import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# ---------- Paths ----------
CURRENT_DIR = os.getcwd()
PARENT_DIR = os.path.dirname(CURRENT_DIR)

# ---------- UI Setup ----------
root = tk.Tk()
root.title("Git Actions Dashboard")
root.geometry("900x700")
root.configure(bg="#1e1e1e")

style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
style.configure("TButton", padding=6, font=("Segoe UI", 10), background="#00aaff", foreground="white")
style.map("TButton", background=[('active', '#007acc')])

# ---------- Repo Detection ----------
def find_git_repos():
    return [f for f in os.listdir(PARENT_DIR)
            if os.path.isdir(os.path.join(PARENT_DIR, f)) and
               os.path.isdir(os.path.join(PARENT_DIR, f, ".git"))]

# ---------- Current Branch ----------
def get_current_branch(repo_path):
    try:
        output = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo_path, stderr=subprocess.STDOUT, text=True)
        return output.strip()
    except subprocess.CalledProcessError:
        return "Unknown"

def update_current_branch_label():
    repo = repo_var.get()
    if repo:
        repo_path = os.path.join(PARENT_DIR, repo)
        current = get_current_branch(repo_path)
        current_branch_label.config(text=f"Current Branch: {current}")
        cleaned_branch = current.replace("SIEBELUPG_IP23.12_ONCCS_", "")
        branch_var.set(cleaned_branch)
    else:
        current_branch_label.config(text="Current Branch: N/A")
        branch_var.set("")

# ---------- Command Execution ----------
def run_git_command(cmd):
    repo = repo_var.get()
    branch = branch_var.get().strip()
    ado_ref = ado_var.get().strip()
    modified_by_val = modified_by.get().strip()
    ado_num_val = ado_num.get().strip()
    dq = '"'
    repo_path = os.path.join(PARENT_DIR, repo)

    if not repo:
        show_popup("Please select a repository.")
        return

    if cmd in ["switch", "reset", "commit", "push"] and not branch:
        show_popup("Please select or enter a branch name.")
        return

    confirm_msg = f"Confirm to run: {cmd} on branch {branch}" if branch else f"Confirm to run: {cmd}"
    if not messagebox.askyesno("Confirm Action", confirm_msg):
        return

    if cmd == "switch":
        command = ["git", "switch", f"SIEBELUPG_IP23.12_ONCCSX{branch}"]
    elif cmd == "reset":
        command = ["git", "reset", "--hard", f"origin/SIEBELUPG_IP23.12_ONCCSX{branch} && git pull"]
    elif cmd == "pull":
        command = ["git", "pull"]
    elif cmd == "status":
        command = ["git", "status"]
    elif cmd == "add":
        command = ["git", "add","*"]
    elif cmd == "commit":
        msg = commit_entry.get().strip()
        if not ado_ref:
            show_popup("❗ Please select an ADO Reference.")
            return
        if ado_ref == 'CR':
            commit_msg = f"{dq}RELEASE-SIEBELUPG_IP23.12_ONCCSX{branch}|JIRA:xxxx|QC:xxxx|CR:{ado_num_val}|INC:xxxxx|ACTION:Modified by {modified_by_val}|DETAILS: CR {ado_num_val} {msg}{dq}"
        else:
            commit_msg = f"{dq}RELEASE-SIEBELUPG_IP23.12_ONCCSX{branch}|JIRA:xxxx|QC:{ado_num_val}|CR:xxxxx|INC:xxxxx|ACTION:Modified by {modified_by_val}|DETAILS: BUG {ado_num_val} {msg}{dq}"
        command = ["git", "commit", "-a", "-m", commit_msg]
    elif cmd == "push":
        command = ["git", "push", "origin", f"SIEBELUPG_IP23.12_ONCCSX{branch}:refs/for/SIEBELUPG_IP23.12_ONCCSX{branch}"]
    else:
        return

    confirm_msg = f"Confirm to run: {' '.join(command)}"
    if not messagebox.askyesno("Confirm Action", confirm_msg):
        return

    formatted_command = ' '.join(command)
    show_output(f"> {formatted_command}\n\n⏳ Loading...", success=True)
    root.update_idletasks()  # Force UI refresh

    try:
        output = subprocess.check_output(formatted_command, cwd=repo_path, shell=True, stderr=subprocess.STDOUT, text=True)
        show_output(f"> {formatted_command}\n\n{output}", success=True)
    except subprocess.CalledProcessError as e:
        show_output(f"> {formatted_command}\n\n{e.output}", success=False)

    update_current_branch_label()


# ---------- Output Display ----------
def show_output(text, success=True):
    output_box.config(fg="green" if success else "red")
    output_box.delete(1.0, tk.END)
    output_box.insert(tk.END, text)

def show_popup(msg):
    status_label.config(text=msg)

# ---------- UI Components ----------
ttk.Label(root, text="Select Git Repository").pack()
repo_var = tk.StringVar()
repo_menu = ttk.Combobox(root, textvariable=repo_var, values=find_git_repos(), width=50)
repo_menu.pack()

current_branch_label = tk.Label(root, text="Current Branch: N/A", fg="#00ffcc", bg="#1e1e1e", font=("Segoe UI", 10, "bold"))
current_branch_label.pack()

repo_menu.bind("<<ComboboxSelected>>", lambda e: update_current_branch_label())

ttk.Label(root, text="Select Git Branch to perform Actions").pack()
branch_var = tk.StringVar()
branch_menu = ttk.Combobox(root, textvariable=branch_var, values=["25.1", "25.2A", "25.2B", "25.3", "25.4", "25.5", "25.6A", "25.6B", "25.7", "25.8", "25.9A", "25.9B", "25.10", "25.11", "25.12"], width=50)
branch_menu.pack()
branch_menu.set("25.8")

ttk.Label(root, text="Modified by").pack()
modified_by = ttk.Entry(root, width=50)
modified_by.pack()

ttk.Label(root, text="ADO Reference").pack()
ado_var = tk.StringVar()
ado_menu = ttk.Combobox(root, textvariable=ado_var, values=["BUG", "CR"], width=50)
ado_menu.pack()
ado_menu.set("BUG")

ttk.Label(root, text="ADO Number").pack()
ado_num = ttk.Entry(root, width=50)
ado_num.pack()

ttk.Label(root, text="Commit Message").pack()
commit_entry = ttk.Entry(root, width=50)
commit_entry.pack()

status_label = tk.Label(root, text="", fg="yellow", bg="#1e1e1e", font=("Segoe UI", 10))
status_label.pack()

button_frame = tk.Frame(root, bg="#1e1e1e")
button_frame.pack(pady=20)

actions = [
    ("Switch", "switch"),
    ("Reset", "reset"),
    ("Git Pull", "pull"),
    ("Git Status", "status"),
    ("Git Add", "add"),
    ("Git Commit", "commit"),
    ("Git Push", "push")
]

for label, cmd in actions:
    b = ttk.Button(button_frame, text=label, command=lambda c=cmd: run_git_command(c))
    b.pack(side=tk.LEFT, padx=5)

ttk.Label(root, text="Command Output").pack()
output_box = tk.Text(root, height=20, bg="#111", fg="#0f0", insertbackground="white", font=("Consolas", 10))
output_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

copy_label = tk.Label(root, text=f"© 2025 nja@vois Git Dashboard. All rights reserved.", fg="#888", bg="#1e1e1e", font=("Segoe UI", 9))
copy_label.pack(pady=(10, 5))

# ---------- Launch ----------
repos = find_git_repos()
if repos:
    repo_menu['values'] = repos
    repo_menu.set(repos[0])
    repo_var.set(repos[0])
    update_current_branch_label()
    
root.mainloop()