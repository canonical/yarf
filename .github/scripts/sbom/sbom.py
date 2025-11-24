import json
import subprocess
import time

import requests


def get_yarf_revision(channel="latest/beta") -> str:
    """
    Get yarf snap revision.
    """
    result = subprocess.run(
        ["snap", "info", "yarf"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        return None

    search_prefix = f"{channel}:"
    for line in result.stdout.splitlines():
        if line.strip().startswith(search_prefix):
            parts = line.split()
            revision = parts[3].strip("()")
            return revision

    return None


def start_sbom_request(revision: str) -> str:
    """
    Start a SBOM generation request for given revision.
    """
    url = "https://sbom-request.canonical.com/api/v1/artifacts/snap/store"
    payload = {
        "maintainer": "Canonical",
        "email": "ce-certification-qa@lists.canonical.com",
        "version": revision,
        "department": {"value": "devices_engineering", "type": "predefined"},
        "team": {"value": "certification", "type": "predefined"},
        "artifactName": "yarf",
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Failed to submit SBOM generation request. Status code: {response.status_code}, Response: {response.text}"
        )

    response_data = response.json()

    # Check if artifactId is present in the response
    if (
        "data" not in response_data
        or "artifactId" not in response_data["data"]
    ):
        raise Exception("artifactId not found in response")

    artifact_id = response_data["data"]["artifactId"]
    print(f"Upload started successfully. Artifact ID: {artifact_id}")

    return artifact_id


def monitor_artifact_status(artifact_id, interval=10, timeout=1800) -> bool:
    """
    Monitor the SBOM generation status.
    """
    status_url = f"https://sbom-request.canonical.com/api/v1/artifacts/status/{artifact_id}"
    headers = {"Accept": "application/json"}

    start_time = time.time()
    elapsed_time = 0

    print(f"Starting to monitor artifact status for ID: {artifact_id}")

    while elapsed_time < timeout:
        response = requests.get(status_url, headers=headers)

        if response.status_code != 200:
            print(
                f"Failed to get status. Status code: {response.status_code}, Response: {response.text}"
            )
            time.sleep(interval)
            elapsed_time = time.time() - start_time
            continue

        response_data = response.json()

        if (
            "data" not in response_data
            or "status" not in response_data["data"]
        ):
            print(f"Invalid response format: {response_data}")
            time.sleep(interval)
            elapsed_time = time.time() - start_time
            continue

        current_status = response_data["data"]["status"]
        print(
            f"Current status: {current_status} (Elapsed time: {elapsed_time:.1f}s)"
        )

        if current_status == "completed":
            print(
                f"Artifact processing completed after {elapsed_time:.1f} seconds"
            )
            return True

        time.sleep(interval)
        elapsed_time = time.time() - start_time

    print(
        f"Timeout reached after {timeout} seconds. Artifact processing did not complete."
    )
    return False


def download_sbom(artifact_id, output_file=None):
    """
    Download the SBOM file and save it.
    """
    sbom_url = f"https://sbom-request.canonical.com/api/v1/artifacts/sbom/{artifact_id}"
    headers = {"Accept": "application/octet-stream"}

    print(f"Downloading SBOM for artifact ID: {artifact_id}")

    response = requests.get(sbom_url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Failed to download SBOM. Status code: {response.status_code}, Response: {response.text}"
        )

    sbom_json = json.loads(response.text)
    if output_file:
        with open(output_file, "w") as f:
            json.dump(sbom_json, f, indent=4)
        print(f"SBOM saved to {output_file}")


if __name__ == "__main__":
    revision = get_yarf_revision()
    artifact_id = start_sbom_request(revision)
    if monitor_artifact_status(artifact_id):
        download_sbom(artifact_id, f"/tmp/yarf_{revision}.sbom.json")
