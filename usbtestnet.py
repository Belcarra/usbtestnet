# usb_net_test_harness.py
"""
USB/Network Device Test Harness

- Exercises a USB device by VID/PID, simulates replug (disable/enable), verifies status
- Checks device driver info and version
- Pings and HTTP GETs device at specified IP
- Logs network traffic counters if psutil is available
- Logs to file and console
"""

import argparse
import subprocess
import logging
import time
from time import time, sleep
import datetime
import re
import sys
import os
import shutil
import socket
import platform
import pythonping
import traceback

from netinfo import NetInfo

from version import __version__


try:
    import requests
except ImportError:
    print("This script requires the 'requests' library. Install with: pip install requests")
    sys.exit(1)

# Helper: run a command and return stdout
def run_cmd(cmd):
    try:
        logging.debug(f"Running command: {cmd}")
        output = subprocess.check_output(cmd, shell=True, encoding='utf-8', stderr=subprocess.STDOUT)
        return output
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e.output}")
        return ""

def osetup_logging(logfile):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y%m%d-%H:%M:%S',)
    # Console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    # File
    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def setup_console_logging():
    logger = logging.getLogger()
    logger.handlers = []
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y%m%d-%H:%M:%S',)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def add_file_logging(logfile):
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y%m%d-%H:%M:%S',)
    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


def find_device_id(vid, pid):
    search = f"USB\\VID_{vid.upper()}&PID_{pid.upper()}"
    output = run_cmd(f'devcon find \"{search}\"')
    logging.info(f"Searching for {search}")
    for line in output.splitlines():
        m = re.search(r'(USB\\VID_[A-F0-9]+&PID_[A-F0-9]+\\[^\s]+)', line, re.IGNORECASE)
        if m:
            device_id = m.group(1).replace('\\\\', '\\')
            logging.info(f"Found Device: {device_id}")
            return device_id
    logging.error(f"No matching device for VID:PID {vid}:{pid}")
    return None

def get_driver_info(device_id):
    output = run_cmd(f'devcon stack "{device_id}"')
    driver_info = []
    for line in output.splitlines():
        if 'Service Name' in line or 'Driver Node' in line or 'Driver' in line:
            driver_info.append(line.strip())
    if driver_info:
        logging.info("Driver stack info: " + " | ".join(driver_info))

    # Try PowerShell for driver version
    try:
        dev_id_last = device_id.split('\\')[-1]
        if sys.platform == 'cygwin':
            ps_cmd = (
                "Get-WmiObject Win32_PnPSignedDriver | "
                "Where-Object {\$_.DeviceID -like '*%s*'} | "
                "Select DeviceName, DriverVersion, DriverProviderName, DriverDate, InfName"
            ) % (dev_id_last)
        else:
            ps_cmd = (
                "Get-WmiObject Win32_PnPSignedDriver | "
                "Where-Object {$_.DeviceID -like '*%s*'} | "
                "Select DeviceName, DriverVersion, DriverProviderName, DriverDate, InfName"
            ) % (dev_id_last)

        run_str = 'powershell -Command "%s"' % (ps_cmd)
        output = run_cmd(f'powershell -Command "%s"' % (ps_cmd))

        tl = ("Driver WMI Info:\n" + output).split("\n")
        for s in tl:
            logging.info(s)
    except Exception as e:
        logging.exception(f"Error fetching driver version: {e}")
        print(traceback.print_exc())

def get_cpu_name():
    try:
        # Use PowerShell to get the Name field from Win32_Processor
        output = subprocess.check_output(
            ['powershell', '-Command', 'Get-WmiObject Win32_Processor | Select-Object -ExpandProperty Name'],
            encoding='utf-8', stderr=subprocess.DEVNULL)
        return output.strip()
    except Exception:
        return None


