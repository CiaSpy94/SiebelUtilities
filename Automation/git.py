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
root.geometry("900x740")
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
    else:
        current_branch_label.config(text="Current Branch: N/A")

# ---------- Command Execution ----------
def run_git_command(cmd):
    repo = repo_var.get()
    branch = branch_var.get().strip()
    ado_ref = ado_var.get().strip()
    repo_path = os.path.join(PARENT_DIR, repo)

    if not repo:
        show_popup("❗ Please select a repository.")
        return

    need_branch = cmd in ["switch", "reset", "commit", "push"]
    if need_branch and not branch:
        show_popup("❗ Please enter or select a Git branch.")
        return

    if cmd == "switch":
        command = ["git", "switch", branch]
    elif cmd == "reset":
        command = ["git", "reset", "--hard", f"origin/{branch}", "&&", "git", "pull"]
    elif cmd == "pull":
        command = ["git", "pull"]
    elif cmd == "status":
        command = ["git", "status"]
    elif cmd == "add":
        command = ["git", "add", "*"]
    elif cmd == "commit":
        msg = commit_entry.get().strip()
        if not ado_ref:
            show_popup("❗ Please select an ADO Reference.")
            return
        commit_msg = f"{ado_ref}:RELEASE:{branch} {msg}"
        command = ["git", "commit", "-a", "-m", commit_msg]
    elif cmd == "push":
        command = ["git", "push", "origin", f"{branch}:{branch}"]
    else:
        return

    confirm_msg = f"Confirm to run: {' '.join(command)}"
    if not messagebox.askyesno("Confirm Action", confirm_msg):
        return

    try:
        output = subprocess.check_output(" ".join(command), cwd=repo_path, shell=True, stderr=subprocess.STDOUT, text=True)
        show_output(f"> {' '.join(command)}\n\n{output}", success=True)
        update_current_branch_label()
    except subprocess.CalledProcessError as e:
        show_output(f"> {' '.join(command)}\n\n{e.output}", success=False)

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

ttk.Label(root, text="Select or Enter Git Branch").pack()
branch_var = tk.StringVar()
branch_menu = ttk.Combobox(root, textvariable=branch_var, width=50)
branch_menu['values'] = [f"25.{i}" for i in range(1, 13)]
branch_menu.pack()
branch_menu.set("25.1")

ttk.Label(root, text="ADO Reference").pack()
ado_var = tk.StringVar()
ado_menu = ttk.Combobox(root, textvariable=ado_var, values=["BUG", "CR"], width=20)
ado_menu.pack()
ado_menu.set("BUG")

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
    ("Git Add *", "add"),
    ("Git Commit", "commit"),
    ("Git Push", "push")
]

for label, cmd in actions:
    b = ttk.Button(button_frame, text=label, command=lambda c=cmd: run_git_command(c))
    b.pack(side=tk.LEFT, padx=5)

ttk.Label(root, text="Command Output").pack()
output_box = tk.Text(root, height=20, bg="#111", fg="#0f0", insertbackground="white", font=("Consolas", 10))
output_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# ---------- Launch ----------
repos = find_git_repos()
if repos:
    repo_menu['values'] = repos
    repo_menu.set(repos[0])
    repo_var.set(repos[0])
    update_current_branch_label()

root.mainloop()