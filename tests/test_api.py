import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mininode.app import app
from mininode.state import store


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture(autouse=True)
def reset_store() -> None:
    store.configure(None)
    store.reset()


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

    update = client.put(
        f"/v4/linode/instances/{instance['id']}",
        headers=AUTH,
        json={"label": "web-1-renamed", "tags": ["frontend"]},
    )
    assert update.status_code == 200
    assert update.json()["label"] == "web-1-renamed"
    assert update.json()["tags"] == ["frontend"]

    events = client.get("/v4/account/events", headers=AUTH)
    assert events.status_code == 200
    assert events.json()["results"] >= 4
    assert events.json()["data"][0]["action"] in {"linode_update", "linode_reboot"}


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


def test_vpc_subnet_lifecycle() -> None:
    vpc = client.post(
        "/v4/vpcs",
        headers=AUTH,
        json={"label": "network-a", "region": "us-east"},
    ).json()

    subnet = client.post(
        f"/v4/vpcs/{vpc['id']}/subnets",
        headers=AUTH,
        json={"label": "private-a", "ipv4": "10.10.0.0/24"},
    )
    assert subnet.status_code == 200
    subnet_id = subnet.json()["id"]

    updated = client.put(
        f"/v4/vpcs/{vpc['id']}/subnets/{subnet_id}",
        headers=AUTH,
        json={"label": "private-b", "ipv4": "10.10.1.0/24"},
    )
    assert updated.status_code == 200
    assert updated.json()["label"] == "private-b"

    listed = client.get(f"/v4/vpcs/{vpc['id']}/subnets", headers=AUTH)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_firewall_lifecycle() -> None:
    instance = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "fw-node",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
        },
    ).json()

    firewall = client.post(
        "/v4/networking/firewalls",
        headers=AUTH,
        json={
            "label": "edge-fw",
            "linodes": [instance["id"]],
            "rules": {
                "inbound": [{"action": "ACCEPT", "ports": "80", "protocol": "TCP", "addresses": {"ipv4": ["0.0.0.0/0"]}}],
                "outbound": [],
            },
        },
    )
    assert firewall.status_code == 200
    firewall_id = firewall.json()["id"]

    fetched = client.get(f"/v4/networking/firewalls/{firewall_id}", headers=AUTH)
    assert fetched.status_code == 200
    assert fetched.json()["linodes"] == [instance["id"]]

    updated = client.put(
        f"/v4/networking/firewalls/{firewall_id}",
        headers=AUTH,
        json={"tags": ["public-edge"]},
    )
    assert updated.status_code == 200
    assert updated.json()["tags"] == ["public-edge"]


def test_filter_and_ordering() -> None:
    client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "z-last",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
        },
    )
    client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "a-first",
            "region": "eu-west",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
        },
    )

    response = client.get(
        "/v4/linode/instances",
        headers=AUTH,
        params={"+filter": json.dumps({"region": "eu-west"}), "+order_by": "label", "+order": "asc"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == 1
    assert body["data"][0]["label"] == "a-first"


def test_disk_and_config_lifecycle() -> None:
    instance = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "vm-a",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
        },
    ).json()

    disk = client.post(
        f"/v4/linode/instances/{instance['id']}/disks",
        headers=AUTH,
        json={"label": "root-disk", "size": 20480, "filesystem": "ext4"},
    )
    assert disk.status_code == 200
    disk_id = disk.json()["id"]

    disk_update = client.put(
        f"/v4/linode/instances/{instance['id']}/disks/{disk_id}",
        headers=AUTH,
        json={"label": "root-disk-renamed"},
    )
    assert disk_update.status_code == 200
    assert disk_update.json()["label"] == "root-disk-renamed"

    config = client.post(
        f"/v4/linode/instances/{instance['id']}/configs",
        headers=AUTH,
        json={
            "label": "primary-config",
            "kernel": "linode/latest-64bit",
            "devices": {"sda": {"disk_id": disk_id}},
            "interfaces": [{"purpose": "public"}],
        },
    )
    assert config.status_code == 200
    config_id = config.json()["id"]

    fetched = client.get(f"/v4/linode/instances/{instance['id']}/configs/{config_id}", headers=AUTH)
    assert fetched.status_code == 200
    assert fetched.json()["devices"]["sda"]["disk_id"] == disk_id

    listed_disks = client.get(f"/v4/linode/instances/{instance['id']}/disks", headers=AUTH)
    assert listed_disks.status_code == 200
    assert len(listed_disks.json()) == 1

    listed_configs = client.get(f"/v4/linode/instances/{instance['id']}/configs", headers=AUTH)
    assert listed_configs.status_code == 200
    assert len(listed_configs.json()) == 1


def test_events_include_secondary_entity() -> None:
    vpc = client.post(
        "/v4/vpcs",
        headers=AUTH,
        json={"label": "network-b", "region": "us-east"},
    ).json()

    client.post(
        f"/v4/vpcs/{vpc['id']}/subnets",
        headers=AUTH,
        json={"label": "private-c", "ipv4": "10.30.0.0/24"},
    )

    events = client.get(
        "/v4/account/events",
        headers=AUTH,
        params={"+filter": json.dumps({"action": "subnet_create"})},
    )
    assert events.status_code == 200
    assert events.json()["results"] == 1
    assert events.json()["data"][0]["secondary_entity"]["type"] == "vpc"


