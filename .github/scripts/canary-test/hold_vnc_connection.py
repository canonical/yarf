"""
Keep one idle client connected to wayvnc for the rest of the job.

wayvnc 0.9 stops its screen capture when the last client disconnects and
can fail to start it again for the next client, which makes it exit. YARF
opens a new VNC connection for each action, so an idle client that stays
connected keeps wayvnc from restarting the capture between actions.

Upstream issue: https://github.com/any1/wayvnc/issues/401

The script returns once the RFB handshake succeeds and leaves a background
process holding the connection until wayvnc closes it.
"""

import argparse
import os
import socket
import time

NO_AUTHENTICATION = 1
SECURITY_RESULT_OK = b"\x00\x00\x00\x00"
SHARED_SESSION = b"\x01"
SERVER_INIT_HEADER_SIZE = 24


def connect(host: str, port: int, timeout: float) -> socket.socket:
    """
    Connect to the VNC server, retrying until it accepts connections.

    Args:
        host: The VNC server host.
        port: The VNC server port.
        timeout: The number of seconds to keep retrying.

    Returns:
        The connected socket.

    Raises:
        TimeoutError: If the server does not accept a connection in time.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            return socket.create_connection((host, port))
        except OSError as error:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"VNC server at {host}:{port} is not reachable"
                ) from error
            time.sleep(0.5)


def receive(sock: socket.socket, size: int) -> bytes:
    """
    Read an exact number of bytes from the socket.

    Args:
        sock: The connected socket.
        size: The number of bytes to read.

    Returns:
        The bytes read.

    Raises:
        ConnectionError: If the server closes the connection first.
    """
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("VNC server closed the connection")
        data += chunk
    return data


def handshake(sock: socket.socket) -> None:
    """
    Complete the RFB handshake as a shared client without authentication.

    Follows RFB 3.8 (RFC 6143), which wayvnc offers. All multi-byte numbers
    in RFB are big-endian.

    Args:
        sock: The connected socket.

    Raises:
        ConnectionError: If the server rejects the client.
    """
    # ProtocolVersion (7.1.1): the server sends a 12-byte version string,
    # e.g. b"RFB 003.008\n". Echoing it back accepts that version.
    sock.sendall(receive(sock, 12))

    # Security (7.1.2): one byte with the number of security types, followed
    # by one byte per type.
    security_types = receive(sock, receive(sock, 1)[0])
    if NO_AUTHENTICATION not in security_types:
        raise ConnectionError("VNC server does not allow unauthenticated use")
    # Choose security type 1, "None" (no password).
    sock.sendall(bytes([NO_AUTHENTICATION]))

    # SecurityResult (7.1.3): a 4-byte integer, 0 for OK and 1 for failed.
    if receive(sock, 4) != SECURITY_RESULT_OK:
        raise ConnectionError("VNC server rejected the security handshake")

    # ClientInit (7.3.1): a 1-byte shared flag. 1 shares the session, so
    # wayvnc keeps YARF's own connections instead of dropping them for us.
    sock.sendall(SHARED_SESSION)

    # ServerInit (7.3.2): a 24-byte header (width: 2, height: 2,
    # pixel format: 16, name length: 4) followed by the desktop name.
    # Read the name length from bytes 20-23, then read and discard the name.
    server_init = receive(sock, SERVER_INIT_HEADER_SIZE)
    receive(sock, int.from_bytes(server_init[20:24], "big"))


def hold(sock: socket.socket) -> None:
    """
    Keep the connection open until the server closes it.

    The client never requests framebuffer updates, so the server has nothing
    to send and the loop only ends when the connection closes.

    Args:
        sock: The connected socket.
    """
    while sock.recv(4096):
        pass


def main() -> None:
    """
    Connect to wayvnc and hold the connection from a background process.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5900)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()

    sock = connect(args.host, args.port, args.timeout)
    handshake(sock)
    print(
        f"Holding an idle VNC connection to {args.host}:{args.port}",
        flush=True,
    )
    if os.fork() == 0:
        os.setsid()
        hold(sock)


if __name__ == "__main__":
    main()
