"""
RunPod Auto-Scaler for Translation Gateway

Monitors traffic + pod load and automatically:
- Creates new RunPod pods when load is high
- Stops idle pods to save cost
- Maintains a healthy pool of pods per service
- Routes requests to least-loaded pod (load balancing)

Configuration via environment variables:
    RUNPOD_API_KEY                  - RunPod API key
    AUTOSCALER_ENABLED              - "true" to enable (default: false)

    # Service: LID
    LID_TEMPLATE_ID                 - RunPod template ID for LID pod
    LID_GPU_TYPE                    - e.g. "NVIDIA RTX 4000 Ada Generation"
    LID_MIN_PODS                    - Minimum pods always running (default: 1)
    LID_MAX_PODS                    - Max pods to scale up to (default: 5)
    LID_INITIAL_POD_IDS             - Comma-separated existing pod IDs

    # Same for INDIC_EN_* and EN_INDIC_*

    # Scaling triggers
    SCALE_UP_RPS_THRESHOLD          - Requests/sec per pod to trigger scale-up (default: 50)
    SCALE_UP_LATENCY_MS             - p95 latency ms to trigger scale-up (default: 2000)
    SCALE_DOWN_RPS_THRESHOLD        - Requests/sec per pod to trigger scale-down (default: 5)
    SCALE_DOWN_IDLE_MINUTES         - Minutes of low load before scale-down (default: 10)
    SCALE_CHECK_INTERVAL_SECONDS    - How often to check scaling (default: 30)
"""
import os
import time
import asyncio
import logging
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger("autoscaler")
logger.setLevel(logging.INFO)


# ============================================================================
# CONFIGURATION
# ============================================================================
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_GRAPHQL_URL = "https://api.runpod.io/graphql"
AUTOSCALER_ENABLED = os.environ.get("AUTOSCALER_ENABLED", "false").lower() == "true"

# Scaling thresholds
SCALE_UP_RPS_THRESHOLD = float(os.environ.get("SCALE_UP_RPS_THRESHOLD", "50"))
SCALE_UP_LATENCY_MS = float(os.environ.get("SCALE_UP_LATENCY_MS", "2000"))
SCALE_DOWN_RPS_THRESHOLD = float(os.environ.get("SCALE_DOWN_RPS_THRESHOLD", "5"))
SCALE_DOWN_IDLE_MINUTES = int(os.environ.get("SCALE_DOWN_IDLE_MINUTES", "10"))
SCALE_CHECK_INTERVAL = int(os.environ.get("SCALE_CHECK_INTERVAL_SECONDS", "30"))
HEALTH_CHECK_INTERVAL = 15  # seconds


# ============================================================================
# DATA CLASSES
# ============================================================================
@dataclass
class Pod:
    """Represents a single RunPod pod instance"""
    pod_id: str
    service_name: str          # "lid", "indic_en", or "en_indic"
    base_url: str              # https://{pod_id}-{port}.proxy.runpod.net
    port: int
    is_healthy: bool = False
    is_starting: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_request_at: Optional[datetime] = None
    in_flight: int = 0          # Currently processing requests
    request_count: int = 0      # Total requests served
    error_count: int = 0
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def avg_latency_ms(self) -> float:
        if not self.recent_latencies:
            return 0
        return sum(self.recent_latencies) / len(self.recent_latencies)

    @property
    def p95_latency_ms(self) -> float:
        if not self.recent_latencies:
            return 0
        sorted_lat = sorted(self.recent_latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]


