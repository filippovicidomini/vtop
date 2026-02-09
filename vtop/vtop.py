import time
import argparse
import os
import signal
import shutil
from collections import deque
from dashing import VSplit, HSplit, HGauge, HChart, Text
from .utils import *
from .providers import get_system_provider
import psutil

# Global flag for terminal resize
terminal_resized = False

def handle_resize(signum, frame):
    """Handle terminal resize signal"""
    global terminal_resized
    terminal_resized = True

# Register resize handler
signal.signal(signal.SIGWINCH, handle_resize)

parser = argparse.ArgumentParser(
    description='vtop: Advanced system monitor for macOS (Intel and Apple Silicon)')
parser.add_argument('--interval', type=int, default=1,
                    help='Display interval and sampling interval for powermetrics (seconds)')
parser.add_argument('--color', type=int, default=2,
                    help='Choose display color (0~8)')
parser.add_argument('--avg', type=int, default=30,
                    help='Interval for averaged values (seconds)')
parser.add_argument('--max_count', type=int, default=0,
                    help='Max show count to restart powermetrics')
args = parser.parse_args()


def get_disk_io():
    """Get disk I/O stats"""
    try:
        disk = psutil.disk_io_counters()
        return {"read_bytes": disk.read_bytes, "write_bytes": disk.write_bytes}
    except:
        return {"read_bytes": 0, "write_bytes": 0}


def get_network_io():
    """Get network I/O stats"""
    try:
        net = psutil.net_io_counters()
        return {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv}
    except:
        return {"bytes_sent": 0, "bytes_recv": 0}


