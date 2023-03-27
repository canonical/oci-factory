import docker
import logging
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
        **kwargs
    )

    output.wait()
    if output.wait().get("StatusCode", 1) > 0:
        raise Exception(output.logs().decode(), output.wait().get("StatusCode"))

    result = output.logs().decode()
    output.remove()

    return result


def run_trivy_scan(
    image_name: str,
    image_or_fs: str,
    trivy_image: str,
    additional_args: str = "",
    docker_client: docker.client.DockerClient = None,
) -> str:
    cmd = f"trivy {image_or_fs} --severity HIGH,CRITICAL --exit-code 2 {additional_args} {image_name}"
    volumes = {
        "/var/run/docker.sock": {"bind": "/var/run/docker.sock"},
        "trivy_db": {"bind": "/root/.cache/trivy/db"},
    }

    if image_or_fs == "filesystem":
        volumes[image_name] = {"bind": image_name}

    return run_docker_container(trivy_image, volumes, cmd, docker_client, entrypoint="")


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


def dive_efficiency_test(
    image_name: str,
    highestUserWastedPercent: float = 0.2,
    lowestEfficiency: float = 0.85,
    additional_args: str = "",
    docker_client: docker.client.DockerClient = None,
):
    # Runs a Dive inspection, failing if the image is not efficient
    logging.info(f"Allowed % of bytes wasted: up to {highestUserWastedPercent}")
    logging.info(f"Lowest % of image efficiency allowed: {lowestEfficiency}")

    cmd = f"--ci --highestUserWastedPercent {highestUserWastedPercent} --lowestEfficiency {lowestEfficiency} {additional_args} {image_name}"
    volumes = {
        "/var/run/docker.sock": {"bind": "/var/run/docker.sock"},
    }
    return run_docker_container("wagoodman/dive:latest", volumes, cmd, docker_client)
