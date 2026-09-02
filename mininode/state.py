from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from itertools import count
from math import ceil
from pathlib import Path
from typing import Any


NOW = "2026-09-02T00:00:00"

REGIONS = [
    {
        "id": "us-east",
        "label": "US East",
        "country": "us",
        "status": "ok",
        "capabilities": ["Linodes", "Block Storage", "NodeBalancers", "Object Storage", "VPCs"],
        "resolvers": {"ipv4": "139.144.18.18", "ipv6": "2a01:7e04::f03c:95ff:fead:d15a"},
    },
    {
        "id": "us-central",
        "label": "US Central",
        "country": "us",
        "status": "ok",
        "capabilities": ["Linodes", "Block Storage", "NodeBalancers", "Object Storage", "VPCs"],
        "resolvers": {"ipv4": "139.144.18.18", "ipv6": "2a01:7e04::f03c:95ff:fead:d15a"},
    },
    {
        "id": "eu-west",
        "label": "EU West",
        "country": "gb",
        "status": "ok",
        "capabilities": ["Linodes", "Block Storage", "NodeBalancers", "Object Storage", "VPCs"],
        "resolvers": {"ipv4": "139.144.18.18", "ipv6": "2a01:7e04::f03c:95ff:fead:d15a"},
    },
]

TYPES = [
    {
        "id": "g6-standard-1",
        "label": "Linode 2GB",
        "class": "standard",
        "disk": 51200,
        "memory": 2048,
        "network_out": 1000,
        "transfer": 2000,
        "vcpus": 1,
        "price": {"hourly": 0.018, "monthly": 12.0},
    },
    {
        "id": "g6-standard-2",
        "label": "Linode 4GB",
        "class": "standard",
        "disk": 81920,
        "memory": 4096,
        "network_out": 2000,
        "transfer": 4000,
        "vcpus": 2,
        "price": {"hourly": 0.036, "monthly": 24.0},
    },
]

IMAGES = [
    {"id": "linode/ubuntu24.04", "label": "Ubuntu 24.04 LTS", "vendor": "Linode", "type": "manual", "is_public": True},
    {"id": "linode/debian12", "label": "Debian 12", "vendor": "Linode", "type": "manual", "is_public": True},
    {"id": "linode/almalinux9", "label": "AlmaLinux 9", "vendor": "Linode", "type": "manual", "is_public": True},
]

OBJECT_STORAGE_CLUSTERS = [
    {"id": "us-east-1", "region": "us-east", "domain": "us-east-1.linodeobjects.com", "status": "available"},
    {"id": "us-central-1", "region": "us-central", "domain": "us-central-1.linodeobjects.com", "status": "available"},
    {"id": "eu-west-1", "region": "eu-west", "domain": "eu-west-1.linodeobjects.com", "status": "available"},
]

DATABASE_ENGINES = [
    {"id": "mysql/8", "engine": "mysql", "version": "8", "platform": "rdbms"},
    {"id": "postgresql/16", "engine": "postgresql", "version": "16", "platform": "rdbms"},
]

DATABASE_TYPES = [
    {"id": "g6-nanode-1", "label": "Nanode 1 GB", "class": "standard", "memory": 1024, "disk": 25600, "vcpus": 1},
    {"id": "g6-standard-1", "label": "Dedicated 2 GB", "class": "standard", "memory": 2048, "disk": 51200, "vcpus": 1},
]


def paginate(items: list[dict[str, Any]], page: int, page_size: int) -> dict[str, Any]:
    total = len(items)
    pages = ceil(total / page_size) if total else 1
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return {
        "page": page,
        "pages": pages,
        "results": total,
        "data": items[start:end],
    }


def clone(value: Any) -> Any:
    return deepcopy(value)