@dataclass
class ServicePool:
    """Pool of pods for one service (LID, Indic→EN, or EN→Indic)"""
    name: str
    port: int
    template_id: str
    gpu_type: str
    min_pods: int
    max_pods: int
    pods: List[Pod] = field(default_factory=list)
    request_window: deque = field(default_factory=lambda: deque(maxlen=300))  # last 5 min of requests
    last_scale_action_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def healthy_pods(self) -> List[Pod]:
        return [p for p in self.pods if p.is_healthy]

    @property
    def num_healthy(self) -> int:
        return len(self.healthy_pods)

    @property
    def total_in_flight(self) -> int:
        return sum(p.in_flight for p in self.healthy_pods)

    @property
    def current_rps(self) -> float:
        """Requests per second over last 60 seconds"""
        cutoff = time.time() - 60
        recent = [t for t in self.request_window if t > cutoff]
        return len(recent) / 60.0

    @property
    def rps_per_pod(self) -> float:
        if self.num_healthy == 0:
            return float("inf")
        return self.current_rps / self.num_healthy

    @property
    def avg_p95_latency(self) -> float:
        if not self.healthy_pods:
            return 0
        latencies = [p.p95_latency_ms for p in self.healthy_pods if p.recent_latencies]
        if not latencies:
            return 0
        return sum(latencies) / len(latencies)

    def least_loaded_pod(self) -> Optional[Pod]:
        """Return the healthy pod with the fewest in-flight requests"""
        healthy = self.healthy_pods
        if not healthy:
            return None
        return min(healthy, key=lambda p: (p.in_flight, p.request_count))

    def record_request(self):
        self.request_window.append(time.time())


