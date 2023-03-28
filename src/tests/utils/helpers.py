import docker
import os


def run_docker_container(
    image: str,
    volumes: dict,
    command: str,
    docker_client: docker.client.DockerClient = None,
    **kwargs,
):
    if not docker_client:
        docker_client = docker.from_env()

    output = docker_client.containers.run(
        image,
        detach=True,
        volumes=volumes,
        oom_kill_disable=True,
        command=command,
        **kwargs,
    )

    output.wait()
    if output.wait().get("StatusCode", 1) > 0:
        raise Exception(output.logs().decode(), output.wait().get("StatusCode"))

    result = output.logs().decode()
    output.remove()

    return result


def run_malware_scan(
    image_fs_path: str,
    additional_args: str = "",
    docker_client: docker.client.DockerClient = None,
) -> str:
    cmd = f"clamscan --archive-verbose --recursive {additional_args} /scandir"
    volumes = {
        os.path.abspath(image_fs_path): {"bind": "/scandir"},
    }

    return run_docker_container("clamav/clamav:1.0", volumes, cmd, docker_client)
