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
            "volumes": len(store.volumes),
            "vpcs": len(store.vpcs),
            "nodebalancers": len(store.nodebalancers),
            "buckets": len(store.buckets),
        },
    }


@app.post("/_mininode/reset")
async def reset() -> dict[str, str]:
    store.reset()
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


@app.get("/v4/regions")
async def list_regions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return paginate(store.list_regions(), page, page_size)


@app.get("/v4/linode/types")
async def list_types(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return paginate(store.list_types(), page, page_size)


@app.get("/v4/images")
async def list_images(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return paginate(store.list_images(), page, page_size)


@app.get("/v4/object-storage/clusters")
async def list_clusters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return paginate(store.list_clusters(), page, page_size)


@app.get("/v4/linode/instances")
async def list_instances(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return paginate(list(store.instances.values()), page, page_size)


@app.post("/v4/linode/instances", status_code=status.HTTP_200_OK)
async def create_instance(payload: InstanceCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_instance_create(payload)
    return store.create_instance(payload.model_dump())


@app.get("/v4/linode/instances/{instance_id}")
async def get_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_instance_or_404(instance_id)


@app.delete("/v4/linode/instances/{instance_id}", status_code=status.HTTP_200_OK)
async def delete_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_instance_or_404(instance_id)
    for volume in store.volumes.values():
        if volume.get("linode_id") == instance_id:
            volume["linode_id"] = None
    del store.instances[instance_id]
    return {"deleted": str(instance_id)}


@app.post("/v4/linode/instances/{instance_id}/boot")
async def boot_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    instance = get_instance_or_404(instance_id)
    instance["status"] = "running"
    return instance


@app.post("/v4/linode/instances/{instance_id}/shutdown")
async def shutdown_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    instance = get_instance_or_404(instance_id)
    instance["status"] = "offline"
    return instance


@app.post("/v4/linode/instances/{instance_id}/reboot")
async def reboot_instance(instance_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    instance = get_instance_or_404(instance_id)
    instance["status"] = "running"
    return instance


@app.get("/v4/volumes")
async def list_volumes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return paginate(list(store.volumes.values()), page, page_size)


@app.post("/v4/volumes", status_code=status.HTTP_200_OK)
async def create_volume(payload: VolumeCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_volume_create(payload)
    return store.create_volume(payload.model_dump())


@app.get("/v4/volumes/{volume_id}")
async def get_volume(volume_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_volume_or_404(volume_id)


@app.post("/v4/volumes/{volume_id}/attach")
async def attach_volume(volume_id: int, payload: VolumeAttach, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    volume = get_volume_or_404(volume_id)
    if payload.linode_id not in store.instances:
        error_response("Linode not found.", field="linode_id", code=status.HTTP_404_NOT_FOUND)
    volume["linode_id"] = payload.linode_id
    return volume


@app.post("/v4/volumes/{volume_id}/detach")
async def detach_volume(volume_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    volume = get_volume_or_404(volume_id)
    volume["linode_id"] = None
    return volume


@app.delete("/v4/volumes/{volume_id}", status_code=status.HTTP_200_OK)
async def delete_volume(volume_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_volume_or_404(volume_id)
    del store.volumes[volume_id]
    return {"deleted": str(volume_id)}


@app.get("/v4/vpcs")
async def list_vpcs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return paginate(list(store.vpcs.values()), page, page_size)


@app.post("/v4/vpcs", status_code=status.HTTP_200_OK)
async def create_vpc(payload: VpcCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_vpc_create(payload)
    return store.create_vpc(payload.model_dump())


@app.get("/v4/vpcs/{vpc_id}")
async def get_vpc(vpc_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_vpc_or_404(vpc_id)


@app.delete("/v4/vpcs/{vpc_id}", status_code=status.HTTP_200_OK)
async def delete_vpc(vpc_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_vpc_or_404(vpc_id)
    del store.vpcs[vpc_id]
    return {"deleted": str(vpc_id)}


@app.get("/v4/nodebalancers")
async def list_nodebalancers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return paginate(list(store.nodebalancers.values()), page, page_size)


@app.post("/v4/nodebalancers", status_code=status.HTTP_200_OK)
async def create_nodebalancer(payload: NodeBalancerCreate, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    validate_nodebalancer_create(payload)
    return store.create_nodebalancer(payload.model_dump())


@app.get("/v4/nodebalancers/{nodebalancer_id}")
async def get_nodebalancer(nodebalancer_id: int, _: str = Depends(require_bearer_token)) -> dict[str, Any]:
    return get_nodebalancer_or_404(nodebalancer_id)


@app.delete("/v4/nodebalancers/{nodebalancer_id}", status_code=status.HTTP_200_OK)
async def delete_nodebalancer(nodebalancer_id: int, _: str = Depends(require_bearer_token)) -> dict[str, str]:
    get_nodebalancer_or_404(nodebalancer_id)
    del store.nodebalancers[nodebalancer_id]
    return {"deleted": str(nodebalancer_id)}


@app.get("/v4/object-storage/buckets")
async def list_buckets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_bearer_token),
) -> dict[str, Any]:
    return paginate(list(store.buckets.values()), page, page_size)


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
    del store.buckets[key]
    return {"deleted": bucket_label}


def main() -> None:
    host = os.getenv("MININODE_HOST", "127.0.0.1")
    port = int(os.getenv("MININODE_PORT", "8000"))
    uvicorn.run("mininode.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
