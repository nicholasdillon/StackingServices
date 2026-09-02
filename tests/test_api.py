from fastapi.testclient import TestClient

from mininode.app import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token"}


def test_health_and_reset() -> None:
    health = client.get("/_mininode/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    reset = client.post("/_mininode/reset")
    assert reset.status_code == 200
    assert reset.json() == {"status": "reset"}


def test_auth_required() -> None:
    response = client.get("/v4/regions")
    assert response.status_code == 401
    assert response.json()["errors"][0]["reason"] == "Expected Bearer token in Authorization header."


def test_instance_lifecycle() -> None:
    create = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "web-1",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
        },
    )
    assert create.status_code == 200
    instance = create.json()
    assert instance["status"] == "running"

    list_response = client.get("/v4/linode/instances", headers=AUTH)
    assert list_response.status_code == 200
    assert list_response.json()["results"] >= 1

    shutdown = client.post(f"/v4/linode/instances/{instance['id']}/shutdown", headers=AUTH)
    assert shutdown.status_code == 200
    assert shutdown.json()["status"] == "offline"

    reboot = client.post(f"/v4/linode/instances/{instance['id']}/reboot", headers=AUTH)
    assert reboot.status_code == 200
    assert reboot.json()["status"] == "running"


def test_volume_attach() -> None:
    instance = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "worker-1",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/debian12",
        },
    ).json()

    volume = client.post(
        "/v4/volumes",
        headers=AUTH,
        json={"label": "data-1", "region": "us-east", "size": 20},
    )
    assert volume.status_code == 200

    attach = client.post(
        f"/v4/volumes/{volume.json()['id']}/attach",
        headers=AUTH,
        json={"linode_id": instance["id"]},
    )
    assert attach.status_code == 200
    assert attach.json()["linode_id"] == instance["id"]


def test_vpc_and_bucket_creation() -> None:
    vpc = client.post(
        "/v4/vpcs",
        headers=AUTH,
        json={
            "label": "app-network",
            "region": "us-east",
            "subnets": [{"label": "private-a", "ipv4": "10.0.0.0/24"}],
        },
    )
    assert vpc.status_code == 200
    assert vpc.json()["label"] == "app-network"

    bucket = client.post(
        "/v4/object-storage/buckets",
        headers=AUTH,
        json={"label": "artifacts", "cluster": "us-east-1", "region": "us-east"},
    )
    assert bucket.status_code == 200
    assert bucket.json()["hostname"] == "artifacts.us-east-1.linodeobjects.com"
