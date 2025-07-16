git reset --hard HEAD (command that is used to undo local changes to the state of a Git repo)
git reset --hard origin/Release_CCSX23.6_A
git switch Release_CCSX23.6_A (command allows you to switch your current HEAD branch)
git pull

git reset --hard HEAD^ && git reset --hard origin/Release_CCSX23.12

git config --global user.name abhinand.nj
git config --global user.email abhinand.nj@NewVoe.local
git clone http://abhinand.nj@10.78.192.254:8080/VFUK_SIEBEL -b SIEBELUPG_IP23.12_ONCCSX25.3

git config --global user.name nja
git config --global user.email abhinand.nj@vodafone.com


git commit -a -m "RELEASE:25.7 DETAILS:Read Me file change"
git push origin Release_CCSX23.6_A:refs/for/Release_CCSX23.6_A
git commit -a -m "RELEASE:CCSX23.5|JIRA:RTB-11155|QC:xxxx|CR:xxx|INC:xxx|ACTION:Modified by Pratyush| DETAILS:Prod issue fix"
git push origin 25.7:refs/for/25.7

----------------------------------------------

from datetime import date
today = date.today().strftime("%d %B %Y")
copy_label = tk.Label(root, text=f"© {today} Abhinand's Git Dashboard. All rights reserved.", fg="#888", bg="#1e1e1e", font=("Segoe UI", 9))
copy_label.pack(pady=(10, 5))

