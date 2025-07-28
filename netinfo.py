import subprocess
import ipaddress

class NetInfo:
    def __init__(self, device_ip, netmask='24'):
        self.device_ip = device_ip
        self.netmask = netmask
        self.adapter_name = None

    def get_name(self):
        # Only look it up if we haven't already (call again to refresh if needed)
        dev_net = ipaddress.ip_network(f"{self.device_ip}/{self.netmask}", strict=False)
        # Query all interface names and IPs
        cmd = [
            "powershell", "-Command",
            "Get-NetIPAddress | Where-Object {$_.AddressFamily -eq 'IPv4' -and $_.PrefixOrigin -ne 'WellKnown'} | "
            "Select-Object InterfaceAlias,IPAddress | Format-Table -HideTableHeaders"
        ]
        output = subprocess.check_output(cmd, encoding="utf-8", errors="ignore")
        for line in output.strip().splitlines():
            if not line.strip():
                continue
            # Split at last whitespace (interface names may have spaces!)
            if ' ' in line:
                iface, ip = line.rsplit(None, 1)
                try:
                    if ipaddress.ip_address(ip) in dev_net:
                        self.adapter_name = iface.strip()
                        return self.adapter_name
                except Exception:
                    continue
        self.adapter_name = None
        return None

    def get_stats(self):
        # If we don't know the interface name, try to get it
        if not self.adapter_name:
            if not self.get_name():
                return None
        # Query stats for the interface
        cmd = [
            "powershell", "-Command",
            f"Get-NetAdapterStatistics -Name \"{self.adapter_name}\" | ConvertTo-Csv -NoTypeInformation"
        ]
        try:
            output = subprocess.check_output(cmd, encoding="utf-8", errors="ignore")
            import csv
            import io
            reader = csv.DictReader(io.StringIO(output))
            stats = next(reader)
            sent = int(stats['SentBytes'])
            recv = int(stats['ReceivedBytes'])
            sent_packets = int(stats['SentUnicastPackets'])
            recv_packets = int(stats['ReceivedUnicastPackets'])
            dropped_sent = int(stats.get('OutboundDiscardedPackets', 0))
            dropped_recv = int(stats.get('InboundDiscardedPackets', 0))
            return (sent, recv, sent_packets, recv_packets, dropped_sent, dropped_recv)
        except Exception as e:
            # Adapter might be gone or stats not available, so reset and return None
            self.adapter_name = None
            return None

if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="NetInfo PowerShell-based demo")
    parser.add_argument("device_ip", help="Device IP address to find interface")
    args = parser.parse_args()

    netinfo = NetInfo(args.device_ip)
    print("Looking up interface for IP", args.device_ip)
    iface = netinfo.get_name()
    print("Interface found:", iface)
    if iface is None:
        print("Could not find interface in subnet for", args.device_ip)
    else:
        while True:
            stats = netinfo.get_stats()
            if stats is not None:
                sent, recv, sent_pkts, recv_pkts, dropped_sent, dropped_recv = stats
                print(
                    f"{iface}: bytes_sent={sent}, bytes_recv={recv}, "
                    f"packets_sent={sent_pkts}, packets_recv={recv_pkts}, "
                    f"dropped_sent={dropped_sent}, dropped_recv={dropped_recv}"
                )
            else:
                print("Could not get stats for", iface)
            time.sleep(1)

