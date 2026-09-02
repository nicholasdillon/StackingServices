from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from mininode.state import paginate, store


def error_response(reason: str, field: str | None = None, code: int = status.HTTP_400_BAD_REQUEST) -> None:
    detail: dict[str, Any] = {"reason": reason}
    if field:
        detail["field"] = field
    raise HTTPException(status_code=code, detail={"errors": [detail]})


async def require_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        error_response("Expected Bearer token in Authorization header.", code=status.HTTP_401_UNAUTHORIZED)
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        error_response("Bearer token cannot be empty.", code=status.HTTP_401_UNAUTHORIZED)
    return token


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.configure(os.getenv("MININODE_STATE_PATH"))
    if store.state_path:
        store.load()
    else:
        store.reset()
    yield


app = FastAPI(title="MiniNode", version="0.1.0", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def linode_http_exception_handler(_, exc: HTTPException):
    if isinstance(exc.detail, dict) and "errors" in exc.detail:
        body = exc.detail
    else:
        body = {"errors": [{"reason": str(exc.detail)}]}
    return Response(content=json.dumps(body), media_type="application/json", status_code=exc.status_code)


class InstanceCreate(BaseModel):
    label: str = Field(min_length=1)
    region: str
    type: str
    image: str | None = None
    group: str | None = None
    tags: list[str] = Field(default_factory=list)
    authorized_keys: list[str] = Field(default_factory=list)


class VolumeCreate(BaseModel):
    label: str = Field(min_length=1)
    region: str
    size: int = Field(ge=10)
    linode_id: int | None = None
    tags: list[str] = Field(default_factory=list)


class VolumeAttach(BaseModel):
    linode_id: int


class VpcSubnet(BaseModel):
    label: str
    ipv4: str


class VpcCreate(BaseModel):
    label: str = Field(min_length=1)
    region: str
    description: str | None = None
    subnets: list[VpcSubnet] = Field(default_factory=list)


class NodeBalancerCreate(BaseModel):
    label: str = Field(min_length=1)
    region: str
    client_conn_throttle: int = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)


class BucketCreate(BaseModel):
    label: str = Field(min_length=3)
    cluster: str
    region: str


class InstanceUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    group: str | None = None
    tags: list[str] | None = None


class VolumeUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None


class VpcUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    description: str | None = None
    subnets: list[VpcSubnet] | None = None


class NodeBalancerUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    client_conn_throttle: int | None = Field(default=None, ge=0)
    tags: list[str] | None = None


class FirewallRules(BaseModel):
    inbound: list[dict[str, Any]] = Field(default_factory=list)
    outbound: list[dict[str, Any]] = Field(default_factory=list)


class FirewallCreate(BaseModel):
    label: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    linodes: list[int] = Field(default_factory=list)
    rules: FirewallRules = Field(default_factory=FirewallRules)


class FirewallUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    linodes: list[int] | None = None
    rules: FirewallRules | None = None


class DiskCreate(BaseModel):
    label: str = Field(min_length=1)
    size: int = Field(ge=1)
    filesystem: str | None = None


class DiskUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    filesystem: str | None = None


class ConfigCreate(BaseModel):
    label: str = Field(min_length=1)
    kernel: str | None = None
    comments: str | None = None
    devices: dict[str, Any] = Field(default_factory=dict)
    helpers: dict[str, Any] = Field(default_factory=dict)
    interfaces: list[dict[str, Any]] = Field(default_factory=list)
    root_device: str | None = None
    run_level: str | None = None
    virt_mode: str | None = None


class ConfigUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    kernel: str | None = None
    comments: str | None = None
    devices: dict[str, Any] | None = None
    helpers: dict[str, Any] | None = None
    interfaces: list[dict[str, Any]] | None = None
    root_device: str | None = None
    run_level: str | None = None
    virt_mode: str | None = None


class DomainCreate(BaseModel):
    domain: str = Field(min_length=1)
    type: str = "master"
    group: str | None = None
    description: str | None = None
    soa_email: str | None = None
    retry_sec: int | None = Field(default=None, ge=1)
    master_ips: list[str] = Field(default_factory=list)
    axfr_ips: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class DomainUpdate(BaseModel):
    group: str | None = None
    description: str | None = None
    soa_email: str | None = None
    retry_sec: int | None = Field(default=None, ge=1)
    master_ips: list[str] | None = None
    axfr_ips: list[str] | None = None
    tags: list[str] | None = None


