# Windows Defender - Excluding a file
## False Positives

If using the provided compiled version, *usbtestnet.exe* Windows may prevent it from being run.

This is normal and depends on how up to date the Windows Defender patterns on your test system are.

Belcarra has submitted the binaries to Microsoft for vetting, and they have confirmed that 
the compiled exe (Nuitka compiler) is not a threat.

They add this there list of exclusions but that can take a while to propagate.

See below in *Submission* for more information on how to get your test system to get
the current malware definitions. N.b. once this is done it may take several hours
to complete.

---

## More information

https://medium.com/@markhank/how-to-stop-your-python-programs-being-seen-as-malware-bfd7eb407a7


https://www.microsoft.com/en-us/wdsi/filesubmission


https://www.youtube.com/watch?v=9lD93k5kxtE


## Exclude a file from Windows Defender

1. Open Windows Security by clicking on the Start menu and typing "Windows Security".
2. Click on "Virus & threat protection" in the left sidebar.
3. Scroll down and click on "Manage settings" under the "Virus & threat protection settings" section.
4. Scroll down to the "Exclusions" section and click on "Add or remove exclusions".
5. Click on "Add an exclusion" and select "File".
6. Browse to the file you want to exclude, select it, and click "Open".
7. The file will now be excluded from Windows Defender scans.


## Group Policy

Using Group Policy (Windows 10 Pro, Enterprise, or Education editions)

Press Win + R to open the Run dialog box. Type gpedit.msc and press Enter to open the Local Group Policy Editor. Navigate to Computer Configuration ->
Administrative Templates -> Windows Components -> Windows Defender Antivirus. Double-click on the policy named "Turn off Windows Defender Antivirus" on the
right pane. Select the Enabled option. Click Apply and then "OK."`:x


## Submission

'''
usbtestnet.exeSubmission ID: aaaeea06-34bb-46c3-ba68-f55affd2e880Status: CompletedSubmitted by: sl@belcarra.comSubmitted: Jun 16, 2025 12:49:40 AMUser Opinion: Incorrect detectionAnalyst comments:

At this time, the submitted files do not meet our criteria for malware or potentially unwanted applications. The detection has been removed. Please follow the steps below to clear cached detections and obtain the latest malware definitions.

1. Open command prompt as administrator and change directory to c:\Program Files\Windows Defender
2. Run “MpCmdRun.exe -removedefinitions -dynamicsignatures”
3. Run "MpCmdRun.exe -SignatureUpdate"

Alternatively, the latest definition is available for download here: https://docs.microsoft.com/microsoft-365/security/defender-endpoint/manage-updates-baselines-microsoft-defender-antivirus

## Typical Microsoft response

```
Thank you for contacting Microsoft.

Click here for more information
Thank you for your submission. To provide feedback about your submission experience to the Microsoft Defender team, click here. Please note that providing feedback will not open a new case or change a determination. To request further clarification on a file determination, please create a new submission
'''

