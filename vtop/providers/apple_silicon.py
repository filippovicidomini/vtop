"""
Apple Silicon (M-series) system provider.
"""

import os
import glob
import subprocess
from subprocess import PIPE
import plistlib
from typing import Dict, Any, Optional, List, Tuple
from .base import SystemProvider
from ..parsers import parse_thermal_pressure, parse_cpu_metrics, parse_gpu_metrics


class AppleSiliconProvider(SystemProvider):
    """
    Provider for Apple Silicon (M1, M2, M3, M4) Macs.
    
    Uses powermetrics for detailed per-core CPU/GPU monitoring,
    power consumption, and thermal data.
    """
    
    def __init__(self):
        self._soc_info_cache = None
    
    def get_soc_info(self) -> Dict[str, Any]:
        """Get Apple Silicon SoC information."""
        if self._soc_info_cache:
            return self._soc_info_cache
        
        cpu_info_dict = self._get_cpu_info()
        core_counts_dict = self._get_core_counts()
        
        try:
            e_core_count = core_counts_dict["hw.perflevel1.logicalcpu"]
            p_core_count = core_counts_dict["hw.perflevel0.logicalcpu"]
        except:
            e_core_count = "?"
            p_core_count = "?"
        
        soc_info = {
            "name": cpu_info_dict["machdep.cpu.brand_string"],
            "core_count": int(cpu_info_dict["machdep.cpu.core_count"]),
            "cpu_max_power": None,
            "gpu_max_power": None,
            "cpu_max_bw": None,
            "gpu_max_bw": None,
            "e_core_count": e_core_count,
            "p_core_count": p_core_count,
            "gpu_core_count": self._get_gpu_cores()
        }
        
        # Set TDP based on chip model
        self._set_power_limits(soc_info)
        self._set_bandwidth_limits(soc_info)
        
        self._soc_info_cache = soc_info
        return soc_info
    
    def supports_powermetrics(self) -> bool:
        """Apple Silicon supports powermetrics."""
        return True
    
    def start_monitoring(self, timecode: str, interval: int) -> subprocess.Popen:
        """Start powermetrics monitoring process."""
        # Clean up old temp files
        for tmpf in glob.glob("/tmp/vtop_powermetrics*"):
            try:
                os.remove(tmpf)
            except:
                pass
        
        command = [
            "sudo", "nice", "-n", "10",
            "powermetrics",
            "--samplers", "cpu_power,gpu_power,thermal",
            "-o", f"/tmp/vtop_powermetrics{timecode}",
            "-f", "plist",
            "-i", str(interval)
        ]
        
        process = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        return process
    
    def get_metrics(self, timecode: str) -> Optional[Tuple[Dict, Dict, str, None, float]]:
        """Get metrics from powermetrics output."""
        path = f"/tmp/vtop_powermetrics{timecode}"
        data = None
        
        try:
            with open(path, 'rb') as fp:
                data = fp.read()
            data = data.split(b'\x00')
            powermetrics_parse = plistlib.loads(data[-1])
            
            thermal_pressure = parse_thermal_pressure(powermetrics_parse)
            cpu_metrics_dict = parse_cpu_metrics(powermetrics_parse)
            gpu_metrics_dict = parse_gpu_metrics(powermetrics_parse)
            timestamp = powermetrics_parse["timestamp"]
            
            return cpu_metrics_dict, gpu_metrics_dict, thermal_pressure, None, timestamp
        except Exception as e:
            # Try second-to-last entry if last one failed
            if data and len(data) > 1:
                try:
                    entry = data[-2]
                    if isinstance(entry, bytes) and len(entry) > 0:
                        powermetrics_parse = plistlib.loads(entry)
                        thermal_pressure = parse_thermal_pressure(powermetrics_parse)
                        cpu_metrics_dict = parse_cpu_metrics(powermetrics_parse)
                        gpu_metrics_dict = parse_gpu_metrics(powermetrics_parse)
                        timestamp = powermetrics_parse["timestamp"]
                        return cpu_metrics_dict, gpu_metrics_dict, thermal_pressure, None, timestamp
                except:
                    pass
            return None
    
    def cleanup(self, process: subprocess.Popen) -> None:
        """Terminate powermetrics process."""
        if process:
            try:
                process.terminate()
            except:
                pass
    
    # Helper methods
    
    def _get_cpu_info(self) -> Dict[str, str]:
        """Get CPU info from sysctl."""
        cpu_info = os.popen('sysctl -a | grep machdep.cpu').read()
        cpu_info_lines = cpu_info.split("\n")
        data_fields = ["machdep.cpu.brand_string", "machdep.cpu.core_count"]
        cpu_info_dict = {}
        
        for l in cpu_info_lines:
            for h in data_fields:
                if h in l:
                    value = l.split(":")[1].strip()
                    cpu_info_dict[h] = value
        
        return cpu_info_dict
    
    def _get_core_counts(self) -> Dict[str, int]:
        """Get E-core and P-core counts from sysctl."""
        cores_info = os.popen('sysctl -a | grep hw.perflevel').read()
        cores_info_lines = cores_info.split("\n")
        data_fields = ["hw.perflevel0.logicalcpu", "hw.perflevel1.logicalcpu"]
        cores_info_dict = {}
        
        for l in cores_info_lines:
            for h in data_fields:
                if h in l:
                    value = int(l.split(":")[1].strip())
                    cores_info_dict[h] = value
        
        return cores_info_dict
    
    def _get_gpu_cores(self) -> Any:
        """Get GPU core count from system_profiler."""
        try:
            cores = os.popen(
                "system_profiler -detailLevel basic SPDisplaysDataType | grep 'Total Number of Cores'"
            ).read()
            cores = int(cores.split(": ")[-1])
        except:
            cores = "?"
        return cores
    
    def _set_power_limits(self, soc_info: Dict[str, Any]) -> None:
        """Set max power based on chip model."""
        name = soc_info["name"]
        
        if name == "Apple M1 Max":
            soc_info["cpu_max_power"] = 30
            soc_info["gpu_max_power"] = 60
        elif name == "Apple M1 Pro":
            soc_info["cpu_max_power"] = 30
            soc_info["gpu_max_power"] = 30
        elif name == "Apple M1":
            soc_info["cpu_max_power"] = 20
            soc_info["gpu_max_power"] = 20
        elif name == "Apple M1 Ultra":
            soc_info["cpu_max_power"] = 60
            soc_info["gpu_max_power"] = 120
        elif name == "Apple M2":
            soc_info["cpu_max_power"] = 25
            soc_info["gpu_max_power"] = 15
        elif "M3" in name:
            soc_info["cpu_max_power"] = 30
            soc_info["gpu_max_power"] = 30
        elif "M4" in name:
            soc_info["cpu_max_power"] = 35
            soc_info["gpu_max_power"] = 35
        else:
            soc_info["cpu_max_power"] = 20
            soc_info["gpu_max_power"] = 20
    
    def _set_bandwidth_limits(self, soc_info: Dict[str, Any]) -> None:
        """Set max bandwidth based on chip model."""
        name = soc_info["name"]
        
        if name == "Apple M1 Max":
            soc_info["cpu_max_bw"] = 250
            soc_info["gpu_max_bw"] = 400
        elif name == "Apple M1 Pro":
            soc_info["cpu_max_bw"] = 200
            soc_info["gpu_max_bw"] = 200
        elif name == "Apple M1":
            soc_info["cpu_max_bw"] = 70
            soc_info["gpu_max_bw"] = 70
        elif name == "Apple M1 Ultra":
            soc_info["cpu_max_bw"] = 500
            soc_info["gpu_max_bw"] = 800
        elif name == "Apple M2":
            soc_info["cpu_max_bw"] = 100
            soc_info["gpu_max_bw"] = 100
        else:
            soc_info["cpu_max_bw"] = 70
            soc_info["gpu_max_bw"] = 70