class DomainRecordCreate(BaseModel):
    type: str
    target: str
    name: str | None = None
    priority: int | None = None
    weight: int | None = None
    port: int | None = None
    service: str | None = None
    protocol: str | None = None
    ttl_sec: int | None = Field(default=None, ge=1)
    tag: str | None = None


class DomainRecordUpdate(BaseModel):
    target: str | None = None
    name: str | None = None
    priority: int | None = None
    weight: int | None = None
    port: int | None = None
    service: str | None = None
    protocol: str | None = None
    ttl_sec: int | None = Field(default=None, ge=1)
    tag: str | None = None


class DatabaseCreate(BaseModel):
    label: str = Field(min_length=1)
    engine: str
    type: str
    region: str
    allow_list: list[str] = Field(default_factory=list)
    cluster_size: int = Field(default=1, ge=1)
    username: str | None = None
    password: str | None = None


class DatabaseUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    allow_list: list[str] | None = None
    cluster_size: int | None = Field(default=None, ge=1)


class SshKeyCreate(BaseModel):
    label: str = Field(min_length=1)
    ssh_key: str = Field(min_length=1)


class SshKeyUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1)


def parse_filter(filter_value: str | None) -> dict[str, Any]:
    if not filter_value:
        return {}
    try:
        parsed = json.loads(filter_value)
    except json.JSONDecodeError:
        error_response("Invalid +filter JSON.", field="+filter")
    if not isinstance(parsed, dict):
        error_response("+filter must be a JSON object.", field="+filter")
    return parsed


def apply_filter(items: list[dict[str, Any]], filter_value: str | None) -> list[dict[str, Any]]:
    filters = parse_filter(filter_value)
    if not filters:
        return items

    filtered: list[dict[str, Any]] = []
    for item in items:
        if all(item.get(key) == value for key, value in filters.items()):
            filtered.append(item)
    return filtered


def apply_order(items: list[dict[str, Any]], order_by: str | None, order: str) -> list[dict[str, Any]]:
    if not order_by:
        return items
    reverse = order.lower() == "desc"
    return sorted(items, key=lambda item: (item.get(order_by) is None, item.get(order_by)), reverse=reverse)


def validate_instance_create(payload: InstanceCreate) -> None:
    if not store.region_exists(payload.region):
        error_response("Invalid region.", field="region")
    if not store.type_exists(payload.type):
        error_response("Invalid Linode type.", field="type")
    if payload.image and not store.image_exists(payload.image):
        error_response("Invalid image.", field="image")


def validate_volume_create(payload: VolumeCreate) -> None:
    if not store.region_exists(payload.region):
        error_response("Invalid region.", field="region")
    if payload.linode_id is not None and payload.linode_id not in store.instances:
        error_response("Linode not found.", field="linode_id", code=status.HTTP_404_NOT_FOUND)


def validate_vpc_create(payload: VpcCreate) -> None:
    if not store.region_exists(payload.region):
        error_response("Invalid region.", field="region")


def validate_nodebalancer_create(payload: NodeBalancerCreate) -> None:
    if not store.region_exists(payload.region):
        error_response("Invalid region.", field="region")


def validate_bucket_create(payload: BucketCreate) -> None:
    if not store.region_exists(payload.region):
        error_response("Invalid region.", field="region")
    if not store.cluster_exists(payload.cluster):
        error_response("Invalid object storage cluster.", field="cluster")
    if store.bucket_key(payload.cluster, payload.label) in store.buckets:
        error_response("Bucket label already exists in cluster.", field="label")


def get_instance_or_404(instance_id: int) -> dict[str, Any]:
    instance = store.instances.get(instance_id)
    if not instance:
        error_response("Linode not found.", code=status.HTTP_404_NOT_FOUND)
    return instance


def get_volume_or_404(volume_id: int) -> dict[str, Any]:
    volume = store.volumes.get(volume_id)
    if not volume:
        error_response("Volume not found.", code=status.HTTP_404_NOT_FOUND)
    return volume


def get_vpc_or_404(vpc_id: int) -> dict[str, Any]:
    vpc = store.vpcs.get(vpc_id)
    if not vpc:
        error_response("VPC not found.", code=status.HTTP_404_NOT_FOUND)
    return vpc


