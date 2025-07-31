# USB/Network Device Test Harness – Test Cycle Documentation

## Overview

This program is designed to **exercise, test, and log the behavior of a network device connected via USB** 
(using specified VID, PID, and IP address). It cycles the device (simulating physical replugging via software disable/enable), 
verifies driver status, and performs network connectivity tests, logging detailed results for each step.

This script can be run using Python if that is installed.

A Nuitka compiled version, *usbtestnet.exe* is also provided.

N.b. See the README-WindowsDefender.md for information on keeping WindowsDefender happy if using the *exe* version.

---
## Command Line Arguments

```
usage: usbtestnet.py [-h] [--logfile LOGFILE] [--version] [--wait-on-error]
                     [--no-get] [--no-auto-replug] [--fast]
                     [vid] [pid] [ip]

USB/Network Device Test Harness

positional arguments:
  vid                USB Vendor ID (e.g., 15EC)
  pid                USB Product ID (e.g., E021)
  ip                 Target IP address to ping

options:
  -h, --help         show this help message and exit
  --logfile LOGFILE  Log file name
  --version          Show version and exit
  --wait-on-error    For for manual replug on error
  --no-get           Disable the HTTP GET test
  --no-auto-replug   Disable the automatic USB Disable
  --fast             Fast
```
---

## Test Cycle Sequencing

Each **test cycle** performs the following sequence of steps:

1. **Disable the USB device** using `devcon`.
2. **Wait for device to disappear** from the system, polling up to 10 seconds.
3. **Enable the USB device** using `devcon`.
4. **Wait for device to be recognized and running**, polling up to 10 seconds.
5. **Wait for network interface to appear and be ready** (polling for up to 4 attempts).
6. **Ping the device IP address** repeatedly until it responds (up to 120 attempts, 0.5s interval).
7. **Perform an HTTP GET** (unless `--no-get` is specified), retrying up to 2 times.
8. **Record and log network interface statistics** (sent/received bytes and packets).
9. **Log the outcome** ("OK" or "NOTOK") and a summary of all sub-tests.

This sequence repeats continuously, producing a new log entry for each cycle.

If there is a failure the test cycle is terminated.

After each test cycle a summary line is logged showing *OK* or *NOTOK* and providing
a summary of success and failures for each test, and the network activity (bytes sent/received and
packets sent/received.)

---

## Step-by-Step: Each Test Step

### 1. **Disable Device**
- **How:** Calls `devcon disable` on the device’s short hardware ID.

### 2. **Wait for Device to Disappear**
- **How:** Repeatedly checks device status with `devcon status`.
- **Success:** `devcon` reports the device as “disabled”.
- **Failure:** Device remains “running” after timeout.

### 3. **Enable Device**
- **How:** Calls `devcon enable` on the device.

### 4. **Wait for Device to be Running**
- **How:** Polls `devcon status` up to 10 seconds.
- **Success:** Device is “running”.
- **Failure:** Device not “running” after timeout.

### 5. **Wait for Network Interface**
- **How:** Attempts up to 4 times to detect the expected network interface (by subnet matching to target IP) using the `NetInfo` class.
- **Success:** Network interface appears, stats can be retrieved.
- **Failure:** Network interface not found.

### 6. **Ping Device**
- **How:** Uses `pythonping` (or Windows `ping` as fallback) to send ICMP echo requests to the device IP.
- **Success:** Ping succeeds (any response) within 120 attempts (0.5s per attempt).
- **Failure:** No ping response after all attempts.

### 7. **HTTP GET (Optional)**
- **How:** Uses `requests.get()` to fetch `http://<device_ip>/` (unless `--no-get` is set).
- **Success:** HTTP 200 OK received.
- **Failure:** No HTTP response or error after 2 attempts.

### 8. **Network Traffic Counters**
- **How:** Uses the `NetInfo` class (PowerShell-based or psutil, as available) to record sent/received bytes and packets before and after the test.
- **Success/Failure:** Used for additional diagnostics; not directly a pass/fail test.

### 9. **Logging the Result**
- Logs summary line for each test cycle, showing:
    - `OK` if all major tests succeeded
    - `NOTOK` if any step failed
    - Per-test success/failure counts (disable, enable, net, ping, get)
    - Current network interface traffic statistics

---

## External Programs and Their Purpose

- **`devcon.exe`:**  
  - Used for device enumeration, status checks, enable/disable operations.  
  - Provided by the Windows Driver Kit (WDK).
  - a local copy of the x64 and amd64 devcon binary are provided

- **`powershell.exe`:**  
  - Used (via subprocess) to query network adapter statistics and driver info.

- **`ping` (Windows built-in) and `pythonping`:**  
  - Used for ICMP echo (ping) testing of the device’s IP address.

- **`requests` Python library:**  
  - Used for HTTP GET requests to the device web interface.

---

## Logfile Entries Per Test Cycle

Each cycle produces a series of log entries (with timestamps), typically including:

