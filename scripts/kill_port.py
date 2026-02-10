"""
Kill all processes bound to a given port.

Cross-platform (Windows / macOS / Linux) using only the standard library.
Strategy:
    1. Discover PIDs via ``netstat -aon`` (Windows) or ``lsof`` / ``ss`` (Unix).
    2. Identify the LISTENING process(es) first – these are the servers.
    3. Kill listeners, pause briefly, then sweep any remaining connections.
    4. Verify the port is clear.
"""

import os
import platform
import re
import signal
import subprocess
import sys
import time


class PortKiller:
    """Find and kill every process that owns a socket on *port*."""

    def __init__(self, port, verbose=True, dry_run=False):
        self.port = int(port)
        self.verbose = verbose
        self.dry_run = dry_run
        self.system = platform.system()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, message):
        if self.verbose:
            print(message)

    # ------------------------------------------------------------------
    # PID discovery
    # ------------------------------------------------------------------

    def find_pids(self):
        """Return ``{pid: [connection_dicts]}`` for the configured port."""
        if self.system == "Windows":
            return self._find_pids_windows()
        return self._find_pids_unix()

    def _find_pids_windows(self):
        """Parse ``netstat -aon`` on Windows."""
        try:
            result = subprocess.run(
                ["netstat", "-aon"],
                capture_output=True, text=True, check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"Error running netstat: {exc}", file=sys.stderr)
            return {}

        pids = {}
        port_str = str(self.port)

        for line in result.stdout.splitlines():
            parts = line.split()

            # TCP lines have 5 columns; UDP lines have 4 (no state).
            if len(parts) == 5 and parts[0] in ("TCP",):
                proto, local, foreign, state, pid_s = parts
            elif len(parts) == 4 and parts[0] in ("UDP",):
                proto, local, foreign, pid_s = parts
                state = "UDP"
            else:
                continue

            # Match port in either local or foreign address.
            local_port = local.rsplit(":", 1)[-1]
            foreign_port = foreign.rsplit(":", 1)[-1]
            if local_port != port_str and foreign_port != port_str:
                continue

            try:
                pid = int(pid_s)
            except ValueError:
                continue
            if pid == 0:
                continue  # System Idle / TIME_WAIT with no owner

            pids.setdefault(pid, []).append({
                "proto": proto,
                "local": local,
                "foreign": foreign,
                "state": state,
            })

        return pids

    def _find_pids_unix(self):
        """Try ``lsof``, then ``ss``, then ``netstat`` on Unix-likes."""
        pids = self._try_lsof()
        if pids is not None:
            return pids

        pids = self._try_ss()
        if pids is not None:
            return pids

        pids = self._try_netstat_unix()
        if pids is not None:
            return pids

        print(
            "Error: none of lsof, ss, or netstat were found on this system.",
            file=sys.stderr,
        )
        return {}

    def _try_lsof(self):
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{self.port}", "-n", "-P"],
                capture_output=True, text=True,
            )
        except FileNotFoundError:
            return None

        if result.returncode != 0:
            return None

        pids = {}
        for line in result.stdout.splitlines()[1:]:  # skip header
            parts = line.split()
            if len(parts) < 9:
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                continue
            state = parts[-1] if "(" in parts[-1] else ""
            # lsof wraps state in parens sometimes, e.g. "(LISTEN)"
            state = state.strip("()")
            pids.setdefault(pid, []).append({
                "proto": parts[7] if len(parts) > 7 else "TCP",
                "local": parts[8] if len(parts) > 8 else "",
                "foreign": parts[9] if len(parts) > 9 else "",
                "state": state or "UNKNOWN",
            })
        return pids

    def _try_ss(self):
        try:
            result = subprocess.run(
                ["ss", "-tlnp", "sport", "=", f":{self.port}"],
                capture_output=True, text=True,
            )
        except FileNotFoundError:
            return None

        if result.returncode != 0:
            return None

        pids = {}
        for line in result.stdout.splitlines()[1:]:
            match = re.search(r"pid=(\d+)", line)
            if match:
                pid = int(match.group(1))
                pids.setdefault(pid, []).append({
                    "proto": "TCP",
                    "local": "",
                    "foreign": "",
                    "state": "LISTEN",
                })
        return pids

    def _try_netstat_unix(self):
        try:
            result = subprocess.run(
                ["netstat", "-tlnp"],
                capture_output=True, text=True,
            )
        except FileNotFoundError:
            return None

        if result.returncode != 0:
            return None

        pids = {}
        for line in result.stdout.splitlines():
            if f":{self.port}" not in line:
                continue
            match = re.search(r"(\d+)/", line)
            if match:
                pid = int(match.group(1))
                pids.setdefault(pid, []).append({
                    "proto": "TCP",
                    "local": "",
                    "foreign": "",
                    "state": "LISTEN",
                })
        return pids

    # ------------------------------------------------------------------
    # Process inspection / killing
    # ------------------------------------------------------------------

    def _is_process_alive(self, pid):
        """Return *True* if *pid* is still running."""
        if self.system == "Windows":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True, text=True,
                )
                return str(pid) in result.stdout
            except Exception:
                return False
        else:
            try:
                os.kill(pid, 0)  # signal 0 = existence check
                return True
            except ProcessLookupError:
                return False
            except PermissionError:
                return True  # alive but we lack permission

    def _kill_process(self, pid, force=False):
        """Attempt to terminate a single process.  Returns *True* on success."""
        if not self._is_process_alive(pid):
            self._log(f"  PID {pid} is already dead.")
            return True

        if self.dry_run:
            self._log(f"  [DRY RUN] Would kill PID {pid}")
            return True

        if self.system == "Windows":
            return self._kill_windows(pid, force)
        return self._kill_unix(pid, force)

    def _kill_windows(self, pid, force):
        try:
            cmd = ["taskkill", "/PID", str(pid)]
            if force:
                cmd.append("/F")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self._log(f"  Killed PID {pid}" + (" (forced)" if force else ""))
                return True
            self._log(f"  Failed to kill PID {pid}: {result.stderr.strip()}")
            return False
        except Exception as exc:
            self._log(f"  Error killing PID {pid}: {exc}")
            return False

    def _kill_unix(self, pid, force):
        sig = signal.SIGKILL if force else signal.SIGTERM
        sig_name = "SIGKILL" if force else "SIGTERM"
        try:
            os.kill(pid, sig)
            self._log(f"  Sent {sig_name} to PID {pid}")
            return True
        except ProcessLookupError:
            self._log(f"  PID {pid} already dead.")
            return True
        except PermissionError:
            self._log(
                f"  Permission denied killing PID {pid}. "
                "Try running as administrator/root."
            )
            return False

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def kill_all(self, force=False):
        """
        Discover every process on *self.port*, kill them, and verify.

        Kill order:
            1. LISTENING / LISTEN processes (the servers) – sorted by PID.
            2. Everything else – sorted by PID.

        After each wave, wait briefly so child processes can collapse,
        then re-scan to see if stragglers remain.

        Returns *True* when the port is clear.
        """
        self._log(f"Scanning for processes on port {self.port}...")

        pids = self.find_pids()

        if not pids:
            self._log(f"No processes found on port {self.port}.")
            return True

        # ---- display findings ----
        self._log(f"\nFound {len(pids)} unique process(es) on port {self.port}:\n")
        for pid, connections in sorted(pids.items()):
            is_listener = any(
                c["state"] in ("LISTENING", "LISTEN") for c in connections
            )
            label = " [LISTENER]" if is_listener else ""
            self._log(f"  PID {pid}{label}  ({len(connections)} connection(s))")
            for c in connections:
                self._log(
                    f"      {c['proto']}  {c['local']}  ->  "
                    f"{c['foreign']}  [{c['state']}]"
                )

        # ---- determine kill order ----
        listener_pids = sorted(
            pid for pid, conns in pids.items()
            if any(c["state"] in ("LISTENING", "LISTEN") for c in conns)
        )
        other_pids = sorted(pid for pid in pids if pid not in listener_pids)
        kill_order = listener_pids + other_pids

        self._log(f"\nKill order: {kill_order}")

        # ---- kill loop ----
        for pid in kill_order:
            self._log(f"\nKilling PID {pid}...")
            success = self._kill_process(pid, force=force)
            if not success and not force:
                self._log("  Retrying with force...")
                self._kill_process(pid, force=True)
            if not self.dry_run:
                time.sleep(0.3)

        # In dry-run mode nothing was actually killed, so skip verification.
        if self.dry_run:
            self._log("\n[DRY RUN] No processes were actually killed.")
            return True

        # ---- verification pass ----
        self._log("\nWaiting for processes to exit...")
        time.sleep(1)

        remaining = {
            pid: conns
            for pid, conns in self.find_pids().items()
            if pid != 0
        }

        if not remaining:
            self._log(f"\nAll processes on port {self.port} have been terminated.")
            return True

        self._log(
            f"\n{len(remaining)} process(es) still alive: "
            f"{sorted(remaining.keys())}"
        )

        if not force:
            self._log("Force-killing remaining processes...")
            for pid in sorted(remaining):
                self._kill_process(pid, force=True)
            time.sleep(1)
            final = {
                pid: c for pid, c in self.find_pids().items() if pid != 0
            }
            if not final:
                self._log(
                    f"\nAll processes on port {self.port} have been terminated."
                )
                return True
            self._log(
                f"\nCould not kill PIDs {sorted(final.keys())}. "
                "You may need elevated privileges."
            )
            return False

        self._log("Could not clear the port. You may need elevated privileges.")
        return False


def kill_port_main(port, force=False, dry_run=False):
    """Entry-point called from the CLI."""
    killer = PortKiller(port, verbose=True, dry_run=dry_run)
    success = killer.kill_all(force=force)
    if not success:
        sys.exit(1)
