"""
Abstract base class for system architecture providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple


class SystemProvider(ABC):
    """
    Abstract interface for system monitoring providers.
    
    Each architecture (Apple Silicon, Intel, ARM) implements this interface
    to provide CPU, GPU, and power metrics in a standardized format.
    """
    
    @abstractmethod
    def get_soc_info(self) -> Dict[str, Any]:
        """
        Get system-on-chip / CPU information.
        
        Returns:
            Dict containing:
                - name: str - CPU/SoC name
                - core_count: int - total number of cores
                - e_core_count: int - efficiency cores (0 if not applicable)
                - p_core_count: int - performance cores (or all cores for non-hybrid)
                - gpu_core_count: int or str - GPU core count or "?" if unknown
                - cpu_max_power: Optional[int] - max CPU power in watts
                - gpu_max_power: Optional[int] - max GPU power in watts
                - cpu_max_bw: Optional[int] - max CPU bandwidth
                - gpu_max_bw: Optional[int] - max GPU bandwidth
        """
        pass
    
    @abstractmethod
    def supports_powermetrics(self) -> bool:
        """
        Check if this provider supports powermetrics monitoring.
        
        Returns:
            bool: True if powermetrics is available for this architecture
        """
        pass
    
    @abstractmethod
    def start_monitoring(self, timecode: str, interval: int) -> Optional[Any]:
        """
        Start architecture-specific monitoring process.
        
        Args:
            timecode: Unique identifier for this monitoring session
            interval: Sampling interval in milliseconds
            
        Returns:
            Process handle or None if not applicable
        """
        pass
    
    @abstractmethod
    def get_metrics(self, timecode: str) -> Optional[Tuple[Dict, Dict, str, None, float]]:
        """
        Get current CPU, GPU, and thermal metrics.
        
        Args:
            timecode: Monitoring session identifier
            
        Returns:
            Tuple of (cpu_metrics, gpu_metrics, thermal_pressure, bandwidth, timestamp)
            or None if no data available yet. Format:
            
            cpu_metrics: Dict with keys like:
                - e_core: List[int] - E-core indices (empty if N/A)
                - p_core: List[int] - P-core indices (or all cores)
                - E-Cluster{i}_active: int - E-core usage percentage
                - E-Cluster{i}_freq_Mhz: int - E-core frequency
                - P-Cluster{i}_active: int - P-core usage percentage
                - P-Cluster{i}_freq_Mhz: int - P-core frequency
                - cpu_W: float - CPU power in watts
                - gpu_W: float - GPU power in watts
                - package_W: float - total package power
                - ane_W: float - ANE power (0 if N/A)
                
            gpu_metrics: Dict with keys:
                - freq_MHz: int - GPU frequency
                - active: int - GPU usage percentage
                
            thermal_pressure: str - thermal status
            bandwidth: None (reserved for future use)
            timestamp: float - unix timestamp
        """
        pass
    
    @abstractmethod
    def cleanup(self, process: Any) -> None:
        """
        Clean up monitoring resources.
        
        Args:
            process: Process handle returned by start_monitoring
        """
        pass
    
    def get_architecture_name(self) -> str:
        """
        Get human-readable architecture name.
        
        Returns:
            str: Architecture name (e.g., "Apple Silicon", "Intel x86")
        """
        return self.__class__.__name__.replace("Provider", "")
