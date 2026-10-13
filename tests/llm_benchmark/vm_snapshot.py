"""
Keywords to save and restore QEMU VM snapshots, so that every test starts from
the same desktop.

They send commands to the QEMU Human Monitor Protocol (HMP), the text
console of a running VM, through the Unix socket given to QEMU with
-monitor.
"""

import re
import socket

from robot.api import logger
from robot.api.deco import keyword, library

PROMPT = b"(qemu) "
# Most bytes read from the socket at once; socket.recv() requires it
RECV_SIZE = 4096
# HMP echoes the typed command with terminal control sequences
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@library(scope="GLOBAL")
class vm_snapshot:
    def __init__(self, monitor: str = "/tmp/yarf-vm-monitor.sock") -> None:
        self.monitor = monitor

    def _hmp(self, command: str, timeout: float = 300) -> str:
        """
        Run an HMP command and return its output.

        Args:
            command: The HMP command.
            timeout: Seconds to wait for the command to finish.

        Returns:
            The output of the command, without the echoed command line.
        """
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(self.monitor)
            output = b""
            while not output.endswith(PROMPT):
                output += sock.recv(RECV_SIZE)
            sock.sendall(command.encode() + b"\n")
            output = b""
            while not output.endswith(PROMPT):
                chunk = sock.recv(RECV_SIZE)
                if not chunk:
                    break
                output += chunk
        text = ANSI_ESCAPE.sub("", output.decode(errors="replace"))
        return text.removesuffix(PROMPT.decode()).split("\r\n", 1)[-1].strip()

    def _run(self, command: str) -> None:
        """
        Run an HMP command that prints nothing on success.

        Args:
            command: The HMP command.

        Raises:
            RuntimeError: If QEMU reports an error.
        """
        output = self._hmp(command)
        logger.info(f"{command}: {output or 'OK'}")
        if output:
            raise RuntimeError(f"'{command}' failed: {output}")

    @keyword
    def save_vm_snapshot(self, name: str = "clean") -> None:
        """
        Save the whole VM, memory included, as a snapshot.

        Args:
            name: The snapshot name.
        """
        self._run(f"savevm {name}")

    @keyword
    def restore_vm_snapshot(self, name: str = "clean") -> None:
        """
        Restore the VM to a snapshot saved with `Save Vm Snapshot`.

        Args:
            name: The snapshot name.
        """
        self._run(f"loadvm {name}")
