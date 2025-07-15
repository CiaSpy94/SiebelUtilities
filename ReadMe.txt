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


git commit -a -m "RELEASE:CCSX23.6_A|JIRA:RTB-11155|QC:xxxx|CR:xxxx|INC:xxxx|ACTION:Modified by Pratyush| DETAILS:Prod issue fix"
git push origin Release_CCSX23.6_A:refs/for/Release_CCSX23.6_A
git commit -a -m "RELEASE:CCSX23.5|JIRA:RTB-11155|QC:xxxx|CR:xxx|INC:xxx|ACTION:Modified by Pratyush| DETAILS:Prod issue fix"
git push origin Release_CCSX23.5:refs/for/Release_CCSX23.5