def get_uptime():
    """Get system uptime"""
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        mins = int((uptime_seconds % 3600) // 60)
        if days > 0:
            return f"{days}d {hours}h {mins}m"
        elif hours > 0:
            return f"{hours}h {mins}m"
        else:
            return f"{mins}m"
    except:
        return "N/A"


def get_disk_usage():
    """Get disk usage for root"""
    try:
        disk = psutil.disk_usage('/')
        used_gb = disk.used / (1024**3)
        total_gb = disk.total / (1024**3)
        return f"{used_gb:.0f}/{total_gb:.0f}GB ({disk.percent}%)"
    except:
        return "N/A"


def format_speed(b):
    """Format bytes/s to human readable"""
    if b < 1024:
        return f"{b:.0f}B/s"
    elif b < 1024 * 1024:
        return f"{b/1024:.1f}KB/s"
    elif b < 1024 * 1024 * 1024:
        return f"{b/1024/1024:.1f}MB/s"
    else:
        return f"{b/1024/1024/1024:.1f}GB/s"


def get_battery_info():
    """Get battery information"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            plugged = battery.power_plugged
            secs_left = battery.secsleft
            
            status = "Charging" if plugged else "Discharging"
            if secs_left == psutil.POWER_TIME_UNLIMITED:
                time_str = "Unlimited"
            elif secs_left == psutil.POWER_TIME_UNKNOWN or secs_left < 0:
                time_str = "Calculating..."
            else:
                hours = secs_left // 3600
                mins = (secs_left % 3600) // 60
                time_str = f"{hours}h {mins}m left"
            
            return {
                "percent": percent,
                "status": status,
                "time": time_str,
                "plugged": plugged,
                "available": True
            }
        return {"available": False}
    except:
        return {"available": False}


def get_load_average():
    """Get system load average"""
    try:
        load1, load5, load15 = os.getloadavg()
        return f"{load1:.2f} / {load5:.2f} / {load15:.2f}"
    except:
        return "N/A"


def get_top_processes(n=3):
    """Get top N processes by CPU usage"""
    try:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                pinfo = p.info
                if pinfo['cpu_percent'] > 0:
                    procs.append(pinfo)
            except:
                pass
        
        procs.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return procs[:n]
    except:
        return []


def get_process_count():
    """Get process counts"""
    try:
        total = len(psutil.pids())
        running = len([p for p in psutil.process_iter(['status']) 
                      if p.info['status'] == psutil.STATUS_RUNNING])
        return f"{running} running / {total} total"
    except:
        return "N/A"


def get_disk_available():
    """Get actual available disk space on macOS (like Finder shows)"""
    try:
        import subprocess
        # Use df which shows available space correctly on APFS
        result = subprocess.run(['df', '-g', '/'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            # Format: Filesystem 1G-blocks Used Available Capacity
            total_gb = int(parts[1])
            used_gb = int(parts[2])
            available_gb = int(parts[3])
            pct = int(parts[4].replace('%', ''))
            return {
                "total": total_gb,
                "used": used_gb,
                "available": available_gb,
                "percent": pct
            }
    except:
        pass
    # Fallback to psutil
    try:
        disk = psutil.disk_usage('/')
        return {
            "total": disk.total / (1024**3),
            "used": disk.used / (1024**3),
            "available": disk.free / (1024**3),
            "percent": disk.percent
        }
    except:
        return {"total": 0, "used": 0, "available": 0, "percent": 0}


def get_memory_pressure():
    """Get macOS memory pressure level"""
    try:
        import subprocess
        result = subprocess.run(['memory_pressure'], capture_output=True, text=True, timeout=2)
        output = result.stdout
        # Parse: "System-wide memory free percentage: XX%"
        for line in output.split('\n'):
            if 'free percentage' in line.lower():
                pct = int(''.join(filter(str.isdigit, line.split(':')[-1])))
                if pct > 75:
                    return {"level": "Normal", "percent": 100 - pct, "color": "green"}
                elif pct > 50:
                    return {"level": "Moderate", "percent": 100 - pct, "color": "yellow"}
                else:
                    return {"level": "High", "percent": 100 - pct, "color": "red"}
    except:
        pass
    return {"level": "N/A", "percent": 0, "color": "gray"}


def main():
    print("\nVTOP - Advanced System Monitor for macOS")
    print("Run with: sudo vtop")
    print("\033[?25l")

    # Detect and initialize system provider
    try:
        provider = get_system_provider()
        print(f"Detected architecture: {provider.get_architecture_name()}")
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1

    # Get SOC/CPU info
    soc_info_dict = provider.get_soc_info()
    e_core_count = soc_info_dict["e_core_count"]
    p_core_count = soc_info_dict["p_core_count"]
    gpu_core_count = soc_info_dict["gpu_core_count"]
    chip_name = soc_info_dict["name"]

    # ============ ROW 1: CPU Cores (left) | GPU (right) ============
    e_core_charts = [HChart(title=f"E{i}", color=args.color) for i in range(e_core_count)] if e_core_count > 0 else []
    p_core_charts = [HChart(title=f"P{i}", color=args.color) for i in range(p_core_count)]

    # Layout CPU cores based on counts
    if e_core_count == 0:
        # Intel or non-hybrid: only P-cores
        if p_core_count <= 8:
            cpu_cores_col = VSplit(
                HSplit(*p_core_charts),
                title="CPU Cores",
                border_color=args.color
            )
        else:
            half = (p_core_count + 1) // 2
            cpu_cores_col = VSplit(
                HSplit(*p_core_charts[:half]),
                HSplit(*p_core_charts[half:]),
                title="CPU Cores",
                border_color=args.color
            )
    elif p_core_count <= 4:
        # Apple Silicon with few P-cores
        cpu_cores_col = VSplit(
            HSplit(*e_core_charts),
            HSplit(*p_core_charts),
            title="CPU Cores",
            border_color=args.color
        )
    else:
        # Apple Silicon with many P-cores
        half = (p_core_count + 1) // 2
        cpu_cores_col = VSplit(
            HSplit(*e_core_charts),
            HSplit(*p_core_charts[:half]),
            HSplit(*p_core_charts[half:]),
            title="CPU Cores",
            border_color=args.color
        )

    gpu_chart = HChart(title="GPU Usage", color=args.color)
    gpu_col = VSplit(
        gpu_chart,
        title="GPU",
        border_color=args.color
    )

    row1 = HSplit(cpu_cores_col, gpu_col)

    # ============ ROW 2: CPU Total (left) | RAM (right) ============
    cpu_total_chart = HChart(title="CPU Total", color=args.color)
    
    cpu_total_col = VSplit(
        cpu_total_chart,
        title="CPU Usage",
        border_color=args.color
    )

    ram_gauge = HGauge(title="RAM", val=0, color=args.color)
    swap_gauge = HGauge(title="Swap", val=0, color=args.color)
    ssd_gauge = HGauge(title="SSD", val=0, color=args.color)
    pressure_gauge = HGauge(title="Mem Pressure", val=0, color=args.color)

    ram_col = VSplit(
        ram_gauge,
        swap_gauge,
        ssd_gauge,
        pressure_gauge,
        title="Memory & Storage",
        border_color=args.color
    )

    row2 = HSplit(cpu_total_col, ram_col)

    # ============ ROW 3: Power CPU+GPU (left) | System (right) ============
    cpu_power_chart = HChart(title="CPU Power", color=args.color)
    gpu_power_chart = HChart(title="GPU Power", color=args.color)
    power_text = Text(text="", color=args.color)

    power_col = VSplit(
        cpu_power_chart,
        gpu_power_chart,
        power_text,
        title="Power",
        border_color=args.color
    )

    sys_text1 = Text(text="Loading...", color=args.color)
    
    sys_col = VSplit(
        sys_text1,
        title="System & Battery",
        border_color=args.color
    )

    row3 = HSplit(power_col, sys_col)

    # ============ MAIN UI ============
    # Build title based on architecture
    if e_core_count > 0:
        ui_title = f"{chip_name} ({e_core_count}E + {p_core_count}P + {gpu_core_count}GPU)"
    else:
        ui_title = f"{chip_name} ({p_core_count} cores)"
    
    ui = VSplit(
        row1,
        row2,
        row3,
        title=ui_title,
        border_color=args.color
    )

    cpu_max_power = soc_info_dict["cpu_max_power"] or 50  # Default if unknown
    gpu_max_power = soc_info_dict["gpu_max_power"] or 25  # Default if unknown

    cpu_peak_power = 0
    gpu_peak_power = 0
    package_peak_power = 0

    timecode = str(int(time.time()))
    monitor_process = provider.start_monitoring(timecode, interval=args.interval * 1000)

    def get_reading(wait=0.1):
        ready = provider.get_metrics(timecode=timecode)
        while not ready:
            time.sleep(wait)
            ready = provider.get_metrics(timecode=timecode)
        return ready

    ready = get_reading()
    last_timestamp = ready[-1]

    def get_avg(inlist):
        return sum(inlist) / len(inlist) if inlist else 0

    avg_cpu_power_list = deque([], maxlen=int(args.avg / args.interval))
    avg_gpu_power_list = deque([], maxlen=int(args.avg / args.interval))

    last_disk = get_disk_io()
    last_net = get_network_io()
    last_time = time.time()

    clear_console()

    # Get initial terminal size
    term_size = shutil.get_terminal_size()

    count = 0
    try:
        while True:
            global terminal_resized
            
            # Handle terminal resize - force dashing to recreate Terminal object
            if terminal_resized:
                terminal_resized = False
                clear_console()
                term_size = shutil.get_terminal_size()
                # Force dashing to recreate the Terminal object on next display
                if hasattr(ui, '_terminal'):
                    del ui._terminal
            
            if args.max_count > 0:
                if count >= args.max_count:
                    count = 0
                    provider.cleanup(monitor_process)
                    timecode = str(int(time.time()))
                    monitor_process = provider.start_monitoring(timecode, interval=args.interval * 1000)
                count += 1
                
            ready = provider.get_metrics(timecode=timecode)
            if ready:
                cpu_metrics, gpu_metrics, thermal_pressure, _, timestamp = ready

                if timestamp > last_timestamp:
                    last_timestamp = timestamp
                    current_time = time.time()
                    time_delta = max(current_time - last_time, 0.1)

                    # ===== ROW 1: CPU Cores + GPU =====
                    # Update E-cores if present
                    if e_core_count > 0:
                        for idx, i in enumerate(cpu_metrics["e_core"]):
                            active = cpu_metrics[f"E-Cluster{i}_active"]
                            freq = cpu_metrics[f"E-Cluster{i}_freq_Mhz"]
                            e_core_charts[idx].title = f"E{i} {active}% {freq}M"
                            e_core_charts[idx].append(active)

                    # Update P-cores (or all cores for Intel)
                    for idx, i in enumerate(cpu_metrics["p_core"]):
                        active = cpu_metrics[f"P-Cluster{i}_active"]
                        freq = cpu_metrics[f"P-Cluster{i}_freq_Mhz"]
                        core_label = f"P{i}" if e_core_count > 0 else f"C{i}"
                        p_core_charts[idx].title = f"{core_label} {active}% {freq}M"
                        p_core_charts[idx].append(active)

                    gpu_active = gpu_metrics["active"]
                    gpu_freq = gpu_metrics["freq_MHz"]
                    gpu_chart.title = f"GPU {gpu_active}% @ {gpu_freq}MHz"
                    gpu_chart.append(gpu_active)

                    # ===== ROW 2: CPU Total + RAM =====
                    p_active = cpu_metrics["P-Cluster_active"]
                    p_freq = cpu_metrics["P-Cluster_freq_Mhz"]
                    
                    if e_core_count > 0:
                        # Apple Silicon: show E and P clusters
                        e_active = cpu_metrics.get("E-Cluster_active", 0)
                        e_freq = cpu_metrics.get("E-Cluster_freq_Mhz", 0)
                        cpu_total = (e_active + p_active) // 2
                        cpu_total_chart.title = f"CPU {cpu_total}% | E:{e_active}%@{e_freq}M | P:{p_active}%@{p_freq}M"
                    else:
                        # Intel: just show overall CPU
                        cpu_total = p_active
                        cpu_total_chart.title = f"CPU {cpu_total}% @ {p_freq}MHz"
                    cpu_total_chart.append(cpu_total)

                    ram = get_ram_metrics_dict()
                    ram_gauge.title = f"RAM {ram['used_GB']}/{ram['total_GB']}GB ({ram['free_percent']}% used)"
                    ram_gauge.value = ram["free_percent"]

                    if ram["swap_total_GB"] > 0.1:
                        swap_gauge.title = f"Swap {ram['swap_used_GB']}/{ram['swap_total_GB']}GB"
                        swap_gauge.value = ram["swap_free_percent"] or 0
                    else:
                        swap_gauge.title = "Swap: inactive"
                        swap_gauge.value = 0

                    # SSD usage (using correct available space like Finder)
                    disk_info = get_disk_available()
                    ssd_used = disk_info["used"]
                    ssd_total = disk_info["total"]
                    ssd_avail = disk_info["available"]
                    ssd_pct = disk_info["percent"]
                    ssd_free_pct = 100 - ssd_pct
                    ssd_gauge.title = f"SSD {ssd_avail:.0f}GB free / {ssd_total:.0f}GB ({ssd_free_pct}% free)"
                    ssd_gauge.value = int(ssd_free_pct)

                    # Memory Pressure
                    mem_pressure = get_memory_pressure()
                    pressure_gauge.title = f"Pressure: {mem_pressure['level']} ({mem_pressure['percent']}%)"
                    pressure_gauge.value = mem_pressure["percent"]

                    # ===== ROW 3: Power + System =====
                    cpu_w = cpu_metrics["cpu_W"] / args.interval
                    gpu_w = cpu_metrics["gpu_W"] / args.interval
                    pkg_w = cpu_metrics["package_W"] / args.interval

                    if cpu_w > cpu_peak_power:
                        cpu_peak_power = cpu_w
                    if gpu_w > gpu_peak_power:
                        gpu_peak_power = gpu_w
                    if pkg_w > package_peak_power:
                        package_peak_power = pkg_w

                    avg_cpu_power_list.append(cpu_w)
                    avg_gpu_power_list.append(gpu_w)
                    avg_cpu_w = get_avg(avg_cpu_power_list)
                    avg_gpu_w = get_avg(avg_gpu_power_list)

                    cpu_power_pct = min(100, int(cpu_w / cpu_max_power * 100))
                    gpu_power_pct = min(100, int(gpu_w / gpu_max_power * 100))

                    cpu_power_chart.title = f"CPU: {cpu_w:.1f}W (avg:{avg_cpu_w:.1f} peak:{cpu_peak_power:.1f})"
                    cpu_power_chart.append(cpu_power_pct)

                    gpu_power_chart.title = f"GPU: {gpu_w:.1f}W (avg:{avg_gpu_w:.1f} peak:{gpu_peak_power:.1f})"
                    gpu_power_chart.append(gpu_power_pct)

                    power_text.text = f"Total: {pkg_w:.1f}W | Peak: {package_peak_power:.1f}W"

                    # System info
                    throttle = "OK" if thermal_pressure == "Nominal" else f"THROTTLE: {thermal_pressure}"

                    curr_disk = get_disk_io()
                    disk_read = (curr_disk["read_bytes"] - last_disk["read_bytes"]) / time_delta
                    disk_write = (curr_disk["write_bytes"] - last_disk["write_bytes"]) / time_delta
                    last_disk = curr_disk

                    curr_net = get_network_io()
                    net_recv = (curr_net["bytes_recv"] - last_net["bytes_recv"]) / time_delta
                    net_sent = (curr_net["bytes_sent"] - last_net["bytes_sent"]) / time_delta
                    last_net = curr_net

                    last_time = current_time

                    uptime = get_uptime()
                    load_avg = get_load_average()
                    
                    # System column: combined info
                    sys_info = f"""Thermal: {throttle} | Uptime: {uptime}
Load: {load_avg}
DISK  Read: {format_speed(disk_read)} | Write: {format_speed(disk_write)}
NET   Down: {format_speed(net_recv)} | Up: {format_speed(net_sent)}"""

                    sys_text1.text = sys_info

                    # Battery & Processes
                    battery = get_battery_info()
                    proc_count = get_process_count()
                    top_procs = get_top_processes(3)
                    
                    if battery["available"]:
                        batt_status = "on cable" if battery["plugged"] else "on battery"
                        batt_line = f"Battery: {battery['percent']:.0f}% {batt_status} ({battery['time']})"
                    else:
                        batt_line = "Desktop Mac (no battery)"
                    
                    procs_str = " | ".join([f"{p['name'][:8]}:{p['cpu_percent']:.0f}%" 
                                           for p in top_procs]) if top_procs else "(idle)"
                    
                    sys_info += f"\n{batt_line}\nProcs: {proc_count}\nTop: {procs_str}"
                    sys_text1.text = sys_info

                    ui.display()

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopping...")
        print("\033[?25h")
        provider.cleanup(monitor_process)

    return monitor_process


if __name__ == "__main__":
    monitor_process = main()
    # Cleanup is already handled in the KeyboardInterrupt handler