def test_domain_and_record_lifecycle() -> None:
    domain = client.post(
        "/v4/domains",
        headers=AUTH,
        json={
            "domain": "example.test",
            "type": "master",
            "soa_email": "dns@example.test",
            "tags": ["public"],
        },
    )
    assert domain.status_code == 200
    domain_id = domain.json()["id"]

    record = client.post(
        f"/v4/domains/{domain_id}/records",
        headers=AUTH,
        json={"type": "A", "name": "app", "target": "192.0.2.10", "ttl_sec": 300},
    )
    assert record.status_code == 200
    record_id = record.json()["id"]

    updated_domain = client.put(
        f"/v4/domains/{domain_id}",
        headers=AUTH,
        json={"description": "Primary zone"},
    )
    assert updated_domain.status_code == 200
    assert updated_domain.json()["description"] == "Primary zone"

    updated_record = client.put(
        f"/v4/domains/{domain_id}/records/{record_id}",
        headers=AUTH,
        json={"target": "192.0.2.20"},
    )
    assert updated_record.status_code == 200
    assert updated_record.json()["target"] == "192.0.2.20"

    records = client.get(f"/v4/domains/{domain_id}/records", headers=AUTH)
    assert records.status_code == 200
    assert len(records.json()) == 1

    events = client.get(
        "/v4/account/events",
        headers=AUTH,
        params={"+filter": json.dumps({"action": "domain_record_create"})},
    )
    assert events.status_code == 200
    assert events.json()["results"] == 1
    assert events.json()["data"][0]["secondary_entity"]["type"] == "domain"


def test_database_lifecycle() -> None:
    created = client.post(
        "/v4/databases/instances",
        headers=AUTH,
        json={
            "label": "app-db",
            "engine": "postgresql/16",
            "type": "g6-standard-1",
            "region": "us-east",
            "allow_list": ["10.0.0.0/24"],
        },
    )
    assert created.status_code == 200
    database = created.json()
    assert database["port"] == 5432

    fetched = client.get(f"/v4/databases/instances/{database['id']}", headers=AUTH)
    assert fetched.status_code == 200
    assert fetched.json()["hosts"]["primary"] == f"db-{database['id']}.mininode.local"

    credentials = client.get(f"/v4/databases/instances/{database['id']}/credentials", headers=AUTH)
    assert credentials.status_code == 200
    assert credentials.json()["username"] == "linodeadmin"

    reset = client.post(f"/v4/databases/instances/{database['id']}/credentials/reset", headers=AUTH)
    assert reset.status_code == 200
    assert reset.json()["password"] == f"mininode-{database['id']}-reset"

    updated = client.put(
        f"/v4/databases/instances/{database['id']}",
        headers=AUTH,
        json={"cluster_size": 2},
    )
    assert updated.status_code == 200
    assert updated.json()["cluster_size"] == 2

    events = client.get(
        "/v4/account/events",
        headers=AUTH,
        params={"+filter": json.dumps({"action": "database_create"})},
    )
    assert events.status_code == 200
    assert events.json()["results"] == 1


def test_ssh_keys_and_instance_authorized_keys() -> None:
    key = client.post(
        "/v4/profile/sshkeys",
        headers=AUTH,
        json={"label": "laptop", "ssh_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey user@example"},
    )
    assert key.status_code == 200
    ssh_key = key.json()

    listed = client.get("/v4/profile/sshkeys", headers=AUTH)
    assert listed.status_code == 200
    assert listed.json()["results"] == 1

    updated = client.put(
        f"/v4/profile/sshkeys/{ssh_key['id']}",
        headers=AUTH,
        json={"label": "work-laptop"},
    )
    assert updated.status_code == 200
    assert updated.json()["label"] == "work-laptop"

    instance = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "ssh-node",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
            "authorized_keys": [ssh_key["ssh_key"]],
        },
    )
    assert instance.status_code == 200
    assert instance.json()["authorized_keys"] == [ssh_key["ssh_key"]]

    missing = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "bad-node",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
            "authorized_keys": ["ssh-ed25519 missing"],
        },
    )
    assert missing.status_code == 404


def test_stackscript_lifecycle_and_instance_linkage() -> None:
    stackscript = client.post(
        "/v4/stackscripts",
        headers=AUTH,
        json={
            "label": "bootstrap-nginx",
            "script": "#!/bin/bash\necho hello",
            "images": ["linode/ubuntu24.04"],
            "user_defined_fields": [{"name": "hostname", "label": "Hostname"}],
        },
    )
    assert stackscript.status_code == 200
    stackscript_id = stackscript.json()["id"]

    updated = client.put(
        f"/v4/stackscripts/{stackscript_id}",
        headers=AUTH,
        json={"description": "Install nginx and bootstrap app"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Install nginx and bootstrap app"

    instance = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "scripted-node",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
            "stackscript_id": stackscript_id,
            "stackscript_data": {"hostname": "web-1"},
        },
    )
    assert instance.status_code == 200
    assert instance.json()["stackscript_id"] == stackscript_id
    assert instance.json()["stackscript_data"] == {"hostname": "web-1"}

    fetched = client.get(f"/v4/stackscripts/{stackscript_id}", headers=AUTH)
    assert fetched.status_code == 200
    assert fetched.json()["deployments_total"] == 1

    missing = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "bad-scripted-node",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
            "stackscript_id": 999999,
        },
    )
    assert missing.status_code == 404


