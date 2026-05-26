"""upstream.yml 파서 + Balancer 싱글턴."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .balancer import Balancer
from .instance_node import InstanceNode


@dataclass
class InstanceConfig:
    url: str
    slot_count: int


@dataclass
class HealthCheckConfig:
    interval_seconds: int = 30
    fail_threshold: int = 2


@dataclass
class UpstreamFileConfig:
    instances: list[InstanceConfig]
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)


def load_upstream_config(path: Path) -> UpstreamFileConfig:
    """upstream.yml을 읽어 UpstreamFileConfig를 반환한다. 없으면 RuntimeError."""
    if not path.exists():
        raise RuntimeError(f"upstream.yml not found at {path}. Cannot start.")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    hc_raw = raw.get("health_check", {})
    hc = HealthCheckConfig(
        interval_seconds=hc_raw.get("interval_seconds", 30),
        fail_threshold=hc_raw.get("fail_threshold", 2),
    )
    instances = [
        InstanceConfig(url=i["url"].rstrip("/"), slot_count=i["slot_count"])
        for i in raw["instances"]
    ]
    return UpstreamFileConfig(instances=instances, health_check=hc)


# 프로젝트 루트의 upstream.yml
# __file__ = apps/api/app/upstream/__init__.py → parents[4] = project root
_UPSTREAM_YML = Path(__file__).resolve().parents[4] / "upstream.yml"

_balancer: Balancer | None = None


def init_balancer() -> Balancer:
    """upstream.yml을 읽어 Balancer를 초기화한다. lifespan에서 한 번만 호출."""
    global _balancer
    cfg = load_upstream_config(_UPSTREAM_YML)
    nodes = [
        InstanceNode(
            url=inst.url,
            slot_count=inst.slot_count,
            fail_threshold=cfg.health_check.fail_threshold,
        )
        for inst in cfg.instances
    ]
    _balancer = Balancer(nodes=nodes, hc_interval=cfg.health_check.interval_seconds)
    return _balancer


def get_balancer() -> Balancer:
    if _balancer is None:
        raise RuntimeError("Balancer not initialized. Call init_balancer() first.")
    return _balancer
