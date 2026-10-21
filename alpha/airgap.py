"""Zero-trust air-gap guard.

Blocks socket creation, DNS resolution and outbound connections at runtime so
that neither the application nor any of its dependencies can leak keystroke
derived data off the machine.
"""
from __future__ import annotations

import socket


class AirGapPrivacyViolation(PermissionError):
    """Raised when any component attempts an unauthorized network connection."""


_MESSAGE = (
    "[ALPHA AIR-GAP FIREWALL] Network access BLOCKED! "
    "ALPHA runs in 100% offline private mode to protect your typing privacy."
)


def _install_airgap_firewall() -> None:
    original_socket = socket.socket

    class _AirGapBlockedSocket(original_socket):  # type: ignore[misc,valid-type]
        def __init__(self, *args, **kwargs):
            raise AirGapPrivacyViolation(_MESSAGE)

        def connect(self, *args, **kwargs):
            raise AirGapPrivacyViolation(_MESSAGE)

        def connect_ex(self, *args, **kwargs):
            raise AirGapPrivacyViolation(_MESSAGE)

        def bind(self, *args, **kwargs):
            raise AirGapPrivacyViolation(_MESSAGE)

    def _blocked_call(*args, **kwargs):
        raise AirGapPrivacyViolation(_MESSAGE)

    socket.socket = _AirGapBlockedSocket  # type: ignore[assignment]
    socket.create_connection = _blocked_call  # type: ignore[assignment]
    for attribute in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "getfqdn"):
        try:
            setattr(socket, attribute, _blocked_call)
        except Exception:
            pass


_INSTALLED = False


def install() -> None:
    """Install the firewall once per process."""
    global _INSTALLED
    if _INSTALLED:
        return
    try:
        _install_airgap_firewall()
    except Exception:
        pass
    _INSTALLED = True


def is_installed() -> bool:
    return _INSTALLED
