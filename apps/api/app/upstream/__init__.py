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


# upstream.yml 경로 결정 우선순위:
# 1) UPSTREAM_YML 환경변수 (Docker 등 배포 환경에서 명시 지정)
# 2) 현재 파일에서 위로 올라가며 upstream.yml을 탐색 (로컬 개발 자동 탐지)
def _find_upstream_yml() -> Path:
    import os
    env_path = os.environ.get("UPSTREAM_YML")
    if env_path:
        return Path(env_path)
    # 현재 파일 위치에서 루트까지 올라가며 upstream.yml 탐색
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "upstream.yml"
        if candidate.is_file():
            return candidate
    # 못 찾으면 기본 경로 반환 (init_balancer에서 RuntimeError 발생)
    return Path(__file__).resolve().parents[0] / "upstream.yml"


_UPSTREAM_YML = _find_upstream_yml()

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