# ============================================================================
# RUNPOD API CLIENT
# ============================================================================
class RunPodClient:
    """Async client for RunPod GraphQL API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=60.0)

    async def _gql(self, query: str) -> dict:
        url = f"{RUNPOD_GRAPHQL_URL}?api_key={self.api_key}"
        try:
            resp = await self.client.post(
                url,
                json={"query": query},
                headers={"Content-Type": "application/json"},
            )
            return resp.json()
        except Exception as e:
            logger.error(f"RunPod API error: {e}")
            return {"errors": [str(e)]}

    async def create_pod(self, template_id: str, gpu_type: str, name: str) -> Optional[str]:
        """Create a new pod from a template. Returns pod_id."""
        query = f"""
        mutation {{
            podFindAndDeployOnDemand(input: {{
                cloudType: SECURE,
                gpuCount: 1,
                gpuTypeId: "{gpu_type}",
                name: "{name}",
                templateId: "{template_id}",
                volumeInGb: 50,
                containerDiskInGb: 20,
                ports: "6001/http,6002/http,6003/http"
            }}) {{
                id
                desiredStatus
            }}
        }}
        """
        result = await self._gql(query)
        data = result.get("data", {}).get("podFindAndDeployOnDemand")
        if data:
            logger.info(f"[autoscaler] Created pod {data['id']} from template {template_id}")
            return data["id"]
        logger.error(f"[autoscaler] Failed to create pod: {result}")
        return None

    async def stop_pod(self, pod_id: str) -> bool:
        query = f'mutation {{ podStop(input: {{podId: "{pod_id}"}}) {{ id desiredStatus }} }}'
        result = await self._gql(query)
        return "errors" not in result

    async def terminate_pod(self, pod_id: str) -> bool:
        """Permanently delete a pod (releases storage)"""
        query = f'mutation {{ podTerminate(input: {{podId: "{pod_id}"}}) }}'
        result = await self._gql(query)
        return "errors" not in result

    async def get_pod_status(self, pod_id: str) -> Optional[dict]:
        query = f'query {{ pod(input: {{podId: "{pod_id}"}}) {{ id name desiredStatus runtime {{ uptimeInSeconds }} }} }}'
        result = await self._gql(query)
        return result.get("data", {}).get("pod")


# ============================================================================
# AUTO-SCALER
# ============================================================================
class AutoScaler:
    """Main auto-scaler for all services"""

    def __init__(self):
        self.runpod = RunPodClient(RUNPOD_API_KEY)
        self.http = httpx.AsyncClient(timeout=10.0)
        self.pools: Dict[str, ServicePool] = {}
        self._build_pools()

    def _build_pools(self):
        """Initialize service pools from environment variables"""
        services = [
            ("lid", 6001),
            ("indic_en", 6002),
            ("en_indic", 6003),
        ]
        for name, port in services:
            prefix = name.upper()
            pool = ServicePool(
                name=name,
                port=port,
                template_id=os.environ.get(f"{prefix}_TEMPLATE_ID", ""),
                gpu_type=os.environ.get(f"{prefix}_GPU_TYPE", "NVIDIA RTX 4000 Ada Generation"),
                min_pods=int(os.environ.get(f"{prefix}_MIN_PODS", "1")),
                max_pods=int(os.environ.get(f"{prefix}_MAX_PODS", "5")),
            )

            # Bootstrap with existing pod IDs
            initial_ids = os.environ.get(f"{prefix}_INITIAL_POD_IDS", "")
            for pid in [p.strip() for p in initial_ids.split(",") if p.strip()]:
                pod = Pod(
                    pod_id=pid,
                    service_name=name,
                    base_url=f"https://{pid}-{port}.proxy.runpod.net",
                    port=port,
                )
                pool.pods.append(pod)
                logger.info(f"[autoscaler] Loaded existing pod {pid} for {name}")

            self.pools[name] = pool

    def get_url_for_service(self, service: str) -> Optional[str]:
        """Get the URL of the least-loaded healthy pod for a service"""
        pool = self.pools.get(service)
        if not pool:
            return None
        pod = pool.least_loaded_pod()
        if not pod:
            return None
        pool.record_request()
        return pod.base_url

    def record_request_metrics(self, service: str, pod_url: str, latency_ms: float, success: bool):
        """Record metrics after a request completes"""
        pool = self.pools.get(service)
        if not pool:
            return
        for pod in pool.pods:
            if pod.base_url == pod_url:
                pod.last_request_at = datetime.utcnow()
                pod.request_count += 1
                pod.recent_latencies.append(latency_ms)
                if not success:
                    pod.error_count += 1
                break

    # ------------------------------------------------------------------------
    # Background loops
    # ------------------------------------------------------------------------
    async def health_check_loop(self):
        """Periodically check health of all pods"""
        while True:
            try:
                for pool in self.pools.values():
                    for pod in pool.pods:
                        try:
                            r = await self.http.get(f"{pod.base_url}/health", timeout=5.0)
                            healthy = r.status_code == 200
                            if healthy and pod.is_starting:
                                pod.is_starting = False
                                logger.info(f"[autoscaler] Pod {pod.pod_id} ({pod.service_name}) is now READY")
                            pod.is_healthy = healthy
                        except Exception:
                            pod.is_healthy = False
            except Exception as e:
                logger.error(f"[autoscaler] Health check error: {e}")
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

    async def scaling_loop(self):
        """Periodically evaluate scaling decisions"""
        while True:
            try:
                for pool in self.pools.values():
                    await self._evaluate_pool(pool)
            except Exception as e:
                logger.error(f"[autoscaler] Scaling loop error: {e}")
            await asyncio.sleep(SCALE_CHECK_INTERVAL)

    async def _evaluate_pool(self, pool: ServicePool):
        """Decide whether to scale a pool up or down"""
        # Cooldown: don't scale more than once every 2 min
        cooldown = timedelta(minutes=2)
        if datetime.utcnow() - pool.last_scale_action_at < cooldown:
            return

        rps_per_pod = pool.rps_per_pod
        p95 = pool.avg_p95_latency

        logger.info(
            f"[autoscaler] {pool.name}: pods={pool.num_healthy}/{len(pool.pods)} "
            f"rps={pool.current_rps:.1f} rps_per_pod={rps_per_pod:.1f} p95={p95:.0f}ms"
        )

        # ---- Scale UP ----
        scale_up = False
        if pool.num_healthy < pool.max_pods:
            if rps_per_pod > SCALE_UP_RPS_THRESHOLD:
                scale_up = True
                logger.info(f"[autoscaler] {pool.name}: SCALE UP — rps/pod {rps_per_pod:.1f} > {SCALE_UP_RPS_THRESHOLD}")
            elif p95 > SCALE_UP_LATENCY_MS and pool.current_rps > 0:
                scale_up = True
                logger.info(f"[autoscaler] {pool.name}: SCALE UP — p95 {p95:.0f}ms > {SCALE_UP_LATENCY_MS}ms")

        if scale_up:
            await self._scale_up(pool)
            pool.last_scale_action_at = datetime.utcnow()
            return

        # ---- Scale DOWN ----
        if pool.num_healthy > pool.min_pods:
            # Find idle pods (no requests in last N minutes)
            idle_cutoff = datetime.utcnow() - timedelta(minutes=SCALE_DOWN_IDLE_MINUTES)
            idle_pods = [
                p for p in pool.healthy_pods
                if p.last_request_at is None or p.last_request_at < idle_cutoff
            ]
            if idle_pods and rps_per_pod < SCALE_DOWN_RPS_THRESHOLD:
                # Don't remove the most recently created pod (let it warm up)
                idle_pods.sort(key=lambda p: p.created_at)
                victim = idle_pods[0]
                logger.info(f"[autoscaler] {pool.name}: SCALE DOWN — stopping idle pod {victim.pod_id}")
                await self._scale_down(pool, victim)
                pool.last_scale_action_at = datetime.utcnow()

    async def _scale_up(self, pool: ServicePool):
        if not pool.template_id:
            logger.warning(f"[autoscaler] {pool.name}: no template_id configured, cannot scale up")
            return
        name = f"{pool.name}-auto-{int(time.time())}"
        pod_id = await self.runpod.create_pod(pool.template_id, pool.gpu_type, name)
        if pod_id:
            pod = Pod(
                pod_id=pod_id,
                service_name=pool.name,
                base_url=f"https://{pod_id}-{pool.port}.proxy.runpod.net",
                port=pool.port,
            )
            pool.pods.append(pod)
            logger.info(f"[autoscaler] {pool.name}: added new pod {pod_id} (will warm up)")

    async def _scale_down(self, pool: ServicePool, pod: Pod):
        success = await self.runpod.stop_pod(pod.pod_id)
        if success:
            pool.pods.remove(pod)
            logger.info(f"[autoscaler] {pool.name}: stopped pod {pod.pod_id}")

    # ------------------------------------------------------------------------
    # Status / observability
    # ------------------------------------------------------------------------
    def status(self) -> dict:
        return {
            "enabled": AUTOSCALER_ENABLED,
            "thresholds": {
                "scale_up_rps_per_pod": SCALE_UP_RPS_THRESHOLD,
                "scale_up_p95_ms": SCALE_UP_LATENCY_MS,
                "scale_down_rps_per_pod": SCALE_DOWN_RPS_THRESHOLD,
                "scale_down_idle_minutes": SCALE_DOWN_IDLE_MINUTES,
            },
            "pools": {
                name: {
                    "min_pods": pool.min_pods,
                    "max_pods": pool.max_pods,
                    "current_rps": round(pool.current_rps, 2),
                    "rps_per_pod": round(pool.rps_per_pod, 2),
                    "avg_p95_latency_ms": round(pool.avg_p95_latency, 0),
                    "pods": [
                        {
                            "pod_id": p.pod_id,
                            "url": p.base_url,
                            "healthy": p.is_healthy,
                            "starting": p.is_starting,
                            "in_flight": p.in_flight,
                            "requests_served": p.request_count,
                            "errors": p.error_count,
                            "p95_ms": round(p.p95_latency_ms, 0),
                            "last_request": p.last_request_at.isoformat() if p.last_request_at else None,
                        }
                        for p in pool.pods
                    ],
                }
                for name, pool in self.pools.items()
            },
        }


# ============================================================================
# SINGLETON
# ============================================================================
_autoscaler: Optional[AutoScaler] = None


def get_autoscaler() -> AutoScaler:
    global _autoscaler
    if _autoscaler is None:
        _autoscaler = AutoScaler()
    return _autoscaler


async def start_autoscaler():
    """Start the background loops. Call this from FastAPI startup."""
    if not AUTOSCALER_ENABLED:
        logger.info("[autoscaler] Disabled (set AUTOSCALER_ENABLED=true to enable)")
        return
    if not RUNPOD_API_KEY:
        logger.warning("[autoscaler] RUNPOD_API_KEY not set, autoscaler disabled")
        return
    scaler = get_autoscaler()
    asyncio.create_task(scaler.health_check_loop())
    asyncio.create_task(scaler.scaling_loop())
    logger.info("[autoscaler] Started — health checks every 15s, scaling checks every 30s")
