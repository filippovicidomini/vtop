# vtop 🖥️

**Advanced System Monitor for Apple Silicon Macs**

A beautiful, real-time system monitoring tool designed specifically for Apple Silicon (M1/M2/M3/M4) Macs. Monitor every CPU core, GPU, memory, storage, and more—all from your terminal.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

### CPU Monitoring
- **Per-core history charts** for both E-cores (Efficiency) and P-cores (Performance)
- Real-time frequency tracking for each core
- Total CPU usage with cluster breakdown

### GPU Monitoring
- GPU utilization percentage and frequency
- Historical usage chart

### Memory & Storage
- **RAM** usage with percentage
- **Swap** usage tracking
- **SSD** usage (shows actual available space like Finder)
- **Memory Pressure** indicator (Normal/Moderate/High)

### Power Consumption
- CPU power draw with avg/peak tracking
- GPU power draw with avg/peak tracking
- Total system power consumption
- Thermal throttling status

### System Information
- Thermal status
- System uptime
- Load average (1/5/15 min)
- Disk I/O (read/write speeds)
- Network I/O (download/upload speeds)
- Battery status (percentage, charging state, time remaining)
- Top 5 CPU-consuming processes

## 📸 Screenshot

```
┌─ Apple M3 (4E + 4P + 10GPU) ────────────────────────────────────────────────┐
│ ┌─ CPU Cores ────────────────────┐ ┌─ GPU ─────────────────────────────────┐│
│ │ E0 15% 1200M │ E1 8% 1100M     │ │                                       ││
│ │ P0 60% 3500M │ P1 30% 3200M    │ │     GPU 20% @ 1380MHz                 ││
│ └────────────────────────────────┘ │     ▁▂▃▄▅▆▇█▆▅▃▂▁                     ││
│                                    └───────────────────────────────────────┘│
│ ┌─ CPU Usage ────────────────────┐ ┌─ Memory & Storage ────────────────────┐│
│ │ CPU 45% | E:15% | P:60%        │ │ RAM 8.2/16GB (51%)  ████████░░░░░░    ││
│ └────────────────────────────────┘ │ Swap: inactive       ░░░░░░░░░░░░░░   ││
│                                    │ SSD 180/228GB (79%) ████████████░░░   ││
│                                    │ Pressure: Normal     ██░░░░░░░░░░░░   ││
│                                    └───────────────────────────────────────┘│
│ ┌─ Power ──────────┐ ┌─ System ──────────┐ ┌─ Battery & Procs ─────────────┐│
│ │ CPU: 8.2W        │ │ Thermal: OK       │ │ BATTERY 🔋                    ││
│ │ GPU: 4.3W        │ │ Uptime: 2d 5h     │ │   75% - Discharging           ││
│ │ Total: 12.5W     │ │ Load: 2.1/1.8/1.5 │ │   3h 20m left                 ││
│ └──────────────────┘ │ DISK              │ │ TOP CPU:                      ││
│                      │   Read: 125MB/s   │ │   Safari       12.5%          ││
│                      │   Write: 45MB/s   │ │   WindowServer  8.2%          ││
│                      │ NETWORK           │ │   Code          3.2%          ││
│                      │   Down: 2.3MB/s   │ └─────────────────────────────────┘│
│                      │   Up: 512KB/s     │                                  │
│                      └───────────────────┘                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 🚀 Installation

### From PyPI (NOT YET PUBLISHED)
```bash
pip install vtop
```

### From source
```bash
git clone https://github.com/filippovicidomini/vtop.git
cd vtop
pip install .
```

### Development install
```bash
git clone https://github.com/filippovicidomini/vtop.git
cd vtop
pip install -e .
```

## 📖 Usage

vtop requires `sudo` to access power metrics:

```bash
sudo vtop
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--interval` | 1 | Refresh interval in seconds |
| `--color` | 2 | Color theme (0-8) |
| `--avg` | 30 | Window for averaged values (seconds) |

### Examples

```bash
# Default usage
sudo vtop

# Update every 2 seconds
sudo vtop --interval 2

# Use a different color theme
sudo vtop --color 5
```

Press `Ctrl+C` to exit.

## 🔧 Requirements

- **macOS** with Apple Silicon (M1, M2, M3, M4 series)
- **Python 3.8+**
- Terminal with Unicode support

### Dependencies
- `dashing` - Terminal UI library
- `psutil` - System monitoring library

## 🏗️ Architecture

```
vtop/
├── vtop.py      # Main application and UI layout
├── parsers.py   # Parsing powermetrics output
├── utils.py     # Utility functions and data gathering
└── __init__.py
```

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [asitop](https://github.com/tlkh/asitop) by tlkh
- Built with [dashing](https://github.com/FedericoCeratto/dashing) terminal UI library

## 📊 Comparison with other tools

| Feature | vtop | htop | asitop |
|---------|------|------|--------|
| Per-core history | ✅ | ❌ | ❌ |
| GPU monitoring | ✅ | ❌ | ✅ |
| Power consumption | ✅ | ❌ | ✅ |
| Memory pressure | ✅ | ❌ | ❌ |
| Battery status | ✅ | ❌ | ❌ |
| Top processes | ✅ | ✅ | ❌ |
| Disk I/O | ✅ | ❌ | ❌ |
| Network I/O | ✅ | ❌ | ❌ |
| Apple Silicon optimized | ✅ | ❌ | ✅ |

---

Made with ❤️ for Apple Silicon