def is_device_enabled(tests_count, short_id, startTime, noisy ):
    # Use only up to VID_xxx&PID_xxx for devcon status
    output = run_cmd(f'devcon status "{short_id}"')
    if 'running' in output.lower():
        #logging.info(f"[{tests_count}:{time()-startTime:.0f}] {short_id}: USB Device Status Working")
        return True
    elif 'disabled' in output.lower():
        #logging.info(f"[{tests_count}:{time()-startTime:.0f}] {short_id}: Not Connected")
        sleep(1)
        if tests_count > 5 and noisy:
            print('\a')
        return False
    else:
        #logging.warning(f"{short_id}: Device status unknown")
        return False



def disable_enable_device(tests_count, short_id, action, startTime):
    if action not in ('disable', 'enable'):
        raise ValueError("action must be 'disable' or 'enable'")
    output = run_cmd(f'devcon {action} "{short_id}"')
    elapsed = time() - startTime
    logging.info(f"[{tests_count}:{elapsed:02.0f}] {short_id}: {action.title()}d")
    return output

import ipaddress


def wping_device(ip, timeout=0.5, count=1):
    ms = int(timeout * 1000)
    try:
        output = subprocess.check_output(
            ["ping", "-n", str(count), "-w", str(ms), ip], encoding='utf-8')
        if 'TTL=' in output or 'ttl=' in output:
            return True
    except Exception:
        pass
    return False

def ping_device(ip, timeout=0.2, count=1, tests_count=None):
    try:
        response = pythonping.ping(ip, count=count, timeout=timeout, verbose=False)
        #logging.warning(f"[{tests_count}] ping response: {response}")
        for r in response:
            if r.success:
                return True
        return False
    except Exception as e:
        logging.warning(f"[{tests_count}] pythonping failed: {e}")
        return False

def wget_device(tests_count, get_count, ip, iface, startTime, networkStartTime, timeout=2, count=None ):
    try:
        url = f"http://{ip}/"
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            logging.info(f"[{tests_count}:{time()-startTime:02.0f}:{time()-networkStartTime:.0f}] {iface}: HTTP GET success: {url} [{count}]")
            return True, r.text[:200]
        else:
            logging.warning(f"[{tests_count}:{time()-startTime:02.0f}:{time()-networkStartTime:.0f}] {iface}: HTTP GET failed: status {r.status_code} [{count}]")
    except Exception as e:
        logging.warning(f"[{tests_count}] HTTP GET failed: {e}")
    return False, None


# Identify Windows version (win10, win11, etc.)
def get_wintype():
    ver = platform.version()
    rel = platform.release()
    if rel == "10":
        # Windows 10 or 11
        build = int(platform.version().split('.')[2])
        return "win11" if build >= 22000 else "win10"
    return f"win{rel}"

