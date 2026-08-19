"""Default executor daemon application."""

from infinite_interns.executor.app import create_app
from infinite_interns.executor.docker_backend import DockerExecutionBackend

app = create_app(DockerExecutionBackend())
