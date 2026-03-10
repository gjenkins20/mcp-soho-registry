"""Tests for topology parser."""

import tempfile
from pathlib import Path

from mcp_orchestrator.topology import Topology


SAMPLE_YAML = """\
name: "Test Network"
devices:
  - type: firewall
    vendor: fortinet
    model: FortiGate 40F
    ip: 192.168.1.1
  - type: server
    vendor: raspberry-pi
    model: Pi 5
    ip: 192.168.1.2
    services: [docker, grafana]
use_cases:
  - network-monitoring
  - security-alerting
constraints:
  max_agents: 4
  require_local: true
  approval_gated: [firewall, credentials]
"""


class TestTopology:
    def test_parse_yaml(self, tmp_path):
        f = tmp_path / "topology.yaml"
        f.write_text(SAMPLE_YAML)
        topo = Topology.from_yaml(f)
        assert topo.name == "Test Network"
        assert len(topo.devices) == 2
        assert topo.devices[0].vendor == "fortinet"
        assert topo.devices[1].services == ["docker", "grafana"]

    def test_constraints(self, tmp_path):
        f = tmp_path / "topology.yaml"
        f.write_text(SAMPLE_YAML)
        topo = Topology.from_yaml(f)
        assert topo.constraints.max_agents == 4
        assert topo.constraints.require_local is True
        assert "firewall" in topo.constraints.approval_gated

    def test_all_vendors(self, tmp_path):
        f = tmp_path / "topology.yaml"
        f.write_text(SAMPLE_YAML)
        topo = Topology.from_yaml(f)
        assert topo.all_vendors == {"fortinet", "raspberry-pi"}

    def test_all_services(self, tmp_path):
        f = tmp_path / "topology.yaml"
        f.write_text(SAMPLE_YAML)
        topo = Topology.from_yaml(f)
        assert topo.all_services == {"docker", "grafana"}

    def test_all_device_types(self, tmp_path):
        f = tmp_path / "topology.yaml"
        f.write_text(SAMPLE_YAML)
        topo = Topology.from_yaml(f)
        assert topo.all_device_types == {"firewall", "server"}