def main():
    parser = argparse.ArgumentParser(description="USB/Network Device Test Harness")
    parser.add_argument("vid", nargs='?', help="USB Vendor ID (e.g., 15EC)")
    parser.add_argument("pid", nargs='?', help="USB Product ID (e.g., E021)")
    parser.add_argument("ip", nargs='?', help="Target IP address to ping")
    parser.add_argument("--logfile", default="usbtest.log", help="Log file name")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument("--wait-on-error", action="store_true", help="For for manual replug on error")
    parser.add_argument("--no-get", action="store_true", help="Disable the HTTP GET test")
    parser.add_argument("--no-auto-replug", action="store_true", help="Disable the automatic USB Disable")

    args = parser.parse_args()

    if args.version:
        print(__version__)
        exit(0)

    if not args.ip or not args.vid or not args.ip:
        parser.print_help()
        exit(0)

    setup_console_logging()

    if shutil.which("devcon") is None:
        logging.error("devcon.exe not found in PATH. Please install it from the Windows Driver Kit.")
        sys.exit(1)

    #setup_logging(args.logfile)

    logging.info(f"Starting test harness wait-on-error:{args.wait_on_error} no-auto-replug:{args.no_auto_replug} no-get:{args.no_get}")
    logging.info(f"VID: {args.vid}, PID: {args.pid}, IP: {args.ip}")


    hostname = socket.gethostname()

    wintype = get_wintype()
    archtype = platform.machine().lower()  # 'amd64', 'arm64', etc.
    archtype = platform.machine().lower()  # 'amd64', 'arm64', etc.
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    logfile = f"{hostname}-{wintype}-{archtype}-usbtest-{now}.log"
    logging.info(f"File logging starting: {logfile}")
    add_file_logging(logfile)
    logging.info(f"Test system hostname: {hostname}")

    win_ver = platform.platform()
    logging.info(f"Windows version: {win_ver}")

    processor = platform.processor()
    logging.info(f"Processor: {processor}")

    cpu_name = get_cpu_name()
    if cpu_name:
        logging.info(f"CPU name: {cpu_name}")

    if hasattr(platform, 'win32_ver'):
        win32_info = platform.win32_ver()
        logging.info(f"Windows detailed version: {win32_info}")

    device_id = find_device_id(args.vid, args.pid)
    if not device_id:
        sys.exit(1)


    get_driver_info(device_id)

    startTime = time()
    short_id = device_id.split('\\')[0] + '\\' + device_id.split('\\')[1]
    if not is_device_enabled(0, short_id, startTime, False):
        logging.info(f"{short_id}:Enabling device")
        disable_enable_device(0, short_id, "enable", startTime)
        sleep(2)
    if not is_device_enabled(0, short_id, startTime, False):
        logging.error(f"{short_id}: Could not be enabled.")
        sys.exit(1)

    # Main test loop

    tests_count = disabled_ok = disabled_notok = enabled_ok = enabled_notok = 0
    net_ok = net_notok = ping_fast = ping_slow = ping_notok = get_ok = get_notok = 0
    sent_packets_before = recv_packets_before = sent_bytes_before = recv_bytes_before = 0
    sent_packets_after = recv_packets_after = sent_bytes_after = recv_bytes_after = 0
    sent = recv = ''
    successFlag = True
    while True:
        netinfo = NetInfo(args.ip)
        tests_count += 1

        # provide a loop to break out of so we can log final stats 
        while True:

            bytes_sent, bytes_recv, packets_sent, packets_recv = (0,0,0,0)
            iface = None
            startTime = time()

            #logging.info(f"successflag:{successFlag}")
            # Wait for device to be disabled (up to 10s)
            if (not successFlag and args.wait_on_error) or args.no_auto_replug:
                logging.info(f"[{tests_count}:{time()-startTime:02.0f}] {short_id}: REPLUG DEVICE NOW")
                waitCount = 2000
            else:
                disable_enable_device(tests_count, short_id, "disable", startTime)
                waitCount = 20
            successFlag = False
            for check in range(waitCount):
                sleep(0.5)
                if not is_device_enabled(tests_count, short_id, startTime, args.wait_on_error ):
                    logging.info(f"[{tests_count}:{time()-startTime:02.0f}] {short_id}: USB Device Disconnected [{check+1}]")
                    disabled_ok += 1
                    break
            else:
                disabled_notok += 1
                logging.warning(f"[{tests_count}:{time()-startTime:02.0f}] {short_id}: USB Device did not disable after 10s.")
                break

            # too short (<2?) and the network interface does not get reset, stats will increment
            #sleep(6)

            # Wait for device to show up and be running
            disable_enable_device(tests_count, short_id, "enable", startTime)
            for attempt in range(20 if not args.no_auto_replug else 2000):
                sleep(0.5)
                if is_device_enabled(tests_count, short_id, startTime, args.wait_on_error):
                    enabled_ok += 1
                    logging.info(f"[{tests_count}:{time()-startTime:02.0f}] {short_id}: USB Device Connected [{attempt+1}]")
                    break
            else:
                enabled_notok += 1
                logging.error(f"{tests_count}:{time()-startTime:02.0f}] {short_id}: USB Device did not Connected after 10 seconds.")
                break

            # reset start time
            startTime = time()
            for i in range(4):
                stats = netinfo.get_stats()
                iface = netinfo.get_name()
                bytes_sent, bytes_recv, packets_sent, packets_recv, dropped_sent, dropped_recv = stats if stats else (0,0,0,0)
                if stats:
                    #logging.info(f"[{tests_count}:{time()-startTime:02.0f}] {iface}: {args.ip} " +
                    #        f"activity: {bytes_sent}:{bytes_recv} {packets_sent}:{packets_recv} {dropped_sent}:{dropped_recv} [{i+1}]")
                    net_ok += 1
                    break
            else:
                net_notok += 1
                logging.error(f"[{tests_count}:{time()-startTime:02.0f}] Network not found for {args.ip}.")
                break

            networkStartTime = time()

            # Ping until success, up to 10 tries
            startPingTime = time()
            for i in range(80):
                if ping_device(args.ip, timeout=0.2, count=1, tests_count=tests_count):
                    logging.info(f"[{tests_count}:{time()-startTime:02.0f}:{time()-networkStartTime:.0f}] {iface}: Ping {args.ip} [{i+1}]")
                    # Do two extra for confirmation
                    ping_device(args.ip, timeout=0.2, count=1)
                    ping_device(args.ip, timeout=0.2, count=1)
                    if time()-startTime < 30:
                        ping_fast += 1
                    else:
                        ping_slow += 1
                    break
                sleep(0.5)
                if i < 3 or i % 10 == 0:
                    stats = netinfo.get_stats()
                    iface = netinfo.get_name()
                    bytes_sent, bytes_recv, packets_sent, packets_recv, dropped_sent, dropped_recv = stats if stats else (0,0,0,0)
                    recv = f"{recv_packets_after-recv_packets_before}/{recv_bytes_after-recv_bytes_before} dropped:{dropped_sent}/{dropped_recv}"
                    logging.info(f"[{tests_count}:{time()-startTime:02.0f}:{time()-networkStartTime:02.0f}]" + 
                        f"activity: {bytes_sent}:{bytes_recv} {packets_sent}:{packets_recv} {dropped_sent}:{dropped_recv}",)
            else:
                ping_notok += 1
                logging.error(f"[{tests_count}:{time()-startTime:02.0f}:{time()-networkStartTime:.0f}] {iface} Ping to {args.ip} failed.")
                sleep(10)
                break


            # HTTP GET (wget equivalent)
            if not args.no_get:
                for i in range(1,3):
                    ok, content = wget_device(tests_count, i, args.ip, iface, startTime, networkStartTime, timeout=2, count=i)
                    if ok:
                        get_ok += 1
                        break
                    sleep(1)
                else:
                    get_notok += 1
                    logging.error(f"[{tests_count}:{time()-startTime:02.0f}] HTTP GET failed after 3 tries.")
                    break

            stats = netinfo.get_stats()
            iface = netinfo.get_name()
            bytes_sent, bytes_recv, packets_sent, packets_recv, dropped_sent, dropped_recv = stats if stats else (0,0,0,0)
            recv = f"{recv_packets_after-recv_packets_before}/{recv_bytes_after-recv_bytes_before} dropped:{dropped_sent}/{dropped_recv}"
            successFlag = True
            break

        logging_level = logging.info if successFlag else logging.error
        logging_level(f"[{tests_count}:{time()-startTime:02.0f}:{time()-networkStartTime:.0f}] {'OK' if successFlag else 'NOTOK'} " +
            f"disable: {disabled_ok}:{disabled_notok} " +
            f"enable: {enabled_ok}:{enabled_notok} " +
            f"net: {net_ok}:{net_notok} " +
            f"ping: {ping_fast}:{ping_slow}:{ping_notok} " +
            f"get: {get_ok}:{get_notok} " +
            f"activity: {bytes_sent}:{bytes_recv} {packets_sent}:{packets_recv} {dropped_sent}:{dropped_recv}",
            )
        logging.info('')
        if not args.no_auto_replug:
                sleep(2)

if __name__ == "__main__":
    main()
