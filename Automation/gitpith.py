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

# ---------- Branch Detection ----------
def get_git_branches(repo_path):
    try:
        output = subprocess.check_output(['git', 'branch', '--all'],
                                         cwd=repo_path,
                                         stderr=subprocess.STDOUT,
                                         text=True)
        branches = [line.strip().replace('*', '').replace('remotes/origin/', '') for line in output.splitlines()]
        return list(set(filter(lambda b: b and "HEAD" not in b, branches)))
    except subprocess.CalledProcessError:
        return []

# ---------- Command Execution ----------
def run_git_command(cmd):
    repo = repo_var.get()
    branch = branch_var.get().strip()
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
        command = ["git", "switch", branch]
    elif cmd == "reset":
        command = ["git", "reset", "--hard", f"origin/{branch}"]
    elif cmd == "pull":
        command = ["git", "pull"]
    elif cmd == "status":
        command = ["git", "status"]
    elif cmd == "commit":
        msg = commit_entry.get()
        command = ["git", "commit", "-a", "-m", f"RELEASE:{branch} {msg}"]
    elif cmd == "push":
        command = ["git", "push", "origin", f"{branch}:{branch}"]
    else:
        return

    try:
        output = subprocess.check_output(command, cwd=repo_path, stderr=subprocess.STDOUT, text=True)
        show_output(f"> {' '.join(command)}\n\n{output}", success=True)
    except subprocess.CalledProcessError as e:
        show_output(f"> {' '.join(command)}\n\n{e.output}", success=False)

# ---------- Output Display ----------
def show_output(text, success=True):
    output_box.config(fg="green" if success else "red")
    output_box.delete(1.0, tk.END)
    output_box.insert(tk.END, text)

def show_popup(msg):
    status_label.config(text=msg)

def update_branches(*args):
    repo = repo_var.get()
    if repo:
        repo_path = os.path.join(PARENT_DIR, repo)
        branches = get_git_branches(repo_path)
        branch_menu['values'] = branches
        if branches:
            branch_menu.set(branches[0])

# ---------- UI Components ----------
ttk.Label(root, text="Select Git Repository").pack()
repo_var = tk.StringVar()
repo_menu = ttk.Combobox(root, textvariable=repo_var, values=find_git_repos(), width=50)
repo_menu.pack()
repo_menu.bind("<<ComboboxSelected>>", update_branches)

ttk.Label(root, text="Select or Enter Git Branch").pack()
branch_var = tk.StringVar()
branch_menu = ttk.Combobox(root, textvariable=branch_var, width=50)
branch_menu.pack()

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
if repo_menu['values']:
    repo_menu.set(repo_menu['values'][0])
    update_branches()

root.mainloop()