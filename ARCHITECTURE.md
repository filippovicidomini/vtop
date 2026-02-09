# Architecture Guide

This document explains vtop's architecture and how to add support for new CPU architectures.

## Overview

vtop uses a **provider pattern** to support multiple CPU architectures (Apple Silicon, Intel, etc.). Each architecture has its own provider class that implements a common interface.

## Provider Architecture

### Core Components

1. **SystemProvider (base.py)**: Abstract base class defining the interface
2. **Concrete Providers**: Architecture-specific implementations
   - `AppleSiliconProvider` - M1/M2/M3/M4 chips
   - `IntelProvider` - Intel x86_64 CPUs
3. **Factory (factory.py)**: Detects architecture and returns appropriate provider
4. **Main Application (vtop.py)**: Uses provider interface, architecture-agnostic

### Provider Interface

Every provider must implement these methods:

```python
class SystemProvider(ABC):
    
    @abstractmethod
    def get_soc_info(self) -> Dict[str, Any]:
        """
        Returns CPU/SoC information:
        - name: str - CPU name
        - core_count: int - total cores
        - e_core_count: int - efficiency cores (0 if N/A)
        - p_core_count: int - performance cores (or all cores)
        - gpu_core_count: int|str - GPU cores or "?"
        - cpu_max_power: Optional[int] - max CPU watts
        - gpu_max_power: Optional[int] - max GPU watts
        - cpu_max_bw: Optional[int] - max bandwidth
        - gpu_max_bw: Optional[int] - max bandwidth
        """
        pass
    
    @abstractmethod
    def supports_powermetrics(self) -> bool:
        """Returns True if detailed power metrics available."""
        pass
    
    @abstractmethod
    def start_monitoring(self, timecode: str, interval: int):
        """
        Start monitoring process.
        
        Args:
            timecode: Unique session identifier
            interval: Sampling interval in milliseconds
            
        Returns:
            Process handle or None
        """
        pass
    
    @abstractmethod
    def get_metrics(self, timecode: str) -> Optional[Tuple[Dict, Dict, str, None, float]]:
        """
        Get current metrics.
        
        Returns:
            (cpu_metrics, gpu_metrics, thermal_pressure, bandwidth, timestamp)
            or None if no data available.
            
        cpu_metrics format:
            {
                "e_core": [0, 1, 2, 3],  # E-core indices (or [])
                "p_core": [4, 5, 6, 7],  # P-core indices
                "E-Cluster{i}_active": 45,  # E-core usage %
                "E-Cluster{i}_freq_Mhz": 2064,  # E-core frequency
                "P-Cluster{i}_active": 78,  # P-core usage %
                "P-Cluster{i}_freq_Mhz": 3228,  # P-core frequency
                "P-Cluster_active": 65,  # Overall P-cluster %
                "P-Cluster_freq_Mhz": 3000,  # Avg P-cluster freq
                "E-Cluster_active": 40,  # Overall E-cluster % (if applicable)
                "E-Cluster_freq_Mhz": 2000,  # Avg E-cluster freq (if applicable)
                "cpu_W": 12.5,  # CPU power (watts)
                "gpu_W": 5.3,   # GPU power (watts)
                "package_W": 18.2,  # Total package power
                "ane_W": 0.0,   # Neural engine power (if applicable)
            }
            
        gpu_metrics format:
            {
                "freq_MHz": 1296,  # GPU frequency
                "active": 35,      # GPU usage %
            }
        """
        pass
    
    @abstractmethod
    def cleanup(self, process):
        """Clean up monitoring resources."""
        pass
```

## Adding a New Architecture

### Example: ARM Linux Support

Here's how you would add support for ARM-based Linux systems:

#### 1. Create the Provider

Create `vtop/providers/arm_linux.py`:

