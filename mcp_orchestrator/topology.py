"""Topology parser — reads YAML network topology definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Device:
    """A device in the network topology."""

    type: str  # firewall, nas, server, access-point, switch, camera, etc.
    vendor: str
    model: str = ""
    ip: str = ""
    services: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> Device:
        return cls(
            type=d["type"],
            vendor=d["vendor"],
            model=d.get("model", ""),
            ip=d.get("ip", ""),
            services=d.get("services", []),
        )


@dataclass
class Constraints:
    """Constraints on the orchestrator output."""

    max_agents: int = 8
    require_local: bool = False
    approval_gated: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict | None) -> Constraints:
        if not d:
            return cls()
        return cls(
            max_agents=d.get("max_agents", 8),
            require_local=d.get("require_local", False),
            approval_gated=d.get("approval_gated", []),
        )


@dataclass
class Topology:
    """A parsed network topology."""

    name: str
    devices: list[Device]
    use_cases: list[str]
    constraints: Constraints

    @classmethod
    def from_yaml(cls, path: str | Path) -> Topology:
        """Parse a topology YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            name=data.get("name", "Unnamed Network"),
            devices=[Device.from_dict(d) for d in data.get("devices", [])],
            use_cases=data.get("use_cases", []),
            constraints=Constraints.from_dict(data.get("constraints")),
        )

    @property
    def all_vendors(self) -> set[str]:
        """All unique vendor names in the topology."""
        return {d.vendor.lower() for d in self.devices}

    @property
    def all_services(self) -> set[str]:
        """All unique services running across devices."""
        services: set[str] = set()
        for d in self.devices:
            services.update(s.lower() for s in d.services)
        return services

    @property
    def all_device_types(self) -> set[str]:
        """All unique device types."""
        return {d.type.lower() for d in self.devices}
