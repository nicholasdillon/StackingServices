# MiniNode

MiniNode is a local Linode API emulator inspired by the shape of MiniStack.

It is intentionally narrower than MiniStack's AWS coverage. This MVP focuses on the Linode resources that are useful for local integration tests and Terraform-style workflows:

- `linode/instances`
- `volumes`
- `vpcs`
- `nodebalancers`
- `object-storage/buckets`
- catalog endpoints such as `regions`, `types`, and `images`

Everything runs behind one local HTTP endpoint with simple in-memory state.

## Features

- Linode v4-style REST paths
- Bearer token auth for non-internal endpoints
- Linode-like paginated list responses: `page`, `pages`, `results`, `data`
- Internal test helpers for `health` and `reset`
- Docker-friendly single-process runtime

## Quick Start

### Local Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
mininode
```

The API will listen on `http://127.0.0.1:8000` by default.

### Docker

```bash
docker build -t mininode .
docker run -p 8000:8000 mininode
```

## Example Usage

Set any token value:

```bash
export LINODE_TOKEN=test-token
```

Create an instance:

```bash
curl -X POST http://127.0.0.1:8000/v4/linode/instances \
  -H "Authorization: Bearer $LINODE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "web-1",
    "region": "us-east",
    "type": "g6-standard-1",
    "image": "linode/ubuntu24.04"
  }'
```

List instances:

```bash
curl http://127.0.0.1:8000/v4/linode/instances \
  -H "Authorization: Bearer $LINODE_TOKEN"
```

Create a VPC:

```bash
curl -X POST http://127.0.0.1:8000/v4/vpcs \
  -H "Authorization: Bearer $LINODE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "app-network",
    "region": "us-east",
    "subnets": [{"label": "private-a", "ipv4": "10.0.0.0/24"}]
  }'
```

Create an object storage bucket:

```bash
curl -X POST http://127.0.0.1:8000/v4/object-storage/buckets \
  -H "Authorization: Bearer $LINODE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "artifacts",
    "cluster": "us-east-1",
    "region": "us-east"
  }'
```

Reset emulator state:

```bash
curl -X POST http://127.0.0.1:8000/_mininode/reset
```

Health check:

```bash
curl http://127.0.0.1:8000/_mininode/health
```

## Scope Notes

This project currently emulates the Linode control plane, not real VMs, block devices, or object storage payloads. It is designed for local app development, tests, and provider-facing workflows that need deterministic API behavior.