```python
"""
ARM Linux system provider.
"""

import psutil
import time
from typing import Dict, Any, Optional, Tuple
from .base import SystemProvider


class ARMLinuxProvider(SystemProvider):
    """Provider for ARM CPUs on Linux."""
    
    def __init__(self):
        self._soc_info_cache = None
    
    def get_soc_info(self) -> Dict[str, Any]:
        """Get ARM CPU information from /proc/cpuinfo."""
        if self._soc_info_cache:
            return self._soc_info_cache
        
        # Read /proc/cpuinfo
        cpu_model = "ARM CPU"
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        cpu_model = line.split(':')[1].strip()
                        break
        except:
            pass
        
        core_count = psutil.cpu_count(logical=True)
        
        soc_info = {
            "name": cpu_model,
            "core_count": core_count,
            "e_core_count": 0,  # Could detect if big.LITTLE
            "p_core_count": core_count,
            "gpu_core_count": "?",
            "cpu_max_power": None,  # Estimate or detect
            "gpu_max_power": None,
            "cpu_max_bw": None,
            "gpu_max_bw": None,
        }
        
        self._soc_info_cache = soc_info
        return soc_info
    
    def supports_powermetrics(self) -> bool:
        """ARM Linux doesn't have powermetrics."""
        return False
    
    def start_monitoring(self, timecode: str, interval: int):
        """Initialize monitoring using psutil."""
        psutil.cpu_percent(percpu=True)  # Prime the pump
        return None
    
    def get_metrics(self, timecode: str) -> Optional[Tuple[Dict, Dict, str, None, float]]:
        """Get metrics using psutil and /sys."""
        try:
            timestamp = time.time()
            per_cpu_percent = psutil.cpu_percent(percpu=True, interval=0.1)
            
            # Read CPU frequencies from /sys/devices/system/cpu/
            cpu_freqs = []
            for i in range(len(per_cpu_percent)):
                try:
                    with open(f'/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq', 'r') as f:
                        freq_khz = int(f.read().strip())
                        cpu_freqs.append(freq_khz // 1000)  # Convert to MHz
                except:
                    cpu_freqs.append(0)
            
            # Build metrics dict
            cpu_metrics = {
                "e_core": [],
                "p_core": list(range(len(per_cpu_percent))),
                "cpu_W": 0.0,
                "gpu_W": 0.0,
                "package_W": 0.0,
                "ane_W": 0.0,
            }
            
            for i, (percent, freq) in enumerate(zip(per_cpu_percent, cpu_freqs)):
                cpu_metrics[f"P-Cluster{i}_active"] = int(percent)
                cpu_metrics[f"P-Cluster{i}_freq_Mhz"] = freq
            
            cpu_metrics["P-Cluster_active"] = int(sum(per_cpu_percent) / len(per_cpu_percent))
            cpu_metrics["P-Cluster_freq_Mhz"] = int(sum(cpu_freqs) / len(cpu_freqs))
            
            gpu_metrics = {"freq_MHz": 0, "active": 0}
            thermal_pressure = "Nominal"
            
            return cpu_metrics, gpu_metrics, thermal_pressure, None, timestamp
        except Exception as e:
            print(f"Error getting ARM metrics: {e}")
            return None
    
    def cleanup(self, process):
        """No cleanup needed."""
        pass
    
    def get_architecture_name(self) -> str:
        return "ARM Linux"
```

#### 2. Update the Factory

Edit `vtop/providers/factory.py`:

```python
from .arm_linux import ARMLinuxProvider

def detect_architecture() -> str:
    """Detect the system architecture."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        result = os.popen('sysctl -n machdep.cpu.brand_string').read().strip()
        if "Apple" in result:
            return "apple_silicon"
        elif "Intel" in result:
            return "intel"
    
    elif system == "Linux":  # Linux
        machine = platform.machine().lower()
        if machine in ["arm64", "aarch64", "armv7l", "armv8"]:
            return "arm_linux"
        elif machine in ["x86_64", "i386", "i686"]:
            return "intel_linux"  # Could add separate provider
    
    return "unknown"

def get_system_provider(force: Optional[str] = None) -> SystemProvider:
    """Get the appropriate system provider."""
    arch = force if force else detect_architecture()
    
    if arch == "apple_silicon":
        return AppleSiliconProvider()
    elif arch == "intel":
        return IntelProvider()
    elif arch == "arm_linux":
        return ARMLinuxProvider()
    else:
        raise RuntimeError(f"Unsupported architecture: {arch}")
```

#### 3. Test

```bash
# Test on ARM Linux system
sudo vtop

# Or force the provider for testing
# (add --arch flag to vtop.py if needed)
python -m vtop.vtop --arch arm_linux
```

## Architecture-Specific Features

### Apple Silicon
- Full powermetrics support
- Per-core E/P distinction
- Detailed power metrics (CPU, GPU, ANE)
- Thermal pressure monitoring

### Intel macOS
- psutil-based monitoring
- No E/P core distinction
- Limited power metrics
- Basic thermal status

### Future: ARM Linux
- psutil + /sys filesystem
- Potential big.LITTLE detection
- RAPL power interface (on some systems)
- hwmon temperature sensors

## Key Design Principles

1. **Graceful Degradation**: If a metric isn't available, use 0 or "?" rather than crashing
2. **Consistent Interface**: All providers return the same data structure
3. **Architecture Detection**: Automatic, but allow manual override for testing
4. **Resource Cleanup**: Always implement cleanup() properly
5. **Error Handling**: Wrap system calls in try/except, return None on failure

## Testing Checklist

When adding a new provider:

- [ ] Detects architecture correctly
- [ ] Returns valid soc_info with all required keys
- [ ] get_metrics() returns correct format
- [ ] UI displays correctly (E-cores, P-cores, labels)
- [ ] Handles missing data gracefully
- [ ] cleanup() releases resources properly
- [ ] Works with/without sudo (if applicable)
- [ ] Tested on actual hardware
- [ ] Documentation updated

## Common Pitfalls

1. **Forgetting to initialize psutil**: First `cpu_percent()` call returns 0
2. **Type mismatches**: Ensure frequencies are int, not float
3. **Missing keys**: UI expects specific keys in metrics dict
4. **Process cleanup**: Always implement cleanup() to avoid zombie processes
5. **Platform-specific commands**: Wrap in try/except, check platform first

## Resources

- psutil documentation: https://psutil.readthedocs.io/
- Linux `/proc` and `/sys`: https://www.kernel.org/doc/Documentation/
- macOS sysctl: `man sysctl`, `sysctl -a`
- PowerMetrics: `sudo powermetrics --help`

## Questions?

Open an issue on GitHub or check existing provider implementations for examples.
