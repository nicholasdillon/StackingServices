from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from itertools import count
from math import ceil
from typing import Any


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
    instances: dict[int, dict[str, Any]] = field(default_factory=dict)
    volumes: dict[int, dict[str, Any]] = field(default_factory=dict)
    vpcs: dict[int, dict[str, Any]] = field(default_factory=dict)
    nodebalancers: dict[int, dict[str, Any]] = field(default_factory=dict)
    buckets: dict[str, dict[str, Any]] = field(default_factory=dict)
    next_instance_id: count = field(default_factory=lambda: count(1000))
    next_volume_id: count = field(default_factory=lambda: count(2000))
    next_vpc_id: count = field(default_factory=lambda: count(3000))
    next_nodebalancer_id: count = field(default_factory=lambda: count(4000))

    def reset(self) -> None:
        self.instances.clear()
        self.volumes.clear()
        self.vpcs.clear()
        self.nodebalancers.clear()
        self.buckets.clear()
        self.next_instance_id = count(1000)
        self.next_volume_id = count(2000)
        self.next_vpc_id = count(3000)
        self.next_nodebalancer_id = count(4000)

    def list_regions(self) -> list[dict[str, Any]]:
        return clone(REGIONS)

    def list_types(self) -> list[dict[str, Any]]:
        return clone(TYPES)

    def list_images(self) -> list[dict[str, Any]]:
        return clone(IMAGES)

    def list_clusters(self) -> list[dict[str, Any]]:
        return clone(OBJECT_STORAGE_CLUSTERS)

    def region_exists(self, region: str) -> bool:
        return any(item["id"] == region for item in REGIONS)

    def type_exists(self, linode_type: str) -> bool:
        return any(item["id"] == linode_type for item in TYPES)

    def image_exists(self, image: str) -> bool:
        return any(item["id"] == image for item in IMAGES)

    def cluster_exists(self, cluster: str) -> bool:
        return any(item["id"] == cluster for item in OBJECT_STORAGE_CLUSTERS)

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
        }
        self.instances[instance_id] = instance
        return clone(instance)

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
        return clone(volume)

    def create_vpc(self, payload: dict[str, Any]) -> dict[str, Any]:
        vpc_id = next(self.next_vpc_id)
        vpc = {
            "id": vpc_id,
            "label": payload["label"],
            "region": payload["region"],
            "description": payload.get("description", ""),
            "subnets": payload.get("subnets", []),
            "created": "2026-09-02T00:00:00",
            "updated": "2026-09-02T00:00:00",
        }
        self.vpcs[vpc_id] = vpc
        return clone(vpc)

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
        return clone(nodebalancer)

    def create_bucket(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = self.bucket_key(payload["cluster"], payload["label"])
        bucket = {
            "label": payload["label"],
            "cluster": payload["cluster"],
            "region": payload["region"],
            "hostname": f"{payload['label']}.{payload['cluster']}.linodeobjects.com",
            "created": "2026-09-02T00:00:00",
            "objects": 0,
            "size": 0,
        }
        self.buckets[key] = bucket
        return clone(bucket)

    @staticmethod
    def bucket_key(cluster: str, label: str) -> str:
        return f"{cluster}:{label}"


store = ResourceStore()
