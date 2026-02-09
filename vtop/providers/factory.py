"""
Factory for detecting and creating the appropriate system provider.
"""

import os
import platform
from typing import Optional
from .base import SystemProvider
from .apple_silicon import AppleSiliconProvider
from .intel import IntelProvider


def detect_architecture() -> str:
    """
    Detect the system architecture.
    
    Returns:
        str: 'apple_silicon', 'intel', or 'unknown'
    """
    try:
        # Check if running on macOS
        if platform.system() != "Darwin":
            return "unknown"
        
        # Get CPU brand string from sysctl
        result = os.popen('sysctl -n machdep.cpu.brand_string 2>/dev/null').read().strip()
        
        if "Apple" in result:
            return "apple_silicon"
        elif "Intel" in result:
            return "intel"
        
        # Fallback: check for Apple Silicon using uname
        machine = platform.machine().lower()
        if machine == "arm64" or machine == "aarch64":
            return "apple_silicon"
        elif machine in ["x86_64", "i386", "i686"]:
            return "intel"
            
    except Exception as e:
        print(f"Warning: Could not detect architecture: {e}")
    
    return "unknown"


def get_system_provider(force: Optional[str] = None) -> SystemProvider:
    """
    Get the appropriate system provider for the current architecture.
    
    Args:
        force: Optional architecture override ('apple_silicon', 'intel')
               Useful for testing or manual selection.
    
    Returns:
        SystemProvider: Instance of the appropriate provider
        
    Raises:
        RuntimeError: If architecture cannot be detected or is unsupported
    """
    arch = force if force else detect_architecture()
    
    if arch == "apple_silicon":
        return AppleSiliconProvider()
    elif arch == "intel":
        return IntelProvider()
    else:
        raise RuntimeError(
            f"Unsupported or unknown architecture: {arch}\n"
            f"vtop currently supports Apple Silicon and Intel CPUs on macOS.\n"
            f"Detected system: {platform.system()} {platform.machine()}"
        )


def list_supported_architectures() -> list:
    """
    List all supported architectures.
    
    Returns:
        List[str]: Names of supported architectures
    """
    return ["apple_silicon", "intel"]
