Create a python code with GUI for the below requirement without using pandas.

-there should be one field which should search and find git repo from the parent directory and label should be Please select a repository.
- below select repository it should show the current git branch which is available for the selected repository
-there should be 1 dropdown field with name as select branch. it should show values from a config file (sample vals 25.1,25.2 ...).

-On selecting the branch it should perform Git switch, reset and git pull.
command = ["git", "switch", f"SIEBELUPG_IP23.12_ONCCSX{branch}"]
command = ["git", "reset", "--hard", f"origin/SIEBELUPG_IP23.12_ONCCSX{branch} && git pull"]

- there should be a file browse control with label as Select the csv where we can select the csv file. the csv will have these headers ADO Reference,Release,Switch Name,Divisions,Value and Status.
- there should be a field called xml path which will be read only ans should point to build\refdata\FUT_Switch_Config path inside the git repository path and which will be the xml path to perform the compare.
- There should be a Validate CSV button which it should check for these headers are available on click.
- there should be Validate button. On click it should compare the records available in the csv line by line with xml files available in the  selected switch xml path.It should consider xmls which ontains the Switch Name in the name of the .xml file

comparison should happen as the below header to the xpth of the xml.and the csv value should convert first all to capital letters and then compare.
before reading the xml files linearize it and form a xml text like a single line and read the xpath

Switch Name - /SiebelMessage/ListOfVfFutSwitchIo/VfFutSwitchBc/Reference
Value - /SiebelMessage/ListOfVfFutSwitchIo/VfFutSwitchBc/Switch.

if the comparison results are inline then update the Status column in the csv file as validated and if there is any difference or error update the same as failed and append with the GIT xml value of the /SiebelMessage/ListOfVfFutSwitchIo/VfFutSwitchBc/Switch value.

After completing all the lies generate the new CSV with name a result appended with time stamp.

it should show the progress in the end of the popup section.

Log file should create with selected row from csv ,switch refernce, value and corresponsing xml files checked and the xpath values. 

add a check box in the UI for enabling the logging. Only create log file if it is checked

generate logs in the log path and result in the result path directly save them by creating a directory in the same path as the python code and if directory available then save inside that.

keep a progress section in the end showing the switch details from csv and the checked files progress with background in black and letters in green color. generate the complete code with progress section embedded in the main window

sample csv and xml attached.