def test_nodebalancer_config_and_node_lifecycle() -> None:
    nodebalancer = client.post(
        "/v4/nodebalancers",
        headers=AUTH,
        json={"label": "public-lb", "region": "us-east"},
    )
    assert nodebalancer.status_code == 200
    nodebalancer_id = nodebalancer.json()["id"]

    config = client.post(
        f"/v4/nodebalancers/{nodebalancer_id}/configs",
        headers=AUTH,
        json={"port": 80, "protocol": "http", "algorithm": "roundrobin"},
    )
    assert config.status_code == 200
    config_id = config.json()["id"]

    updated_config = client.put(
        f"/v4/nodebalancers/{nodebalancer_id}/configs/{config_id}",
        headers=AUTH,
        json={"check": "http", "check_interval": 10},
    )
    assert updated_config.status_code == 200
    assert updated_config.json()["check"] == "http"

    node = client.post(
        f"/v4/nodebalancers/{nodebalancer_id}/configs/{config_id}/nodes",
        headers=AUTH,
        json={"label": "web-1", "address": "10.0.0.10:80", "weight": 75},
    )
    assert node.status_code == 200
    node_id = node.json()["id"]

    updated_node = client.put(
        f"/v4/nodebalancers/{nodebalancer_id}/configs/{config_id}/nodes/{node_id}",
        headers=AUTH,
        json={"mode": "drain"},
    )
    assert updated_node.status_code == 200
    assert updated_node.json()["mode"] == "drain"

    nodes = client.get(f"/v4/nodebalancers/{nodebalancer_id}/configs/{config_id}/nodes", headers=AUTH)
    assert nodes.status_code == 200
    assert len(nodes.json()) == 1


def test_instance_backup_lifecycle() -> None:
    instance = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "backup-node",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
        },
    ).json()

    backups = client.get(f"/v4/linode/instances/{instance['id']}/backups", headers=AUTH)
    assert backups.status_code == 200
    assert backups.json()["enabled"] is False

    enabled = client.post(f"/v4/linode/instances/{instance['id']}/backups/enable", headers=AUTH)
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True

    snapshot = client.post(f"/v4/linode/instances/{instance['id']}/backups", headers=AUTH)
    assert snapshot.status_code == 200
    backup_id = snapshot.json()["id"]

    fetched = client.get(f"/v4/linode/instances/{instance['id']}/backups/{backup_id}", headers=AUTH)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "successful"

    restored = client.post(f"/v4/linode/instances/{instance['id']}/backups/{backup_id}/restore", headers=AUTH)
    assert restored.status_code == 200
    assert restored.json()["id"] == backup_id

    cancelled = client.post(f"/v4/linode/instances/{instance['id']}/backups/cancel", headers=AUTH)
    assert cancelled.status_code == 200
    assert cancelled.json()["enabled"] is False


def test_vlan_lifecycle_and_instance_attachment() -> None:
    instance = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "vlan-node",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
        },
    ).json()

    vlan = client.post(
        "/v4/networking/vlans",
        headers=AUTH,
        json={"label": "private-vlan", "region": "us-east", "description": "east private network"},
    )
    assert vlan.status_code == 200
    vlan_id = vlan.json()["id"]

    attached = client.post(
        f"/v4/networking/vlans/{vlan_id}/attach",
        headers=AUTH,
        json={"linode_id": instance["id"], "ipam_address": "10.20.0.10/24"},
    )
    assert attached.status_code == 200
    assert attached.json()["vlan_id"] == vlan_id

    fetched_vlan = client.get(f"/v4/networking/vlans/{vlan_id}", headers=AUTH)
    assert fetched_vlan.status_code == 200
    assert fetched_vlan.json()["linodes"] == [instance["id"]]

    detached = client.post(
        f"/v4/networking/vlans/{vlan_id}/detach",
        headers=AUTH,
        json={"linode_id": instance["id"]},
    )
    assert detached.status_code == 200
    assert detached.json()["detached"] == str(instance["id"])


def test_store_persistence(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    store.configure(str(state_file))
    store.reset()

    created = client.post(
        "/v4/linode/instances",
        headers=AUTH,
        json={
            "label": "persisted-1",
            "region": "us-east",
            "type": "g6-standard-1",
            "image": "linode/ubuntu24.04",
        },
    )
    assert created.status_code == 200
    assert state_file.exists()

    store.reset()
    assert store.instances == {}

    store.configure(str(state_file))
    store.load()
    assert len(store.instances) == 1
    restored = next(iter(store.instances.values()))
    assert restored["label"] == "persisted-1"
    assert len(store.events) >= 1
