import streamlit as st
from git import Repo, GitCommandError
import pandas as pd
import os
import json
from datetime import datetime

# Load paths from config
CONFIG_FILE = 'merge_paths_config.json'

def load_paths(config_file):
    if not os.path.exists(config_file):
        return []
    with open(config_file, 'r') as f:
        return json.load(f).get("paths", [])

# UI
st.title("🔀 Git Merge Report Generator (Path-Specific)")

repo_path = st.text_input("📁 Repository Path", "")
branch_from = st.text_input("🔄 Merge From Branch", "")
branch_to = st.text_input("🔁 Merge To Branch", "")
start_date = st.date_input("📅 Start Date")
end_date = st.date_input("📅 End Date")

available_paths = load_paths(CONFIG_FILE)
selected_paths = st.multiselect("📂 Select Paths to Compare", available_paths)

if st.button("📊 Generate Merge Report"):
    if not os.path.isdir(repo_path):
        st.error("Invalid repository path.")
    elif not selected_paths:
        st.warning("Please select at least one path to compare.")
    else:
        try:
            repo = Repo(repo_path)
            if repo.bare:
                st.error("The repository is bare.")
            else:
                commits = list(repo.iter_commits(f'{branch_to}..{branch_from}'))
                filtered_commits = [
                    c for c in commits
                    if start_date <= datetime.fromtimestamp(c.committed_date).date() <= end_date
                ]

                report_data = []
                for commit in filtered_commits:
                    for file in commit.stats.files:
                        if any(file.startswith(path) for path in selected_paths):
                            object_name = os.path.basename(file)
                            report_data.append({
                                'Filename': file,
                                'Object Name': object_name,
                                'Commit Message': commit.message.strip(),
                                'Author': commit.author.name,
                                'Commit Hash': commit.hexsha
                            })

                if not report_data:
                    st.info("No changes found in the selected paths and date range.")
                else:
                    df = pd.DataFrame(report_data)
                    st.success(f"Found {len(df)} changes.")
                    st.dataframe(df)

                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name='merge_report_filtered.csv',
                        mime='text/csv'
                    )

        except GitCommandError as e:
            st.error(f"Git error: {e}")
        except Exception as e:
            st.error(f"Error: {e}")