@dataclass
class ResourceStore:
    state_path: Path | None = None
    instances: dict[int, dict[str, Any]] = field(default_factory=dict)
    instance_disks: dict[int, dict[str, Any]] = field(default_factory=dict)
    instance_configs: dict[int, dict[str, Any]] = field(default_factory=dict)
    volumes: dict[int, dict[str, Any]] = field(default_factory=dict)
    vpcs: dict[int, dict[str, Any]] = field(default_factory=dict)
    nodebalancers: dict[int, dict[str, Any]] = field(default_factory=dict)
    firewalls: dict[int, dict[str, Any]] = field(default_factory=dict)
    domains: dict[int, dict[str, Any]] = field(default_factory=dict)
    domain_records: dict[int, dict[str, Any]] = field(default_factory=dict)
    databases: dict[int, dict[str, Any]] = field(default_factory=dict)
    events: dict[int, dict[str, Any]] = field(default_factory=dict)
    buckets: dict[str, dict[str, Any]] = field(default_factory=dict)
    next_instance_id: count = field(default_factory=lambda: count(1000))
    next_disk_id: count = field(default_factory=lambda: count(1500))
    next_config_id: count = field(default_factory=lambda: count(1750))
    next_volume_id: count = field(default_factory=lambda: count(2000))
    next_vpc_id: count = field(default_factory=lambda: count(3000))
    next_subnet_id: count = field(default_factory=lambda: count(3500))
    next_nodebalancer_id: count = field(default_factory=lambda: count(4000))
    next_firewall_id: count = field(default_factory=lambda: count(5000))
    next_domain_id: count = field(default_factory=lambda: count(6000))
    next_domain_record_id: count = field(default_factory=lambda: count(7000))
    next_database_id: count = field(default_factory=lambda: count(8000))
    next_event_id: count = field(default_factory=lambda: count(9000))

    def reset(self) -> None:
        self.instances.clear()
        self.instance_disks.clear()
        self.instance_configs.clear()
        self.volumes.clear()
        self.vpcs.clear()
        self.nodebalancers.clear()
        self.firewalls.clear()
        self.domains.clear()
        self.domain_records.clear()
        self.databases.clear()
        self.events.clear()
        self.buckets.clear()
        self.next_instance_id = count(1000)
        self.next_disk_id = count(1500)
        self.next_config_id = count(1750)
        self.next_volume_id = count(2000)
        self.next_vpc_id = count(3000)
        self.next_subnet_id = count(3500)
        self.next_nodebalancer_id = count(4000)
        self.next_firewall_id = count(5000)
        self.next_domain_id = count(6000)
        self.next_domain_record_id = count(7000)
        self.next_database_id = count(8000)
        self.next_event_id = count(9000)

    def configure(self, state_path: str | None) -> None:
        self.state_path = Path(state_path) if state_path else None

    def load(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return

        data = json.loads(self.state_path.read_text())
        self.instances = {int(key): value for key, value in data.get("instances", {}).items()}
        self.instance_disks = {int(key): value for key, value in data.get("instance_disks", {}).items()}
        self.instance_configs = {int(key): value for key, value in data.get("instance_configs", {}).items()}
        self.volumes = {int(key): value for key, value in data.get("volumes", {}).items()}
        self.vpcs = {int(key): value for key, value in data.get("vpcs", {}).items()}
        self.nodebalancers = {int(key): value for key, value in data.get("nodebalancers", {}).items()}
        self.firewalls = {int(key): value for key, value in data.get("firewalls", {}).items()}
        self.domains = {int(key): value for key, value in data.get("domains", {}).items()}
        self.domain_records = {int(key): value for key, value in data.get("domain_records", {}).items()}
        self.databases = {int(key): value for key, value in data.get("databases", {}).items()}
        self.events = {int(key): value for key, value in data.get("events", {}).items()}
        self.buckets = data.get("buckets", {})
        self.next_instance_id = count(data.get("next_instance_id", 1000))
        self.next_disk_id = count(data.get("next_disk_id", 1500))
        self.next_config_id = count(data.get("next_config_id", 1750))
        self.next_volume_id = count(data.get("next_volume_id", 2000))
        self.next_vpc_id = count(data.get("next_vpc_id", 3000))
        self.next_subnet_id = count(data.get("next_subnet_id", 3500))
        self.next_nodebalancer_id = count(data.get("next_nodebalancer_id", 4000))
        self.next_firewall_id = count(data.get("next_firewall_id", 5000))
        self.next_domain_id = count(data.get("next_domain_id", 6000))
        self.next_domain_record_id = count(data.get("next_domain_record_id", 7000))
        self.next_database_id = count(data.get("next_database_id", 8000))
        self.next_event_id = count(data.get("next_event_id", 9000))

    def save(self) -> None:
        if not self.state_path:
            return

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(
                {
                    "instances": self.instances,
                    "instance_disks": self.instance_disks,
                    "instance_configs": self.instance_configs,
                    "volumes": self.volumes,
                    "vpcs": self.vpcs,
                    "nodebalancers": self.nodebalancers,
                    "firewalls": self.firewalls,
                    "domains": self.domains,
                    "domain_records": self.domain_records,
                    "databases": self.databases,
                    "events": self.events,
                    "buckets": self.buckets,
                    "next_instance_id": self.next_counter_value("next_instance_id"),
                    "next_disk_id": self.next_counter_value("next_disk_id"),
                    "next_config_id": self.next_counter_value("next_config_id"),
                    "next_volume_id": self.next_counter_value("next_volume_id"),
                    "next_vpc_id": self.next_counter_value("next_vpc_id"),
                    "next_subnet_id": self.next_counter_value("next_subnet_id"),
                    "next_nodebalancer_id": self.next_counter_value("next_nodebalancer_id"),
                    "next_firewall_id": self.next_counter_value("next_firewall_id"),
                    "next_domain_id": self.next_counter_value("next_domain_id"),
                    "next_domain_record_id": self.next_counter_value("next_domain_record_id"),
                    "next_database_id": self.next_counter_value("next_database_id"),
                    "next_event_id": self.next_counter_value("next_event_id"),
                },
                indent=2,
                sort_keys=True,
            )
        )

    def next_counter_value(self, attr_name: str) -> int:
        counter = getattr(self, attr_name)
        value = next(counter)
        setattr(self, attr_name, count(value))
        return value

    def persist(self) -> None:
        self.save()

    def list_regions(self) -> list[dict[str, Any]]:
        return clone(REGIONS)

    def list_types(self) -> list[dict[str, Any]]:
        return clone(TYPES)

    def list_images(self) -> list[dict[str, Any]]:
        return clone(IMAGES)

    def list_clusters(self) -> list[dict[str, Any]]:
        return clone(OBJECT_STORAGE_CLUSTERS)

    def list_events(self) -> list[dict[str, Any]]:
        return clone(sorted(self.events.values(), key=lambda item: item["id"], reverse=True))

    def list_database_engines(self) -> list[dict[str, Any]]:
        return clone(DATABASE_ENGINES)

    def list_database_types(self) -> list[dict[str, Any]]:
        return clone(DATABASE_TYPES)

    def region_exists(self, region: str) -> bool:
        return any(item["id"] == region for item in REGIONS)

    def type_exists(self, linode_type: str) -> bool:
        return any(item["id"] == linode_type for item in TYPES)

    def image_exists(self, image: str) -> bool:
        return any(item["id"] == image for item in IMAGES)

    def cluster_exists(self, cluster: str) -> bool:
        return any(item["id"] == cluster for item in OBJECT_STORAGE_CLUSTERS)

    def database_engine_exists(self, engine: str) -> bool:
        return any(item["id"] == engine for item in DATABASE_ENGINES)

    def database_type_exists(self, database_type: str) -> bool:
        return any(item["id"] == database_type for item in DATABASE_TYPES)

    def create_instance(self, payload: dict[str, Any]) -> dict[str, Any]:
        instance_id = next(self.next_instance_id)
        instance = {
            "id": instance_id,
            "label": payload["label"],
            "region": payload["region"],
            "type": payload["type"],
            "image": payload.get("image"),
            "status": "running",
            "group": payload.get("group", ""),
            "tags": payload.get("tags", []),
            "ipv4": [f"192.168.128.{instance_id % 255}"],
            "ipv6": f"2600:3c00::f03c:95ff:fe00:{instance_id:x}/64",
            "hypervisor": "kvm",
            "specs": next(item for item in TYPES if item["id"] == payload["type"]),
            "alerts": {"cpu": 90, "io": 10000, "network_in": 10, "network_out": 10, "transfer_quota": 80},
            "backups": {"enabled": False, "available": False, "schedule": None, "last_successful": None},
            "created": NOW,
            "updated": NOW,
        }
        self.instances[instance_id] = instance
        self.record_event("linode_create", self.entity_ref("linode", instance_id, instance["label"], f"/v4/linode/instances/{instance_id}"))
        self.persist()
        return clone(instance)

    def update_instance(self, instance_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        instance = self.instances[instance_id]
        instance.update(updates)
        instance["updated"] = NOW
        self.record_event("linode_update", self.entity_ref("linode", instance_id, instance["label"], f"/v4/linode/instances/{instance_id}"))
        self.persist()
        return clone(instance)

    def set_instance_status(self, instance_id: int, status: str, action: str) -> dict[str, Any]:
        instance = self.instances[instance_id]
        instance["status"] = status
        instance["updated"] = NOW
        self.record_event(action, self.entity_ref("linode", instance_id, instance["label"], f"/v4/linode/instances/{instance_id}"))
        self.persist()
        return clone(instance)

    def create_disk(self, instance_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        disk_id = next(self.next_disk_id)
        disk = {
            "id": disk_id,
            "linode_id": instance_id,
            "label": payload["label"],
            "size": payload["size"],
            "filesystem": payload.get("filesystem", "ext4"),
            "status": "ready",
            "created": NOW,
            "updated": NOW,
        }
        self.instance_disks[disk_id] = disk
        self.record_event("disk_create", self.entity_ref("disk", disk_id, disk["label"], f"/v4/linode/instances/{instance_id}/disks/{disk_id}"), self.entity_ref("linode", instance_id, self.instances[instance_id]["label"], f"/v4/linode/instances/{instance_id}"))
        self.persist()
        return clone(disk)

    def list_disks(self, instance_id: int) -> list[dict[str, Any]]:
        return clone([disk for disk in self.instance_disks.values() if disk["linode_id"] == instance_id])

    def update_disk(self, disk_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        disk = self.instance_disks[disk_id]
        disk.update(updates)
        disk["updated"] = NOW
        self.record_event("disk_update", self.entity_ref("disk", disk_id, disk["label"], f"/v4/linode/instances/{disk['linode_id']}/disks/{disk_id}"))
        self.persist()
        return clone(disk)

    def create_config(self, instance_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        config_id = next(self.next_config_id)
        config = {
            "id": config_id,
            "linode_id": instance_id,
            "label": payload["label"],
            "kernel": payload.get("kernel", "linode/latest-64bit"),
            "comments": payload.get("comments", ""),
            "devices": payload.get("devices", {}),
            "helpers": payload.get(
                "helpers",
                {"updatedb_disabled": False, "distro": True, "modules_dep": True, "network": True},
            ),
            "interfaces": payload.get("interfaces", []),
            "root_device": payload.get("root_device", "/dev/sda"),
            "run_level": payload.get("run_level", "default"),
            "virt_mode": payload.get("virt_mode", "paravirt"),
            "created": NOW,
            "updated": NOW,
        }
        self.instance_configs[config_id] = config
        self.record_event("config_create", self.entity_ref("config", config_id, config["label"], f"/v4/linode/instances/{instance_id}/configs/{config_id}"), self.entity_ref("linode", instance_id, self.instances[instance_id]["label"], f"/v4/linode/instances/{instance_id}"))
        self.persist()
        return clone(config)

    def list_configs(self, instance_id: int) -> list[dict[str, Any]]:
        return clone([config for config in self.instance_configs.values() if config["linode_id"] == instance_id])

    def update_config(self, config_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        config = self.instance_configs[config_id]
        config.update(updates)
        config["updated"] = NOW
        self.record_event("config_update", self.entity_ref("config", config_id, config["label"], f"/v4/linode/instances/{config['linode_id']}/configs/{config_id}"))
        self.persist()
        return clone(config)

    def create_volume(self, payload: dict[str, Any]) -> dict[str, Any]:
        volume_id = next(self.next_volume_id)
        volume = {
            "id": volume_id,
            "label": payload["label"],
            "region": payload["region"],
            "size": payload["size"],
            "status": "active",
            "linode_id": payload.get("linode_id"),
            "tags": payload.get("tags", []),
            "filesystem_path": f"/dev/disk/by-id/scsi-0Linode_Volume_{volume_id}",
        }
        self.volumes[volume_id] = volume
        self.record_event("volume_create", self.entity_ref("volume", volume_id, volume["label"], f"/v4/volumes/{volume_id}"))
        self.persist()
        return clone(volume)

    def update_volume(self, volume_id: int, updates: dict[str, Any], action: str = "volume_update") -> dict[str, Any]:
        volume = self.volumes[volume_id]
        volume.update(updates)
        self.record_event(action, self.entity_ref("volume", volume_id, volume["label"], f"/v4/volumes/{volume_id}"))
        self.persist()
        return clone(volume)

    def create_vpc(self, payload: dict[str, Any]) -> dict[str, Any]:
        vpc_id = next(self.next_vpc_id)
        vpc = {
            "id": vpc_id,
            "label": payload["label"],
            "region": payload["region"],
            "description": payload.get("description", ""),
            "subnets": [self.build_subnet(subnet) for subnet in payload.get("subnets", [])],
            "created": NOW,
            "updated": NOW,
        }
        self.vpcs[vpc_id] = vpc
        self.record_event("vpc_create", self.entity_ref("vpc", vpc_id, vpc["label"], f"/v4/vpcs/{vpc_id}"))
        self.persist()
        return clone(vpc)

    def update_vpc(self, vpc_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        vpc = self.vpcs[vpc_id]
        if "subnets" in updates:
            updates["subnets"] = [self.build_subnet(subnet) for subnet in updates["subnets"]]
        vpc.update(updates)
        vpc["updated"] = NOW
        self.record_event("vpc_update", self.entity_ref("vpc", vpc_id, vpc["label"], f"/v4/vpcs/{vpc_id}"))
        self.persist()
        return clone(vpc)

    def build_subnet(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": next(self.next_subnet_id),
            "label": payload["label"],
            "ipv4": payload["ipv4"],
            "created": NOW,
            "updated": NOW,
        }

    def create_subnet(self, vpc_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        vpc = self.vpcs[vpc_id]
        subnet = self.build_subnet(payload)
        vpc.setdefault("subnets", []).append(subnet)
        vpc["updated"] = NOW
        self.record_event("subnet_create", self.entity_ref("subnet", subnet["id"], subnet["label"], f"/v4/vpcs/{vpc_id}/subnets/{subnet['id']}"), self.entity_ref("vpc", vpc_id, vpc["label"], f"/v4/vpcs/{vpc_id}"))
        self.persist()
        return clone(subnet)

    def update_subnet(self, vpc_id: int, subnet_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        subnet = self.get_subnet(vpc_id, subnet_id)
        subnet.update(updates)
        subnet["updated"] = NOW
        self.vpcs[vpc_id]["updated"] = NOW
        self.record_event("subnet_update", self.entity_ref("subnet", subnet_id, subnet["label"], f"/v4/vpcs/{vpc_id}/subnets/{subnet_id}"))
        self.persist()
        return clone(subnet)

    def get_subnet(self, vpc_id: int, subnet_id: int) -> dict[str, Any]:
        for subnet in self.vpcs[vpc_id].get("subnets", []):
            if subnet["id"] == subnet_id:
                return subnet
        raise KeyError(subnet_id)

    def delete_subnet(self, vpc_id: int, subnet_id: int) -> None:
        vpc = self.vpcs[vpc_id]
        subnet = self.get_subnet(vpc_id, subnet_id)
        vpc["subnets"] = [item for item in vpc.get("subnets", []) if item["id"] != subnet_id]
        vpc["updated"] = NOW
        self.record_event("subnet_delete", self.entity_ref("subnet", subnet_id, subnet["label"], f"/v4/vpcs/{vpc_id}/subnets/{subnet_id}"), self.entity_ref("vpc", vpc_id, vpc["label"], f"/v4/vpcs/{vpc_id}"))
        self.persist()

    def create_nodebalancer(self, payload: dict[str, Any]) -> dict[str, Any]:
        nodebalancer_id = next(self.next_nodebalancer_id)
        nodebalancer = {
            "id": nodebalancer_id,
            "label": payload["label"],
            "region": payload["region"],
            "hostname": f"nb-{nodebalancer_id}.members.linode.com",
            "ipv4": f"172.233.{nodebalancer_id % 255}.10",
            "client_conn_throttle": payload.get("client_conn_throttle", 0),
            "tags": payload.get("tags", []),
            "transfer": {"total": 0, "out": 0, "in": 0},
        }
        self.nodebalancers[nodebalancer_id] = nodebalancer
        self.record_event("nodebalancer_create", self.entity_ref("nodebalancer", nodebalancer_id, nodebalancer["label"], f"/v4/nodebalancers/{nodebalancer_id}"))
        self.persist()
        return clone(nodebalancer)

    def update_nodebalancer(self, nodebalancer_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        nodebalancer = self.nodebalancers[nodebalancer_id]
        nodebalancer.update(updates)
        self.record_event("nodebalancer_update", self.entity_ref("nodebalancer", nodebalancer_id, nodebalancer["label"], f"/v4/nodebalancers/{nodebalancer_id}"))
        self.persist()
        return clone(nodebalancer)

    def create_firewall(self, payload: dict[str, Any]) -> dict[str, Any]:
        firewall_id = next(self.next_firewall_id)
        firewall = {
            "id": firewall_id,
            "label": payload["label"],
            "status": "enabled",
            "tags": payload.get("tags", []),
            "rules": payload.get("rules", {"inbound": [], "outbound": []}),
            "linodes": payload.get("linodes", []),
            "created": NOW,
            "updated": NOW,
        }
        self.firewalls[firewall_id] = firewall
        self.record_event("firewall_create", self.entity_ref("firewall", firewall_id, firewall["label"], f"/v4/networking/firewalls/{firewall_id}"))
        self.persist()
        return clone(firewall)

    def update_firewall(self, firewall_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        firewall = self.firewalls[firewall_id]
        firewall.update(updates)
        firewall["updated"] = NOW
        self.record_event("firewall_update", self.entity_ref("firewall", firewall_id, firewall["label"], f"/v4/networking/firewalls/{firewall_id}"))
        self.persist()
        return clone(firewall)

    def create_bucket(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = self.bucket_key(payload["cluster"], payload["label"])
        bucket = {
            "label": payload["label"],
            "cluster": payload["cluster"],
            "region": payload["region"],
            "hostname": f"{payload['label']}.{payload['cluster']}.linodeobjects.com",
            "created": NOW,
            "objects": 0,
            "size": 0,
        }
        self.buckets[key] = bucket
        self.record_event("bucket_create", self.entity_ref("bucket", payload["label"], bucket["label"], f"/v4/object-storage/buckets/{payload['cluster']}/{payload['label']}"))
        self.persist()
        return clone(bucket)

    def create_domain(self, payload: dict[str, Any]) -> dict[str, Any]:
        domain_id = next(self.next_domain_id)
        domain = {
            "id": domain_id,
            "domain": payload["domain"],
            "type": payload.get("type", "master"),
            "group": payload.get("group", ""),
            "status": "active",
            "description": payload.get("description", ""),
            "soa_email": payload.get("soa_email", "admin@example.test"),
            "retry_sec": payload.get("retry_sec", 300),
            "master_ips": payload.get("master_ips", []),
            "axfr_ips": payload.get("axfr_ips", []),
            "tags": payload.get("tags", []),
            "created": NOW,
            "updated": NOW,
        }
        self.domains[domain_id] = domain
        self.record_event("domain_create", self.entity_ref("domain", domain_id, domain["domain"], f"/v4/domains/{domain_id}"))
        self.persist()
        return clone(domain)

    def update_domain(self, domain_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        domain = self.domains[domain_id]
        domain.update(updates)
        domain["updated"] = NOW
        self.record_event("domain_update", self.entity_ref("domain", domain_id, domain["domain"], f"/v4/domains/{domain_id}"))
        self.persist()
        return clone(domain)

    def create_domain_record(self, domain_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        record_id = next(self.next_domain_record_id)
        record = {
            "id": record_id,
            "domain_id": domain_id,
            "type": payload["type"],
            "name": payload.get("name", ""),
            "target": payload["target"],
            "priority": payload.get("priority", 0),
            "weight": payload.get("weight", 0),
            "port": payload.get("port", 0),
            "service": payload.get("service", ""),
            "protocol": payload.get("protocol", ""),
            "ttl_sec": payload.get("ttl_sec", 300),
            "tag": payload.get("tag", ""),
            "created": NOW,
            "updated": NOW,
        }
        self.domain_records[record_id] = record
        self.record_event("domain_record_create", self.entity_ref("domain_record", record_id, record["name"] or record["type"], f"/v4/domains/{domain_id}/records/{record_id}"), self.entity_ref("domain", domain_id, self.domains[domain_id]["domain"], f"/v4/domains/{domain_id}"))
        self.persist()
        return clone(record)

    def list_domain_records(self, domain_id: int) -> list[dict[str, Any]]:
        return clone([record for record in self.domain_records.values() if record["domain_id"] == domain_id])

    def update_domain_record(self, record_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        record = self.domain_records[record_id]
        record.update(updates)
        record["updated"] = NOW
        self.record_event("domain_record_update", self.entity_ref("domain_record", record_id, record["name"] or record["type"], f"/v4/domains/{record['domain_id']}/records/{record_id}"))
        self.persist()
        return clone(record)

    def create_event(self, payload: dict[str, Any]) -> None:
        event_id = next(self.next_event_id)
        self.events[event_id] = {
            "id": event_id,
            "action": payload["action"],
            "created": NOW,
            "seen": False,
            "read": False,
            "status": payload.get("status", "finished"),
            "percent_complete": payload.get("percent_complete", 100),
            "time_remaining": None,
            "rate": None,
            "username": "mininode",
            "entity": payload.get("entity"),
            "secondary_entity": payload.get("secondary_entity"),
        }

    def record_event(self, action: str, entity: dict[str, Any] | None, secondary_entity: dict[str, Any] | None = None) -> None:
        self.create_event({"action": action, "entity": entity, "secondary_entity": secondary_entity})

    def create_database(self, payload: dict[str, Any]) -> dict[str, Any]:
        database_id = next(self.next_database_id)
        database = {
            "id": database_id,
            "label": payload["label"],
            "engine": payload["engine"],
            "type": payload["type"],
            "region": payload["region"],
            "status": "active",
            "allow_list": payload.get("allow_list", []),
            "cluster_size": payload.get("cluster_size", 1),
            "encrypted": True,
            "hosts": {
                "primary": f"db-{database_id}.mininode.local",
                "standby": None,
            },
            "port": 3306 if payload["engine"].startswith("mysql") else 5432,
            "ssl_connection": True,
            "updates": {"day_of_week": 0, "duration": 1, "frequency": "weekly", "hour_of_day": 3, "week_of_month": None},
            "created": NOW,
            "updated": NOW,
            "credentials": {
                "username": payload.get("username", "linodeadmin"),
                "password": payload.get("password", f"mininode-{database_id}"),
            },
        }
        self.databases[database_id] = database
        self.record_event("database_create", self.entity_ref("database", database_id, database["label"], f"/v4/databases/instances/{database_id}"))
        self.persist()
        return clone(database)

    def update_database(self, database_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        database = self.databases[database_id]
        database.update(updates)
        database["updated"] = NOW
        self.record_event("database_update", self.entity_ref("database", database_id, database["label"], f"/v4/databases/instances/{database_id}"))
        self.persist()
        return clone(database)

    def reset_database_credentials(self, database_id: int) -> dict[str, Any]:
        database = self.databases[database_id]
        database["credentials"] = {
            "username": database["credentials"]["username"],
            "password": f"mininode-{database_id}-reset",
        }
        database["updated"] = NOW
        self.record_event("database_credentials_reset", self.entity_ref("database", database_id, database["label"], f"/v4/databases/instances/{database_id}"))
        self.persist()
        return clone(database["credentials"])

    @staticmethod
    def entity_ref(resource_type: str, resource_id: int | str, label: str, url: str) -> dict[str, Any]:
        return {"type": resource_type, "id": resource_id, "label": label, "url": url}

    def delete_instance(self, instance_id: int) -> None:
        instance = self.instances[instance_id]
        self.instance_disks = {disk_id: disk for disk_id, disk in self.instance_disks.items() if disk["linode_id"] != instance_id}
        self.instance_configs = {config_id: config for config_id, config in self.instance_configs.items() if config["linode_id"] != instance_id}
        del self.instances[instance_id]
        self.record_event("linode_delete", self.entity_ref("linode", instance_id, instance["label"], f"/v4/linode/instances/{instance_id}"))
        self.persist()

    def delete_disk(self, disk_id: int) -> None:
        disk = self.instance_disks[disk_id]
        del self.instance_disks[disk_id]
        self.record_event("disk_delete", self.entity_ref("disk", disk_id, disk["label"], f"/v4/linode/instances/{disk['linode_id']}/disks/{disk_id}"))
        self.persist()

    def delete_config(self, config_id: int) -> None:
        config = self.instance_configs[config_id]
        del self.instance_configs[config_id]
        self.record_event("config_delete", self.entity_ref("config", config_id, config["label"], f"/v4/linode/instances/{config['linode_id']}/configs/{config_id}"))
        self.persist()

    def delete_volume(self, volume_id: int) -> None:
        volume = self.volumes[volume_id]
        del self.volumes[volume_id]
        self.record_event("volume_delete", self.entity_ref("volume", volume_id, volume["label"], f"/v4/volumes/{volume_id}"))
        self.persist()

    def delete_vpc(self, vpc_id: int) -> None:
        vpc = self.vpcs[vpc_id]
        del self.vpcs[vpc_id]
        self.record_event("vpc_delete", self.entity_ref("vpc", vpc_id, vpc["label"], f"/v4/vpcs/{vpc_id}"))
        self.persist()

    def delete_nodebalancer(self, nodebalancer_id: int) -> None:
        nodebalancer = self.nodebalancers[nodebalancer_id]
        del self.nodebalancers[nodebalancer_id]
        self.record_event("nodebalancer_delete", self.entity_ref("nodebalancer", nodebalancer_id, nodebalancer["label"], f"/v4/nodebalancers/{nodebalancer_id}"))
        self.persist()

    def delete_firewall(self, firewall_id: int) -> None:
        firewall = self.firewalls[firewall_id]
        del self.firewalls[firewall_id]
        self.record_event("firewall_delete", self.entity_ref("firewall", firewall_id, firewall["label"], f"/v4/networking/firewalls/{firewall_id}"))
        self.persist()

    def delete_domain(self, domain_id: int) -> None:
        domain = self.domains[domain_id]
        self.domain_records = {record_id: record for record_id, record in self.domain_records.items() if record["domain_id"] != domain_id}
        del self.domains[domain_id]
        self.record_event("domain_delete", self.entity_ref("domain", domain_id, domain["domain"], f"/v4/domains/{domain_id}"))
        self.persist()

    def delete_domain_record(self, record_id: int) -> None:
        record = self.domain_records[record_id]
        del self.domain_records[record_id]
        self.record_event("domain_record_delete", self.entity_ref("domain_record", record_id, record["name"] or record["type"], f"/v4/domains/{record['domain_id']}/records/{record_id}"))
        self.persist()

    def delete_database(self, database_id: int) -> None:
        database = self.databases[database_id]
        del self.databases[database_id]
        self.record_event("database_delete", self.entity_ref("database", database_id, database["label"], f"/v4/databases/instances/{database_id}"))
        self.persist()

    def delete_bucket(self, key: str) -> None:
        bucket = self.buckets[key]
        del self.buckets[key]
        self.record_event("bucket_delete", self.entity_ref("bucket", bucket["label"], bucket["label"], f"/v4/object-storage/buckets/{bucket['cluster']}/{bucket['label']}"))
        self.persist()

    @staticmethod
    def bucket_key(cluster: str, label: str) -> str:
        return f"{cluster}:{label}"


store = ResourceStore()
