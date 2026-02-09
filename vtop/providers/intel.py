"""
Intel x86/x64 system provider.
"""

import os
import time
import psutil
from typing import Dict, Any, Optional, Tuple
from .base import SystemProvider


class IntelProvider(SystemProvider):
    """
    Provider for Intel x86/x64 CPUs on macOS.
    
    Uses psutil for CPU monitoring since powermetrics doesn't provide
    as much useful data for Intel CPUs. Limited power metrics available.
    """
    
    def __init__(self):
        self._soc_info_cache = None
        self._last_per_cpu = None
        self._last_timestamp = None
    
    def get_soc_info(self) -> Dict[str, Any]:
        """Get Intel CPU information."""
        if self._soc_info_cache:
            return self._soc_info_cache
        
        cpu_info_dict = self._get_cpu_info()
        core_count = psutil.cpu_count(logical=True)
        physical_count = psutil.cpu_count(logical=False) or core_count
        
        # Intel CPUs don't have E/P core distinction (or we can't easily detect it)
        # Treat all cores as P-cores for display purposes
        soc_info = {
            "name": cpu_info_dict.get("machdep.cpu.brand_string", "Intel CPU"),
            "core_count": core_count,
            "cpu_max_power": self._estimate_tdp(cpu_info_dict),
            "gpu_max_power": None,  # Intel integrated GPU power not easily available
            "cpu_max_bw": None,
            "gpu_max_bw": None,
            "e_core_count": 0,  # No E-cores on Intel (or not detectable)
            "p_core_count": core_count,
            "gpu_core_count": "?"
        }
        
        self._soc_info_cache = soc_info
        return soc_info
    
    def supports_powermetrics(self) -> bool:
        """Intel doesn't have useful powermetrics support."""
        return False
    
    def start_monitoring(self, timecode: str, interval: int) -> None:
        """No background process needed for Intel monitoring."""
        # Initialize per-cpu tracking for accurate measurements
        psutil.cpu_percent(percpu=True)  # First call returns 0, needed to initialize
        self._last_timestamp = time.time()
        return None
    
    def get_metrics(self, timecode: str) -> Optional[Tuple[Dict, Dict, str, None, float]]:
        """Get metrics using psutil."""
        try:
            timestamp = time.time()
            
            # Get per-core CPU usage
            per_cpu_percent = psutil.cpu_percent(percpu=True, interval=0.1)
            
            # Get CPU frequency info - macOS Intel often doesn't support per-core freq
            cpu_freq = psutil.cpu_freq(percpu=True)
            
            # Ensure cpu_freq is a list matching per_cpu_percent length
            if not cpu_freq or not isinstance(cpu_freq, list):
                # Fallback: use single frequency for all cores
                freq_all = psutil.cpu_freq() if not cpu_freq else cpu_freq
                if freq_all:
                    cpu_freq = [freq_all] * len(per_cpu_percent)
                else:
                    # No frequency data available at all
                    cpu_freq = [type('obj', (object,), {'current': 0})] * len(per_cpu_percent)
            elif len(cpu_freq) == 1 and len(per_cpu_percent) > 1:
                # Single frequency reported, replicate for all cores
                cpu_freq = cpu_freq * len(per_cpu_percent)
            
            # Build cpu_metrics dict in the expected format
            cpu_metrics = {
                "e_core": [],  # No E-cores
                "p_core": list(range(len(per_cpu_percent))),  # All cores are P-cores
                "cpu_W": 0.0,  # Power metrics not available without special tools
                "gpu_W": 0.0,
                "package_W": 0.0,
                "ane_W": 0.0,
            }
            
            # Add per-core metrics
            for i, (percent, freq) in enumerate(zip(per_cpu_percent, cpu_freq)):
                freq_mhz = int(getattr(freq, 'current', 0))
                cpu_metrics[f"P-Cluster{i}_active"] = int(percent)
                cpu_metrics[f"P-Cluster{i}_freq_Mhz"] = freq_mhz
            
            # Calculate cluster averages (treating all cores as one cluster)
            if per_cpu_percent:
                cpu_metrics["P-Cluster_active"] = int(sum(per_cpu_percent) / len(per_cpu_percent))
                avg_freq = sum(int(getattr(f, 'current', 0)) for f in cpu_freq) / len(cpu_freq)
                cpu_metrics["P-Cluster_freq_Mhz"] = int(avg_freq)
            else:
                cpu_metrics["P-Cluster_active"] = 0
                cpu_metrics["P-Cluster_freq_Mhz"] = 0
            
            # GPU metrics - minimal since integrated Intel GPU monitoring is limited
            gpu_metrics = {
                "freq_MHz": 0,  # Not easily accessible
                "active": 0,    # Not easily accessible
            }
            
            # Thermal pressure
            thermal_pressure = self._get_thermal_status()
            
            self._last_timestamp = timestamp
            
            return cpu_metrics, gpu_metrics, thermal_pressure, None, timestamp
            
        except Exception as e:
            print(f"Error getting Intel metrics: {e}")
            return None
    
    def cleanup(self, process: Any) -> None:
        """No cleanup needed for Intel monitoring."""
        pass
    
    # Helper methods
    
    def _get_cpu_info(self) -> Dict[str, str]:
        """Get CPU info from sysctl."""
        cpu_info = os.popen('sysctl -a | grep machdep.cpu').read()
        cpu_info_lines = cpu_info.split("\n")
        data_fields = [
            "machdep.cpu.brand_string",
            "machdep.cpu.core_count",
            "machdep.cpu.model",
            "machdep.cpu.family"
        ]
        cpu_info_dict = {}
        
        for l in cpu_info_lines:
            for h in data_fields:
                if h in l:
                    value = l.split(":")[1].strip()
                    cpu_info_dict[h] = value
        
        return cpu_info_dict
    
    def _estimate_tdp(self, cpu_info: Dict[str, str]) -> Optional[int]:
        """
        Estimate TDP based on CPU model.
        This is a rough approximation.
        """
        brand = cpu_info.get("machdep.cpu.brand_string", "").lower()
        
        # Common Intel Mac TDP ranges
        if "i9" in brand:
            return 45  # Typical for mobile i9
        elif "i7" in brand:
            return 35  # Typical for mobile i7
        elif "i5" in brand:
            return 28  # Typical for mobile i5
        elif "i3" in brand:
            return 15
        elif "xeon" in brand:
            return 65  # Could be higher, but conservative estimate
        else:
            return 25  # Generic estimate
    
    def _get_thermal_status(self) -> str:
        """
        Try to get thermal status.
        Intel Macs have less detailed thermal info exposed.
        """
        try:
            # Try to get thermal level from sysctl
            result = os.popen('sysctl machdep.xcpm.cpu_thermal_level 2>/dev/null').read()
            if result:
                level = result.split(":")[-1].strip()
                return f"Thermal Level {level}"
        except:
            pass
        
        # Check CPU temperature if available (requires additional tools usually)
        # For now, return nominal
        return "Nominal"
    
    def get_architecture_name(self) -> str:
        """Return Intel-specific name."""
        return "Intel x86_64"
