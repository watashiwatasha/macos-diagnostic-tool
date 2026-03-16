#!/usr/bin/env python3
"""
macOS System Diagnostic Scanner
Version: 1.0
Author: https://github.com/watashiwatasha/macos-diagnostic-tool

Comprehensive health check for:
- Memory and swap usage
- Residual processes and orphan daemons
- Resource leaks and zombie processes
- Leftover preference files from uninstalled apps
- System extensions
- Disk space issues and top space consumers
- Fan/thermal health
- Network listeners

Usage:
    python3 macos_diagnostic.py

Reports saved to: ~/Desktop/diagnostic_reports/
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import re


class MacOSDiagnostic:
    def __init__(self):
        self.timestamp = datetime.now()
        self.results = {
            "timestamp": self.timestamp.isoformat(),
            "system_info": {},
            "warnings": [],
            "critical": [],
            "info": [],
            "detailed_findings": {},
        }

    def run_command(self, cmd: str) -> str:
        """Execute shell command and return output."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "[TIMEOUT]"
        except Exception as e:
            return f"[ERROR: {str(e)}]"

    # ========== SYSTEM INFO ==========
    def check_system_info(self):
        """Get basic system information."""
        print("Checking system info...")

        os_version = self.run_command("sw_vers -productVersion")
        cpu_model = self.run_command("sysctl -n machdep.cpu.brand_string")
        cpu_count = self.run_command("sysctl -n hw.ncpu")
        ram_bytes = self.run_command("sysctl -n hw.memsize")
        ram_gb = int(ram_bytes) / (1024 ** 3)

        self.results["system_info"] = {
            "os_version": os_version,
            "cpu_model": cpu_model,
            "cpu_cores": int(cpu_count),
            "ram_gb": round(ram_gb, 1),
        }

    # ========== MEMORY & SWAP ==========
    def check_memory_usage(self):
        """Check RAM and swap usage patterns."""
        print("Checking memory usage...")

        vm_stat = self.run_command("vm_stat")
        lines = vm_stat.split("\n")
        memory_info = {}

        for line in lines:
            if "Pages free:" in line:
                memory_info["pages_free"] = line.split(":")[1].strip()
            elif "Pages active:" in line:
                memory_info["pages_active"] = line.split(":")[1].strip()
            elif "Pages inactive:" in line:
                memory_info["pages_inactive"] = line.split(":")[1].strip()

        top_memory = self.run_command("ps aux | sort -k 4 -nr | head -10")

        self.results["detailed_findings"]["memory"] = {
            "vm_stat": memory_info,
            "top_consumers": top_memory,
        }

        swap_info = self.run_command("sysctl vm.swapusage")
        if "Total" in swap_info:
            match = re.search(r"Used = (\d+\.?\d*)([GM])", swap_info)
            if match:
                swap_val = float(match.group(1))
                swap_unit = match.group(2)
                swap_gb = swap_val if swap_unit == "G" else swap_val / 1024

                # Scale thresholds relative to installed RAM so warnings
                # are meaningful on both 8GB and 32GB machines.
                # Warning at 50% of RAM, critical at 100% of RAM.
                ram_gb = self.results["system_info"].get("ram_gb", 16)
                warn_threshold = ram_gb * 0.5    # e.g. 4GB on 8GB, 8GB on 16GB
                crit_threshold = ram_gb * 1.0    # e.g. 8GB on 8GB, 16GB on 16GB

                if swap_gb >= crit_threshold:
                    self.results["critical"].append(
                        f"🚨 HIGH SWAP USAGE: {swap_gb:.1f}GB used "
                        f"(critical threshold for your {ram_gb}GB Mac: {crit_threshold:.0f}GB). "
                        f"Mac is under heavy memory pressure. Close apps or restart."
                    )
                elif swap_gb >= warn_threshold:
                    self.results["warnings"].append(
                        f"⚠️ Elevated swap usage: {swap_gb:.1f}GB "
                        f"(warning threshold for your {ram_gb}GB Mac: {warn_threshold:.0f}GB). "
                        f"Monitor closely."
                    )

    # ========== GPU MEMORY ==========
    def check_gpu_usage(self):
        """Check GPU memory usage across all running processes."""
        print("Checking GPU memory...")

        # Get total VRAM available from system profiler
        gpu_info = self.run_command(
            "system_profiler SPDisplaysDataType | grep -E 'VRAM|Chipset'"
        )

        # Use powermetrics to get per-process GPU usage if available
        gpu_processes = self.run_command(
            "sudo powermetrics --samplers gpu_power -i1 -n1 2>/dev/null | grep -E 'GPU|gpu' || echo 'N/A'"
        )

        # Fallback: check which processes are using significant memory
        # as a proxy for GPU-heavy apps (not perfect but works without sudo)
        top_mem_processes = self.run_command(
            "ps aux | sort -k 6 -nr | head -5 | awk '{print $6, $11}'"
        )

        findings = {
            "gpu_info": gpu_info if gpu_info else "Not available",
            "gpu_processes": gpu_processes,
            "top_memory_processes": top_mem_processes,
        }

        self.results["detailed_findings"]["gpu"] = findings

        # Parse VRAM usage if detectable
        vram_match = re.search(r"(\d+)\s*MB.*?(\d+)\s*MB", gpu_info or "")
        if vram_match:
            used_mb = int(vram_match.group(1))
            total_mb = int(vram_match.group(2))
            if total_mb > 0:
                usage_pct = (used_mb / total_mb) * 100
                if usage_pct > 90:
                    self.results["warnings"].append(
                        f"⚠️ GPU memory nearly full: {used_mb}MB / {total_mb}MB ({usage_pct:.0f}%). "
                        f"Close graphics-heavy apps if performance feels slow."
                    )

    # ========== RESIDUAL DAEMONS ==========
    def check_orphan_daemons(self):
        """Scan for residual/orphan daemons from uninstalled apps."""
        print("Scanning for orphan daemons...")

        # List all third-party launch daemons/agents (exclude Apple's own)
        launchctl_list = self.run_command(
            "sudo launchctl list 2>/dev/null | grep -v 'com.apple' | grep -v '^-' || true"
        )

        findings = {
            "third_party_daemons": launchctl_list if launchctl_list else "None detected",
            "orphan_plist_locations": [],
        }

        plist_locations = [
            "/Library/LaunchDaemons",
            "/Library/LaunchAgents",
            "~/Library/LaunchAgents",
        ]

        for location in plist_locations:
            expanded_path = os.path.expanduser(location)
            try:
                if os.path.exists(expanded_path):
                    for file in os.listdir(expanded_path):
                        if file.endswith(".plist"):
                            # Flag any non-Apple plist as worth reviewing
                            if not file.startswith("com.apple"):
                                findings["orphan_plist_locations"].append(
                                    f"{location}/{file}"
                                )
            except PermissionError:
                pass

        self.results["detailed_findings"]["daemons"] = findings

        if findings["orphan_plist_locations"]:
            plist_list = "\n".join(
                [f"  • {f}" for f in findings["orphan_plist_locations"]]
            )
            self.results["info"].append(
                f"ℹ️ Found {len(findings['orphan_plist_locations'])} third-party launch items. "
                f"Review if any are from apps you've uninstalled:\n{plist_list}"
            )

    # ========== SYSTEM EXTENSIONS ==========
    def check_system_extensions(self):
        """Check for suspicious or orphaned System Extensions."""
        print("Checking System Extensions...")

        ext_list = self.run_command("systemextensionsctl list")

        ext_count = ext_list.count("enabled")
        self.results["detailed_findings"]["extensions"] = {
            "total_extensions": ext_count,
            "extensions": ext_list,
        }

        if ext_count > 5:
            self.results["warnings"].append(
                f"⚠️ Multiple System Extensions ({ext_count}) detected. "
                f"Review in System Settings > General > Extensions."
            )

    # ========== PREFERENCE FILES ==========
    def check_preference_files(self):
        """Scan for leftover/orphaned preference files."""
        print("🔎 Scanning preference files...")

        pref_dir = os.path.expanduser("~/Library/Preferences")
        findings = {"suspicious_files": []}

        # Get list of installed apps to cross-reference
        installed_raw = self.run_command("ls /Applications/ 2>/dev/null")
        installed_apps = set(
            name.lower().replace(".app", "").replace(" ", "")
            for name in installed_raw.split("\n")
            if name.endswith(".app")
        )

        try:
            for file in os.listdir(pref_dir):
                if not file.endswith(".plist"):
                    continue
                # Extract app identifier from reverse-DNS plist name
                # e.g. "com.apple.finder.plist" -> skip Apple
                # e.g. "com.dropbox.client.plist" -> check if Dropbox is installed
                if file.startswith("com.apple.") or file.startswith("com.apple "):
                    continue
                parts = file.replace(".plist", "").split(".")
                # Use the third segment as the app name hint (e.g. "dropbox" from com.dropbox.client)
                app_hint = parts[1].lower() if len(parts) >= 2 else ""
                if app_hint and not any(app_hint in app for app in installed_apps):
                    findings["suspicious_files"].append(file)
        except PermissionError:
            findings["error"] = "Permission denied accessing Preferences"

        self.results["detailed_findings"]["preferences"] = findings

        if findings["suspicious_files"]:
            self.results["info"].append(
                f"ℹ️ Found {len(findings['suspicious_files'])} leftover preference files "
                f"from old apps. Safe to delete if those apps are uninstalled."
            )

    # ========== DISK SPACE ==========
    def check_disk_space(self):
        """Check disk space."""
        print("Checking disk space...")

        df_output = self.run_command("df -h / | tail -1")
        du_top = self.run_command(
            "du -sh ~/Library/Caches ~/Downloads ~/Library/Logs 2>/dev/null | sort -rh"
        )

        self.results["detailed_findings"]["disk"] = {
            "root_disk": df_output,
            "top_space_users": du_top,
        }

        parts = df_output.split()
        if len(parts) >= 5:
            try:
                used_percent = int(parts[4].rstrip("%"))
                if used_percent > 90:
                    self.results["critical"].append(
                        f"🚨 CRITICAL DISK SPACE: {used_percent}% used. "
                        f"Free up space immediately to prevent crashes."
                    )
                elif used_percent > 80:
                    self.results["warnings"].append(
                        f"⚠️ Disk space running low: {used_percent}% used."
                    )
            except ValueError:
                pass

    # ========== SPACE OFFENDERS ==========
    def check_space_offenders(self):
        """Identify biggest space consumers for quick cleanup wins."""
        print("Scanning for space offenders...")

        scan_paths = [
            "~/Library/Caches",
            "~/Downloads",
            "~/Documents",
            "~/Pictures",
            "~/Movies",
            "~/Music",
            "~/Library/Application Support",
            "~/Library/Logs",
            "~/Library/Mail",
            "~/.Trash",
        ]

        space_offenders = []

        for path in scan_paths:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                try:
                    size_output = self.run_command(f"du -sh '{expanded}' 2>/dev/null")
                    if size_output and not size_output.startswith("["):
                        size_str = size_output.split("\t")[0].strip()
                        space_offenders.append({"path": path, "size": size_str})
                except Exception:
                    pass

        def parse_size_mb(size_str):
            try:
                if "G" in size_str:
                    return float(size_str.replace("G", "")) * 1024
                elif "M" in size_str:
                    return float(size_str.replace("M", ""))
                elif "K" in size_str:
                    return float(size_str.replace("K", "")) / 1024
            except Exception:
                pass
            return 0

        space_offenders.sort(key=lambda x: parse_size_mb(x["size"]), reverse=True)

        self.results["detailed_findings"]["space_offenders"] = {
            "ranked_offenders": space_offenders[:15],
            "total_scanned": len(scan_paths),
        }

        big_offenders = [
            x for x in space_offenders if parse_size_mb(x["size"]) > 5120
        ]

        if big_offenders:
            offender_list = "\n".join(
                [f"  • {x['path']}: {x['size']}" for x in big_offenders[:5]]
            )
            self.results["info"].append(
                f"💡 Large folders (>5GB) — consider archiving or deleting:\n"
                f"{offender_list}"
            )

        for item in space_offenders[:5]:
            size_mb = parse_size_mb(item["size"])
            if "Caches" in item["path"] and size_mb > 10240:
                self.results["warnings"].append(
                    f"⚠️ Cache folder is large: {item['path']} ({item['size']}). "
                    f"Safe to clear via Finder > Go > Library > Caches."
                )
            elif "Downloads" in item["path"] and size_mb > 20480:
                self.results["warnings"].append(
                    f"⚠️ Downloads folder is {item['size']}. Archive or delete old files."
                )
            elif ".Trash" in item["path"] and size_mb > 5120:
                self.results["info"].append(
                    f"Trash contains {item['size']}. Empty it to reclaim space."
                )

    # ========== FAN / THERMAL HEALTH ==========
    def check_fan_health(self):
        """Monitor fan sensors and thermal health."""
        print("Checking fan/thermal health...")

        pmset_output = self.run_command("pmset -g thermlog 2>/dev/null")
        fan_info = self.run_command(
            "system_profiler SPHardwareDataType | grep -i fan || echo 'No direct fan data'"
        )
        cpu_temp_raw = self.run_command(
            "sudo powermetrics --samplers smc -i1 -n1 2>/dev/null "
            "| grep -i 'CPU die temperature' || echo 'N/A'"
        )

        self.results["detailed_findings"]["fan_health"] = {
            "pmset_thermal": pmset_output if pmset_output else "Not available",
            "fan_info": fan_info,
            "cpu_temp_raw": cpu_temp_raw,
        }

        if pmset_output and "thermal" in pmset_output.lower():
            if "warning" in pmset_output.lower() or "critical" in pmset_output.lower():
                self.results["warnings"].append(
                    "⚠️ Thermal warnings found in system logs. "
                    "Check Mac ventilation and consider cleaning dust from vents."
                )

        if "CPU die temperature" in cpu_temp_raw:
            temp_match = re.search(r"(\d+\.\d+)\s*C", cpu_temp_raw)
            if temp_match:
                temp = float(temp_match.group(1))
                self.results["system_info"]["cpu_temp"] = f"{temp}°C"

                if temp > 90:
                    self.results["critical"].append(
                        f"🚨 HIGH CPU TEMPERATURE: {temp}°C. "
                        f"Check cooling immediately — this can damage your Mac."
                    )
                elif temp > 80:
                    self.results["warnings"].append(
                        f"⚠️ Elevated CPU temperature: {temp}°C. "
                        f"Ensure vents are not blocked."
                    )

        if fan_info and "No direct fan data" not in fan_info:
            self.results["info"].append(
                "ℹ️ Fan sensors detected. Temperature monitoring active."
            )

    # ========== PROCESS ANOMALIES ==========
    def check_process_anomalies(self):
        """Check for unusual process behavior."""
        print("Scanning processes...")

        high_cpu = self.run_command("ps aux | sort -k 3 -nr | head -10")
        high_mem = self.run_command("ps aux | sort -k 4 -nr | head -10")
        zombies = self.run_command("ps aux | grep -E '\\<Z\\>' | grep -v grep")

        self.results["detailed_findings"]["processes"] = {
            "high_cpu": high_cpu,
            "high_memory": high_mem,
            "zombie_processes": zombies if zombies else "None detected",
        }

        if zombies:
            self.results["warnings"].append(
                "⚠️ Zombie processes detected. A restart is recommended."
            )

    # ========== NETWORK CONNECTIONS ==========
    def check_network_connections(self):
        """Check for suspicious network listeners."""
        print("Checking network connections...")

        listeners = self.run_command(
            "lsof -i -P -n 2>/dev/null | grep LISTEN | head -15"
        )

        self.results["detailed_findings"]["network"] = {
            "listening_ports": listeners
        }

        port_count = len([l for l in listeners.split("\n") if l])
        if port_count > 20:
            self.results["warnings"].append(
                f"⚠️ Many listening ports ({port_count}). "
                f"Check for unwanted background services."
            )

    # ========== CACHE CLEANUP ==========
    def check_cache_cleanup_opportunities(self):
        """Identify cache cleanup opportunities."""
        print("Checking cache cleanup opportunities...")

        cache_size = self.run_command("du -sh ~/Library/Caches 2>/dev/null | cut -f1")
        logs_size = self.run_command("du -sh ~/Library/Logs 2>/dev/null | cut -f1")
        tmp_size = self.run_command("du -sh /tmp 2>/dev/null | cut -f1")

        self.results["detailed_findings"]["cleanup"] = {
            "cache_size": cache_size,
            "logs_size": logs_size,
            "tmp_size": tmp_size,
        }

        try:
            if "G" in cache_size:
                cache_gb = float(cache_size.replace("G", ""))
                if cache_gb > 5:
                    self.results["info"].append(
                        f"ℹ️ Cache folder is {cache_size}. "
                        f"You can safely clear it via Finder > Go > Library > Caches."
                    )
        except Exception:
            pass

    # ========== RUN ALL ==========
    def run_full_diagnostic(self):
        """Run all diagnostic checks."""
        print()
        print("=" * 60)
        print("  macOS System Diagnostic Scanner v1.0")
        print("=" * 60)
        print()

        self.check_system_info()
        self.check_memory_usage()
        self.check_gpu_usage()
        self.check_orphan_daemons()
        self.check_system_extensions()
        self.check_preference_files()
        self.check_disk_space()
        self.check_space_offenders()
        self.check_fan_health()
        self.check_process_anomalies()
        self.check_network_connections()
        self.check_cache_cleanup_opportunities()

        print()
        print("✅ Diagnostic complete!")
        print()
        return self.results

    def save_json_report(self, filepath: str):
        """Save detailed JSON report."""
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"📄 JSON report: {filepath}")

    def generate_html_report(self, filepath: str):
        """Generate HTML report."""
        si = self.results["system_info"]
        df = self.results["detailed_findings"]

        # Build status badges
        badges = ""
        if self.results["critical"]:
            badges += f'<span class="badge badge-critical">🚨 {len(self.results["critical"])} Critical</span>'
        if self.results["warnings"]:
            badges += f'<span class="badge badge-warning">⚠️ {len(self.results["warnings"])} Warnings</span>'
        if self.results["info"]:
            badges += f'<span class="badge badge-info">ℹ️ {len(self.results["info"])} Info</span>'
        if not self.results["critical"] and not self.results["warnings"]:
            badges += '<span class="badge badge-ok">✅ All Clear</span>'

        def alert_blocks(items, css_class):
            return "".join(
                f'<div class="alert {css_class}">{item}</div>' for item in items
            )

        def space_table_rows():
            offenders = df.get("space_offenders", {}).get("ranked_offenders", [])
            if not offenders:
                return ""
            rows = "".join(
                f"<tr><td>{i+1}</td><td>{item['path']}</td><td><strong>{item['size']}</strong></td></tr>"
                for i, item in enumerate(offenders[:10])
            )
            return f"""
            <div class="section">
                <h2>Top Space Consumers</h2>
                <table class="space-table">
                    <thead><tr><th>#</th><th>Location</th><th>Size</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>"""

        cpu_temp = si.get("cpu_temp", self.timestamp.strftime("%H:%M:%S"))
        cpu_temp_label = "CPU Temp" if "cpu_temp" in si else "Scan Time"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>macOS Diagnostic Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #2d3436, #1e272e);
            color: #fff;
            padding: 40px;
            text-align: center;
        }}
        header h1 {{ font-size: 26px; margin-bottom: 8px; }}
        header p {{ opacity: 0.7; font-size: 13px; }}
        .version {{ display:inline-block; background:#667eea; color:#fff;
                    padding:3px 10px; border-radius:10px; font-size:11px; margin-top:8px; }}
        .content {{ padding: 40px; }}
        .sys-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
        }}
        .sys-box {{
            background: #fff;
            border-left: 4px solid #667eea;
            padding: 14px;
            border-radius: 8px;
        }}
        .sys-box label {{ font-size:11px; color:#888; text-transform:uppercase; font-weight:600; }}
        .sys-box value {{ display:block; font-size:20px; font-weight:700;
                          font-family:monospace; color:#2d3436; margin-top:4px; }}
        .badges {{ margin-bottom: 32px; }}
        .badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
            margin-bottom: 8px;
        }}
        .badge-critical {{ background:#ffebee; color:#c62828; }}
        .badge-warning  {{ background:#fff3e0; color:#e65100; }}
        .badge-info     {{ background:#e3f2fd; color:#1565c0; }}
        .badge-ok       {{ background:#e8f5e9; color:#2e7d32; }}
        .section {{ margin-bottom: 36px; }}
        .section h2 {{
            font-size: 18px;
            font-weight: 700;
            color: #2d3436;
            border-bottom: 3px solid #667eea;
            padding-bottom: 8px;
            margin-bottom: 16px;
        }}
        .alert {{
            padding: 14px 16px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid;
            white-space: pre-wrap;
            line-height: 1.5;
        }}
        .critical {{ background:#fff3f3; border-color:#ff4757; color:#b71c1c; }}
        .warning  {{ background:#fff8e1; border-color:#ffb300; color:#f57c00; }}
        .info     {{ background:#e3f2fd; border-color:#2196f3; color:#1565c0; }}
        .space-table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
        .space-table th {{ background:#667eea; color:#fff; padding:10px; text-align:left; font-size:12px; }}
        .space-table td {{ padding:10px; border-bottom:1px solid #eee; font-size:13px; }}
        .space-table tr:last-child td {{ border-bottom: none; }}
        .details {{ background:#f8f9fa; border-radius:12px; padding:24px; margin-bottom:36px; }}
        .detail-block {{ margin-bottom:20px; }}
        .detail-label {{ font-size:11px; font-weight:700; text-transform:uppercase;
                         color:#667eea; margin-bottom:6px; }}
        .detail-content {{
            background:#fff;
            padding:12px;
            border-radius:6px;
            font-family:monospace;
            font-size:12px;
            color:#555;
            white-space:pre-wrap;
            overflow-x:auto;
        }}
        footer {{
            background:#f8f9fa;
            padding:20px;
            text-align:center;
            color:#aaa;
            font-size:12px;
        }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>🔍 macOS System Diagnostic</h1>
        <p>Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <span class="version">v1.0</span>
    </header>

    <div class="content">
        <div class="sys-grid">
            <div class="sys-box"><label>OS Version</label><value>{si.get('os_version','N/A')}</value></div>
            <div class="sys-box"><label>CPU Cores</label><value>{si.get('cpu_cores','N/A')}</value></div>
            <div class="sys-box"><label>RAM</label><value>{si.get('ram_gb','N/A')} GB</value></div>
            <div class="sys-box"><label>{cpu_temp_label}</label><value>{cpu_temp}</value></div>
        </div>

        <div class="badges">{badges}</div>

        {'<div class="section"><h2>🚨 Critical Issues</h2>' + alert_blocks(self.results["critical"], "alert critical") + '</div>' if self.results["critical"] else ''}
        {'<div class="section"><h2>⚠️ Warnings</h2>' + alert_blocks(self.results["warnings"], "alert warning") + '</div>' if self.results["warnings"] else ''}
        {'<div class="section"><h2>ℹ️ Information</h2>' + alert_blocks(self.results["info"], "alert info") + '</div>' if self.results["info"] else ''}

        {space_table_rows()}

        <div class="details">
            <div class="section"><h2>Detailed Findings</h2></div>
            <div class="detail-block">
                <div class="detail-label">Memory (vm_stat)</div>
                <div class="detail-content">{json.dumps(df.get('memory', {}), indent=2)}</div>
            </div>
            <div class="detail-block">
                <div class="detail-label">Fan / Thermal Health</div>
                <div class="detail-content">{json.dumps(df.get('fan_health', {}), indent=2)}</div>
            </div>
            <div class="detail-block">
                <div class="detail-label">GPU Memory</div>
                <div class="detail-content">{json.dumps(df.get('gpu', {}), indent=2)}</div>
            </div>
            <div class="detail-block">
                <div class="detail-label">Top Processes by CPU</div>
                <div class="detail-content">{df.get('processes', {}).get('high_cpu', 'N/A')}</div>
            </div>
            <div class="detail-block">
                <div class="detail-label">Top Processes by Memory</div>
                <div class="detail-content">{df.get('processes', {}).get('high_memory', 'N/A')}</div>
            </div>
            <div class="detail-block">
                <div class="detail-label">Disk Space</div>
                <div class="detail-content">{df.get('disk', {}).get('root_disk', 'N/A')}</div>
            </div>
            <div class="detail-block">
                <div class="detail-label">System Extensions</div>
                <div class="detail-content">{df.get('extensions', {}).get('extensions', 'N/A')}</div>
            </div>
            <div class="detail-block">
                <div class="detail-label">Network Listeners</div>
                <div class="detail-content">{df.get('network', {}).get('listening_ports', 'N/A')}</div>
            </div>
        </div>
    </div>

    <footer>
        <p>macOS System Diagnostic Tool v1.0 &nbsp;|&nbsp;
           <a href="https://github.com/watashiwatasha/macos-diagnostic-tool">GitHub</a></p>
        <p style="margin-top:6px;opacity:0.5">Full data in companion .json report</p>
    </footer>
</div>
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML report: {filepath}")


def main():
    if sys.platform != "darwin":
        print("❌ This script requires macOS.")
        sys.exit(1)

    diagnostic = MacOSDiagnostic()
    results = diagnostic.run_full_diagnostic()

    output_dir = Path.home() / "Desktop" / "diagnostic_reports"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"diagnostic_{timestamp}.json"
    html_path = output_dir / f"diagnostic_{timestamp}.html"

    diagnostic.save_json_report(str(json_path))
    diagnostic.generate_html_report(str(html_path))

    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    if results["critical"]:
        print(f"\n🚨 CRITICAL ({len(results['critical'])}):")
        for alert in results["critical"]:
            print(f"  • {alert}")

    if results["warnings"]:
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
        for alert in results["warnings"]:
            print(f"  • {alert}")

    if results["info"]:
        print(f"\nℹ️  INFO ({len(results['info'])}):")
        for alert in results["info"]:
            print(f"  • {alert}")

    if not results["critical"] and not results["warnings"]:
        print("\n✅ System looks healthy — no critical issues detected.")

    print(f"\n📁 Reports saved to: {output_dir}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