- Device enable/disable actions and elapsed time
- Device USB status checks (e.g., “USB Device Disconnected [N]”)
- Network interface status and statistics (activity: bytes/packets sent/received)
- Ping attempts and responses, with attempt count
- HTTP GET attempts and responses
- **Summary line** for the cycle, e.g.:

    ```
    20250731-14:16:16 [INFO] [149:11:4] OK disable: 149:0 enable: 149:0 net: 149:0 ping: 137:0:12 get: 137:0 activity: 12060:5022 107:11 0:0
    ```
    Where:
    - `[149:11:4]`: Test cycle 149, elapsed time 11 seconds
    - `OK` (or `NOTOK`): Overall test result
    - `disable: 149:0`: Success:fail count for device disable
    - `enable: 149:0`: Success:fail for enable
    - `net: 149:0`: Success:fail for network interface found
    - `ping: 137:0:12`: Fast:Slow:Fail results for ping
    - `get: 137:0`: Success:fail for HTTP GET
    - `activity: 12060:5022 107:11: Network bytes sent:received and packets sent:received

---

## Example Log Sequence
This shows three tests, fast, fail and fast.

```
20250731-14:13:40 [INFO] [147:00] USB\VID_15EC&PID_E021: Disabled
20250731-14:13:41 [INFO] [147:02] USB\VID_15EC&PID_E021: USB Device Disconnected [1]
20250731-14:13:41 [INFO] [147:02] USB\VID_15EC&PID_E021: Enabled
20250731-14:13:43 [INFO] [147:04] USB\VID_15EC&PID_E021: USB Device Connected [3]
20250731-14:13:55 [INFO] [147:12:05]activity: 11274:321 111:2 0:0
20250731-14:13:55 [INFO] [147:12:5] Ethernet 5: Ping 10.1.11.58 [2]
20250731-14:13:55 [INFO] [147:12:5] Ethernet 5: HTTP GET success: http://10.1.11.58/ [1]
20250731-14:13:59 [INFO] [147:16:9] OK disable: 147:0 enable: 147:0 net: 147:0 ping: 136:0:11 get: 136:0 activity: 13864:5343 128:13 0:0
20250731-14:13:59 [INFO]
20250731-14:14:02 [INFO] [148:00] USB\VID_15EC&PID_E021: Disabled
20250731-14:14:03 [INFO] [148:02] USB\VID_15EC&PID_E021: USB Device Disconnected [1]
20250731-14:14:03 [INFO] [148:02] USB\VID_15EC&PID_E021: Enabled
20250731-14:14:05 [INFO] [148:03] USB\VID_15EC&PID_E021: USB Device Connected [3]
20250731-14:14:16 [INFO] [148:12:05]activity: 498:0 6:0 0:0
20250731-14:14:21 [INFO] [148:17:10]activity: 498:0 6:0 0:0
20250731-14:14:27 [INFO] [148:22:15]activity: 498:0 6:0 0:0
20250731-14:14:36 [INFO] [148:32:25]activity: 498:0 6:0 0:0
20250731-14:14:48 [INFO] [148:43:36]activity: 498:0 6:0 0:0
20250731-14:14:59 [INFO] [148:54:48]activity: 498:0 6:0 0:0
20250731-14:15:10 [INFO] [148:66:59]activity: 498:0 6:0 0:0
20250731-14:15:22 [INFO] [148:77:70]activity: 498:0 6:0 0:0
20250731-14:15:33 [INFO] [148:88:82]activity: 498:0 6:0 0:0
20250731-14:15:45 [INFO] [148:100:93]activity: 498:0 6:0 0:0
20250731-14:15:51 [ERROR] [148:106:100] Ethernet 5 Ping to 10.1.11.58 failed.
20250731-14:16:01 [ERROR] [148:116:110] NOTOK disable: 148:0 enable: 148:0 net: 148:0 ping: 136:0:12 get: 136:0 activity: 498:0 6:0 0:0
20250731-14:16:01 [INFO]
20250731-14:16:03 [INFO] [149:00] USB\VID_15EC&PID_E021: Disabled
20250731-14:16:05 [INFO] [149:02] USB\VID_15EC&PID_E021: USB Device Disconnected [1]
20250731-14:16:05 [INFO] [149:02] USB\VID_15EC&PID_E021: Enabled
20250731-14:16:05 [INFO] [149:03] USB\VID_15EC&PID_E021: USB Device Connected [1]
20250731-14:16:12 [INFO] [149:06:0] Ethernet 5: Ping 10.1.11.58 [1]
20250731-14:16:12 [INFO] [149:06:0] Ethernet 5: HTTP GET success: http://10.1.11.58/ [1]
20250731-14:16:16 [INFO] [149:11:4] OK disable: 149:0 enable: 149:0 net: 149:0 ping: 137:0:12 get: 137:0 activity: 12060:5022 107:11 0:0
20250731-14:16:16 [INFO]
```

## Summary
This test harness provides a robust, automated sequence to simulate USB device unplug/plug, 
validate driver and network stack readiness, and exercise application-level connectivity, 
logging granular status at every stage to facilitate debugging and analysis.

