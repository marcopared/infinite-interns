from pathlib import Path
from typing import cast

import yaml


def test_only_executor_receives_docker_socket() -> None:
    payload = cast(dict[str, object], yaml.safe_load(Path("docker-compose.workstation.yml").read_text()))
    services = cast(dict[str, dict[str, object]], payload["services"])

    socket = "/var/run/docker.sock:/var/run/docker.sock"
    services_with_socket = {
        name
        for name, config in services.items()
        if socket in cast(list[str], config.get("volumes", []))
    }
    assert services_with_socket == {"executor"}


def test_agent_server_and_executor_share_only_control_network() -> None:
    payload = cast(dict[str, object], yaml.safe_load(Path("docker-compose.workstation.yml").read_text()))
    services = cast(dict[str, dict[str, object]], payload["services"])
    assert services["agent-server"]["networks"] == ["control"]
    assert services["executor"]["networks"] == ["control"]