def get_nodebalancer_or_404(nodebalancer_id: int) -> dict[str, Any]:
    nodebalancer = store.nodebalancers.get(nodebalancer_id)
    if not nodebalancer:
        error_response("NodeBalancer not found.", code=status.HTTP_404_NOT_FOUND)
    return nodebalancer


def get_firewall_or_404(firewall_id: int) -> dict[str, Any]:
    firewall = store.firewalls.get(firewall_id)
    if not firewall:
        error_response("Firewall not found.", code=status.HTTP_404_NOT_FOUND)
    return firewall


def get_disk_or_404(instance_id: int, disk_id: int) -> dict[str, Any]:
    get_instance_or_404(instance_id)
    disk = store.instance_disks.get(disk_id)
    if not disk or disk["linode_id"] != instance_id:
        error_response("Disk not found.", code=status.HTTP_404_NOT_FOUND)
    return disk


def get_config_or_404(instance_id: int, config_id: int) -> dict[str, Any]:
    get_instance_or_404(instance_id)
    config = store.instance_configs.get(config_id)
    if not config or config["linode_id"] != instance_id:
        error_response("Config not found.", code=status.HTTP_404_NOT_FOUND)
    return config


def get_domain_or_404(domain_id: int) -> dict[str, Any]:
    domain = store.domains.get(domain_id)
    if not domain:
        error_response("Domain not found.", code=status.HTTP_404_NOT_FOUND)
    return domain


def get_domain_record_or_404(domain_id: int, record_id: int) -> dict[str, Any]:
    get_domain_or_404(domain_id)
    record = store.domain_records.get(record_id)
    if not record or record["domain_id"] != domain_id:
        error_response("Domain record not found.", code=status.HTTP_404_NOT_FOUND)
    return record


def get_database_or_404(database_id: int) -> dict[str, Any]:
    database = store.databases.get(database_id)
    if not database:
        error_response("Database not found.", code=status.HTTP_404_NOT_FOUND)
    return database


def get_ssh_key_or_404(ssh_key_id: int) -> dict[str, Any]:
    ssh_key = store.ssh_keys.get(ssh_key_id)
    if not ssh_key:
        error_response("SSH key not found.", code=status.HTTP_404_NOT_FOUND)
    return ssh_key


def validate_database_create(payload: DatabaseCreate) -> None:
    if not store.region_exists(payload.region):
        error_response("Invalid region.", field="region")
    if not store.database_engine_exists(payload.engine):
        error_response("Invalid database engine.", field="engine")
    if not store.database_type_exists(payload.type):
        error_response("Invalid database type.", field="type")


def validate_instance_keys(authorized_keys: list[str]) -> None:
    known_keys = {item["ssh_key"] for item in store.ssh_keys.values()}
    for key in authorized_keys:
        if key not in known_keys:
            error_response("SSH key not found in profile.", field="authorized_keys", code=status.HTTP_404_NOT_FOUND)


def get_subnet_or_404(vpc_id: int, subnet_id: int) -> dict[str, Any]:
    get_vpc_or_404(vpc_id)
    try:
        return store.get_subnet(vpc_id, subnet_id)
    except KeyError:
        error_response("VPC subnet not found.", code=status.HTTP_404_NOT_FOUND)


def validate_firewall_linodes(linode_ids: list[int]) -> None:
    for linode_id in linode_ids:
        if linode_id not in store.instances:
            error_response("Linode not found.", field="linodes", code=status.HTTP_404_NOT_FOUND)


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "mininode",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/_mininode/health",
    }


@app.get("/_mininode/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "mininode",
        "resources": {
            "instances": len(store.instances),
            "instance_disks": len(store.instance_disks),
            "instance_configs": len(store.instance_configs),
            "volumes": len(store.volumes),
            "vpcs": len(store.vpcs),
            "nodebalancers": len(store.nodebalancers),
            "firewalls": len(store.firewalls),
            "domains": len(store.domains),
            "domain_records": len(store.domain_records),
            "databases": len(store.databases),
            "ssh_keys": len(store.ssh_keys),
            "events": len(store.events),
            "buckets": len(store.buckets),
        },
    }


@app.post("/_mininode/reset")
async def reset() -> dict[str, str]:
    store.reset()
    store.save()
    return {"status": "reset"}


