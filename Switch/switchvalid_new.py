import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import os
import xml.etree.ElementTree as ET
from datetime import datetime

def browse_csv():
    path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    csv_path.set(path)

def browse_xml_dir():
    path = filedialog.askdirectory()
    xml_dir.set(path)

def validate_csv_headers():
    try:
        with open(csv_path.get(), newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            required = ['ADO Reference', 'Release', 'Switch Name', 'Divisions', 'Value', 'Status']
            if all(h in headers for h in required):
                messagebox.showinfo("Validation", "CSV headers are valid.")
            else:
                messagebox.showerror("Validation", "CSV headers are invalid.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read CSV: {e}")

def linearize_xml(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        return ET.tostring(root, encoding='unicode', method='xml')
    except Exception:
        return ""

def extract_xpath_value(xml_text, tag):
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter(tag):
            return elem.text.strip().upper() if elem.text else ""
    except Exception:
        return ""
    return ""

def clear_previous_results():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    results_dir = os.path.join(base_dir, "results")
    deleted_files = 0

    for d in [logs_dir, results_dir]:
        if os.path.exists(d):
            for fname in os.listdir(d):
                fpath = os.path.join(d, fname)
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                        deleted_files += 1
                    except Exception:
                        pass
    messagebox.showinfo("Clear Results", f"Deleted {deleted_files} files from logs and results folders.")

def validate_data():
    try:
        # Prepare directories for logs and results
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(base_dir, "logs")
        results_dir = os.path.join(base_dir, "results")
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)

        # Read CSV into list of dicts
        with open(csv_path.get(), newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = reader.fieldnames

        xml_files = [f for f in os.listdir(xml_dir.get()) if f.endswith('.xml')]
        log_entries = []

        total = len(rows)
        validated_count = 0
        failed_count = 0

        progress_bar['maximum'] = total
        progress_bar['value'] = 0
        root.update_idletasks()

        for idx, row in enumerate(rows):
            switch_name = row['Switch Name'].strip().upper()
            value = row['Value'].strip().upper()
            status = "failed"
            xml_val = ""
            matched_files = [f for f in xml_files if switch_name in f.upper()]

            for xml_file in matched_files:
                xml_path_full = os.path.join(xml_dir.get(), xml_file)
                xml_text = linearize_xml(xml_path_full)
                ref_value = extract_xpath_value(xml_text, 'Reference')
                switch_xml_value = extract_xpath_value(xml_text, 'Switch')

                if log_enabled.get():
                    log_entries.append(
                        f"Row {idx+1}: ADO Reference={row['ADO Reference']}, Switch Name={switch_name}, Value={value}, "
                        f"XML File={xml_file}, Reference={ref_value}, Switch={switch_xml_value}"
                    )

                if switch_name == ref_value and value == switch_xml_value:
                    status = "Validated and matching with GIT"
                    validated_count += 1
                    break
                else:
                    xml_val = switch_xml_value

            if status != "Validated and matching with GIT":
                failed_count += 1

            row['Status'] = status if status == "Validated and matching with GIT" else f"failed - {xml_val}"

            # Update progress bar
            progress_bar['value'] = idx + 1
            root.update_idletasks()

        # Write result CSV to results directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = os.path.join(results_dir, f"result_{timestamp}.csv")
        with open(result_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        # Write log file only if enabled, to logs directory
        log_file_path = ""
        if log_enabled.get():
            log_file_path = os.path.join(logs_dir, f"log_{timestamp}.txt")
            with open(log_file_path, 'w', encoding='utf-8') as f:
                for entry in log_entries:
                    f.write(entry + "\n")

        progress_label.config(text=f"Validation completed. Result saved to {result_file}")

        # Show summary popup
        summary = f"Validation Summary:\n\nTotal Rows: {total}\nValidated: {validated_count}\nFailed: {failed_count}\n\nResult File:\n{result_file}"
        if log_enabled.get():
            summary += f"\nLog File:\n{log_file_path}"
        messagebox.showinfo("Validation Summary", summary)

    except Exception as e:
        messagebox.showerror("Error", f"Validation failed: {e}")

# GUI setup
root = tk.Tk()
root.title("CSV and XML Validator (No pandas)")
root.resizable(False, False)

main_font = ("Segoe UI", 11)
header_font = ("Segoe UI", 13, "bold")

# Section header
section_lbl = tk.Label(root, text="CSV & XML Validation Tool", font=header_font, fg="#2a4d69")
section_lbl.grid(row=0, column=0, columnspan=3, pady=(18, 10))

# CSV selection
tk.Label(root, text="Select the CSV:", font=main_font).grid(row=1, column=0, sticky='e', padx=(20,5), pady=5)
csv_path = tk.StringVar()
tk.Entry(root, textvariable=csv_path, width=40, font=main_font).grid(row=1, column=1, padx=5, pady=5)
tk.Button(root, text="Browse", font=main_font, command=browse_csv, width=12, bg="#4f81bd", fg="white").grid(row=1, column=2, padx=(5,20), pady=5)

# XML selection
tk.Label(root, text="Select switch XML path:", font=main_font).grid(row=2, column=0, sticky='e', padx=(20,5), pady=5)
xml_dir = tk.StringVar()
tk.Entry(root, textvariable=xml_dir, width=40, font=main_font).grid(row=2, column=1, padx=5, pady=5)
tk.Button(root, text="Browse", font=main_font, command=browse_xml_dir, width=12, bg="#4f81bd", fg="white").grid(row=2, column=2, padx=(5,20), pady=5)

# Logging checkbox
log_enabled = tk.BooleanVar(value=True)
tk.Checkbutton(root, text="Enable logging", variable=log_enabled, font=main_font).grid(row=3, column=1, sticky='w', padx=5, pady=5)

# Buttons row
btn_frame = tk.Frame(root)
btn_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0))
tk.Button(btn_frame, text="Validate CSV", font=main_font, command=validate_csv_headers, width=18, bg="#7fb800", fg="white").grid(row=0, column=0, padx=10)
tk.Button(btn_frame, text="Validate", font=main_font, command=validate_data, width=18, bg="#00796b", fg="white").grid(row=0, column=1, padx=10)
tk.Button(btn_frame, text="Clear Previous Results", font=main_font, command=clear_previous_results, width=18, bg="#d7263d", fg="white").grid(row=0, column=2, padx=10)

# Progress bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress_bar.grid(row=5, column=0, columnspan=3, pady=(30,5))

progress_label = tk.Label(root, text="", font=main_font, fg="#2a4d69")
progress_label.grid(row=6, column=0, columnspan=3, pady=(5,10))

root.mainloop()