@app.get("/v4/profile")
async def profile(_: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return {
        "uid": 1,
        "username": "mininode",
        "email": "mininode@example.test",
        "restricted": False,
        "email_notifications": True,
        "ip_whitelist_enabled": False,
        "lish_auth_method": "keys_only",
    }


@app.get("/v4/account")
async def account(_: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return {
        "active_since": "2026-09-02T00:00:00",
        "balance": 0,
        "balance_uninvoiced": 0,
        "capabilities": ["Linodes", "NodeBalancers", "Block Storage", "Object Storage", "VPCs"],
        "company": "MiniNode Local",
        "credit_card": {"last_four": "4242", "expiry": "never"},
    }


@app.get("/v4/account/events")
async def list_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="desc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(store.list_events(), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.get("/v4/regions")
async def list_regions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(store.list_regions(), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.get("/v4/linode/types")
async def list_types(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(store.list_types(), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.get("/v4/images")
async def list_images(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(store.list_images(), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.get("/v4/object-storage/clusters")
async def list_clusters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(store.list_clusters(), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.get("/v4/linode/instances")
async def list_instances(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(list(store.instances.values()), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.post("/v4/linode/instances", status_code=status.HTTP_200_OK)
async def create_instance(payload: InstanceCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_instance_create(payload)
    validate_instance_keys(payload.authorized_keys)
    return store.create_instance(payload.model_dump())


@app.get("/v4/linode/instances/{instance_id}")
async def get_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_instance_or_404(instance_id)


@app.get("/v4/linode/instances/{instance_id}/disks")
async def list_disks(instance_id: int, _: str = Depends(require_bearer_token)) -> list[dict[str, Any]]:
    get_instance_or_404(instance_id)
    return store.list_disks(instance_id)


@app.post("/v4/linode/instances/{instance_id}/disks", status_code=status.HTTP_200_OK)
async def create_disk(instance_id: int, payload: DiskCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_instance_or_404(instance_id)
    return store.create_disk(instance_id, payload.model_dump(exclude_none=True))


@app.get("/v4/linode/instances/{instance_id}/disks/{disk_id}")
async def get_disk(instance_id: int, disk_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_disk_or_404(instance_id, disk_id)


@app.put("/v4/linode/instances/{instance_id}/disks/{disk_id}")
async def update_disk(instance_id: int, disk_id: int, payload: DiskUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_disk_or_404(instance_id, disk_id)
    return store.update_disk(disk_id, payload.model_dump(exclude_none=True))


@app.delete("/v4/linode/instances/{instance_id}/disks/{disk_id}", status_code=status.HTTP_200_OK)
async def delete_disk(instance_id: int, disk_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_disk_or_404(instance_id, disk_id)
    store.delete_disk(disk_id)
    return {"deleted": str(disk_id)}


@app.get("/v4/linode/instances/{instance_id}/configs")
async def list_configs(instance_id: int, _: str = Depends(require_bearer_token)) -> list[dict[str, Any]]:
    get_instance_or_404(instance_id)
    return store.list_configs(instance_id)


@app.post("/v4/linode/instances/{instance_id}/configs", status_code=status.HTTP_200_OK)
async def create_config(instance_id: int, payload: ConfigCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_instance_or_404(instance_id)
    return store.create_config(instance_id, payload.model_dump(exclude_none=True))


@app.get("/v4/linode/instances/{instance_id}/configs/{config_id}")
async def get_config(instance_id: int, config_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_config_or_404(instance_id, config_id)


@app.put("/v4/linode/instances/{instance_id}/configs/{config_id}")
async def update_config(instance_id: int, config_id: int, payload: ConfigUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_config_or_404(instance_id, config_id)
    return store.update_config(config_id, payload.model_dump(exclude_none=True))


@app.delete("/v4/linode/instances/{instance_id}/configs/{config_id}", status_code=status.HTTP_200_OK)
async def delete_config(instance_id: int, config_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_config_or_404(instance_id, config_id)
    store.delete_config(config_id)
    return {"deleted": str(config_id)}


@app.put("/v4/linode/instances/{instance_id}")
async def update_instance(instance_id: int, payload: InstanceUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_instance_or_404(instance_id)
    updates = payload.model_dump(exclude_none=True)
    return store.update_instance(instance_id, updates)


@app.delete("/v4/linode/instances/{instance_id}", status_code=status.HTTP_200_OK)
async def delete_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_instance_or_404(instance_id)
    for volume in store.volumes.values():
        if volume.get("linode_id") == instance_id:
            volume["linode_id"] = None
    store.delete_instance(instance_id)
    return {"deleted": str(instance_id)}


@app.post("/v4/linode/instances/{instance_id}/boot")
async def boot_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_instance_or_404(instance_id)
    return store.set_instance_status(instance_id, "running", "linode_boot")


@app.post("/v4/linode/instances/{instance_id}/shutdown")
async def shutdown_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_instance_or_404(instance_id)
    return store.set_instance_status(instance_id, "offline", "linode_shutdown")


@app.post("/v4/linode/instances/{instance_id}/reboot")
async def reboot_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_instance_or_404(instance_id)
    return store.set_instance_status(instance_id, "running", "linode_reboot")


@app.get("/v4/volumes")
async def list_volumes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(list(store.volumes.values()), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.post("/v4/volumes", status_code=status.HTTP_200_OK)
async def create_volume(payload: VolumeCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_volume_create(payload)
    return store.create_volume(payload.model_dump())


@app.get("/v4/volumes/{volume_id}")
async def get_volume(volume_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_volume_or_404(volume_id)


@app.put("/v4/volumes/{volume_id}")
async def update_volume(volume_id: int, payload: VolumeUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_volume_or_404(volume_id)
    updates = payload.model_dump(exclude_none=True)
    return store.update_volume(volume_id, updates)


@app.post("/v4/volumes/{volume_id}/attach")
async def attach_volume(volume_id: int, payload: VolumeAttach, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_volume_or_404(volume_id)
    if payload.linode_id not in store.instances:
        error_response("Linode not found.", field="linode_id", code=status.HTTP_404_NOT_FOUND)
    return store.update_volume(volume_id, {"linode_id": payload.linode_id}, action="volume_attach")


@app.post("/v4/volumes/{volume_id}/detach")
async def detach_volume(volume_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_volume_or_404(volume_id)
    return store.update_volume(volume_id, {"linode_id": None}, action="volume_detach")


@app.delete("/v4/volumes/{volume_id}", status_code=status.HTTP_200_OK)
async def delete_volume(volume_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_volume_or_404(volume_id)
    store.delete_volume(volume_id)
    return {"deleted": str(volume_id)}


@app.get("/v4/vpcs")
async def list_vpcs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(list(store.vpcs.values()), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.post("/v4/vpcs", status_code=status.HTTP_200_OK)
async def create_vpc(payload: VpcCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_vpc_create(payload)
    return store.create_vpc(payload.model_dump())


@app.get("/v4/vpcs/{vpc_id}")
async def get_vpc(vpc_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_vpc_or_404(vpc_id)


@app.put("/v4/vpcs/{vpc_id}")
async def update_vpc(vpc_id: int, payload: VpcUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_vpc_or_404(vpc_id)
    updates = payload.model_dump(exclude_none=True)
    return store.update_vpc(vpc_id, updates)


@app.get("/v4/vpcs/{vpc_id}/subnets")
async def list_vpc_subnets(vpc_id: int, _: str = Depends(require_bearer_token)) -> list[dict[str, Any]]:
    return get_vpc_or_404(vpc_id).get("subnets", [])


@app.post("/v4/vpcs/{vpc_id}/subnets", status_code=status.HTTP_200_OK)
async def create_vpc_subnet(vpc_id: int, payload: VpcSubnet, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_vpc_or_404(vpc_id)
    return store.create_subnet(vpc_id, payload.model_dump())


@app.get("/v4/vpcs/{vpc_id}/subnets/{subnet_id}")
async def get_vpc_subnet(vpc_id: int, subnet_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_subnet_or_404(vpc_id, subnet_id)


@app.put("/v4/vpcs/{vpc_id}/subnets/{subnet_id}")
async def update_vpc_subnet(vpc_id: int, subnet_id: int, payload: VpcSubnet, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_subnet_or_404(vpc_id, subnet_id)
    return store.update_subnet(vpc_id, subnet_id, payload.model_dump())


@app.delete("/v4/vpcs/{vpc_id}/subnets/{subnet_id}", status_code=status.HTTP_200_OK)
async def delete_vpc_subnet(vpc_id: int, subnet_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_subnet_or_404(vpc_id, subnet_id)
    store.delete_subnet(vpc_id, subnet_id)
    return {"deleted": str(subnet_id)}


@app.delete("/v4/vpcs/{vpc_id}", status_code=status.HTTP_200_OK)
async def delete_vpc(vpc_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_vpc_or_404(vpc_id)
    store.delete_vpc(vpc_id)
    return {"deleted": str(vpc_id)}


@app.get("/v4/nodebalancers")
async def list_nodebalancers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(list(store.nodebalancers.values()), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.post("/v4/nodebalancers", status_code=status.HTTP_200_OK)
async def create_nodebalancer(payload: NodeBalancerCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_nodebalancer_create(payload)
    return store.create_nodebalancer(payload.model_dump())


@app.get("/v4/nodebalancers/{nodebalancer_id}")
async def get_nodebalancer(nodebalancer_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_nodebalancer_or_404(nodebalancer_id)


@app.put("/v4/nodebalancers/{nodebalancer_id}")
async def update_nodebalancer(nodebalancer_id: int, payload: NodeBalancerUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_nodebalancer_or_404(nodebalancer_id)
    updates = payload.model_dump(exclude_none=True)
    return store.update_nodebalancer(nodebalancer_id, updates)


@app.delete("/v4/nodebalancers/{nodebalancer_id}", status_code=status.HTTP_200_OK)
async def delete_nodebalancer(nodebalancer_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_nodebalancer_or_404(nodebalancer_id)
    store.delete_nodebalancer(nodebalancer_id)
    return {"deleted": str(nodebalancer_id)}


@app.get("/v4/networking/firewalls")
async def list_firewalls(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(list(store.firewalls.values()), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.post("/v4/networking/firewalls", status_code=status.HTTP_200_OK)
async def create_firewall(payload: FirewallCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_firewall_linodes(payload.linodes)
    return store.create_firewall(payload.model_dump())


@app.get("/v4/networking/firewalls/{firewall_id}")
async def get_firewall(firewall_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_firewall_or_404(firewall_id)


@app.put("/v4/networking/firewalls/{firewall_id}")
async def update_firewall(firewall_id: int, payload: FirewallUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_firewall_or_404(firewall_id)
    updates = payload.model_dump(exclude_none=True)
    if "linodes" in updates:
        validate_firewall_linodes(updates["linodes"])
    return store.update_firewall(firewall_id, updates)


@app.delete("/v4/networking/firewalls/{firewall_id}", status_code=status.HTTP_200_OK)
async def delete_firewall(firewall_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_firewall_or_404(firewall_id)
    store.delete_firewall(firewall_id)
    return {"deleted": str(firewall_id)}


@app.get("/v4/domains")
async def list_domains(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(list(store.domains.values()), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.post("/v4/domains", status_code=status.HTTP_200_OK)
async def create_domain(payload: DomainCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return store.create_domain(payload.model_dump(exclude_none=True))


@app.get("/v4/domains/{domain_id}")
async def get_domain(domain_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_domain_or_404(domain_id)


@app.put("/v4/domains/{domain_id}")
async def update_domain(domain_id: int, payload: DomainUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_domain_or_404(domain_id)
    return store.update_domain(domain_id, payload.model_dump(exclude_none=True))


@app.delete("/v4/domains/{domain_id}", status_code=status.HTTP_200_OK)
async def delete_domain(domain_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_domain_or_404(domain_id)
    store.delete_domain(domain_id)
    return {"deleted": str(domain_id)}


@app.get("/v4/domains/{domain_id}/records")
async def list_domain_records(domain_id: int, _: str = Depends(require_bearer_token)) -> list[dict[str, Any]]:
    get_domain_or_404(domain_id)
    return store.list_domain_records(domain_id)


@app.post("/v4/domains/{domain_id}/records", status_code=status.HTTP_200_OK)
async def create_domain_record(domain_id: int, payload: DomainRecordCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_domain_or_404(domain_id)
    return store.create_domain_record(domain_id, payload.model_dump(exclude_none=True))


@app.get("/v4/domains/{domain_id}/records/{record_id}")
async def get_domain_record(domain_id: int, record_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_domain_record_or_404(domain_id, record_id)


@app.put("/v4/domains/{domain_id}/records/{record_id}")
async def update_domain_record(domain_id: int, record_id: int, payload: DomainRecordUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_domain_record_or_404(domain_id, record_id)
    return store.update_domain_record(record_id, payload.model_dump(exclude_none=True))


@app.delete("/v4/domains/{domain_id}/records/{record_id}", status_code=status.HTTP_200_OK)
async def delete_domain_record(domain_id: int, record_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_domain_record_or_404(domain_id, record_id)
    store.delete_domain_record(record_id)
    return {"deleted": str(record_id)}


@app.get("/v4/databases/engines")
async def list_database_engines(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(store.list_database_engines(), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.get("/v4/databases/types")
async def list_database_types(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(store.list_database_types(), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.get("/v4/databases/instances")
async def list_databases(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(list(store.databases.values()), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.post("/v4/databases/instances", status_code=status.HTTP_200_OK)
async def create_database(payload: DatabaseCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_database_create(payload)
    return store.create_database(payload.model_dump(exclude_none=True))


@app.get("/v4/databases/instances/{database_id}")
async def get_database(database_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_database_or_404(database_id)


@app.put("/v4/databases/instances/{database_id}")
async def update_database(database_id: int, payload: DatabaseUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_database_or_404(database_id)
    return store.update_database(database_id, payload.model_dump(exclude_none=True))


@app.get("/v4/databases/instances/{database_id}/credentials")
async def get_database_credentials(database_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_database_or_404(database_id)["credentials"]


@app.post("/v4/databases/instances/{database_id}/credentials/reset", status_code=status.HTTP_200_OK)
async def reset_database_credentials(database_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_database_or_404(database_id)
    return store.reset_database_credentials(database_id)


@app.delete("/v4/databases/instances/{database_id}", status_code=status.HTTP_200_OK)
async def delete_database(database_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_database_or_404(database_id)
    store.delete_database(database_id)
    return {"deleted": str(database_id)}


@app.get("/v4/profile/sshkeys")
async def list_ssh_keys(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(list(store.ssh_keys.values()), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.post("/v4/profile/sshkeys", status_code=status.HTTP_200_OK)
async def create_ssh_key(payload: SshKeyCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return store.create_ssh_key(payload.model_dump())


@app.get("/v4/profile/sshkeys/{ssh_key_id}")
async def get_ssh_key(ssh_key_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_ssh_key_or_404(ssh_key_id)


@app.put("/v4/profile/sshkeys/{ssh_key_id}")
async def update_ssh_key(ssh_key_id: int, payload: SshKeyUpdate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    get_ssh_key_or_404(ssh_key_id)
    return store.update_ssh_key(ssh_key_id, payload.model_dump(exclude_none=True))


@app.delete("/v4/profile/sshkeys/{ssh_key_id}", status_code=status.HTTP_200_OK)
async def delete_ssh_key(ssh_key_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_ssh_key_or_404(ssh_key_id)
    store.delete_ssh_key(ssh_key_id)
    return {"deleted": str(ssh_key_id)}


@app.get("/v4/object-storage/buckets")
async def list_buckets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    filter_value: str | None = Query(default=None, alias="+filter"),
    order_by: str | None = Query(default=None, alias="+order_by"),
    order: str = Query(default="asc", alias="+order"),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    items = apply_order(apply_filter(list(store.buckets.values()), filter_value), order_by, order)
    return paginate(items, page, page_size)


@app.post("/v4/object-storage/buckets", status_code=status.HTTP_200_OK)
async def create_bucket(payload: BucketCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_bucket_create(payload)
    return store.create_bucket(payload.model_dump())


@app.get("/v4/object-storage/buckets/{cluster}/{bucket_label}")
async def get_bucket(cluster: str, bucket_label: str, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    key = store.bucket_key(cluster, bucket_label)
    bucket = store.buckets.get(key)
    if not bucket:
        error_response("Bucket not found.", code=status.HTTP_404_NOT_FOUND)
    return bucket


@app.delete("/v4/object-storage/buckets/{cluster}/{bucket_label}", status_code=status.HTTP_200_OK)
async def delete_bucket(cluster: str, bucket_label: str, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    key = store.bucket_key(cluster, bucket_label)
    if key not in store.buckets:
        error_response("Bucket not found.", code=status.HTTP_404_NOT_FOUND)
    store.delete_bucket(key)
    return {"deleted": bucket_label}


def main() -> None:
    host = os.getenv("MININODE_HOST", "127.0.0.1")
    port = int(os.getenv("MININODE_PORT", "8000"))
    uvicorn.run("mininode.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
