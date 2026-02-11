"""
Health Check System

Provides comprehensive health checks for all system components.
Supports both simple health checks and detailed component-level checks.
"""

import asyncio
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, Response, status
import httpx

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemHealth:
    """Overall system health"""
    status: HealthStatus
    timestamp: str
    components: Dict[str, ComponentHealth]
    overall_response_time_ms: float


class HealthChecker:
    """
    Comprehensive health checker for all system components
    """
    
    def __init__(
        self,
        db_path: str = "./database/loan_collateral.db",
        chromadb_path: str = "./data/chromadb",
        gemini_api_key: Optional[str] = None,
        disk_threshold_percent: float = 10.0
    ):
        """
        Initialize health checker
        
        Args:
            db_path: Path to SQLite database
            chromadb_path: Path to ChromaDB storage
            gemini_api_key: Gemini API key for testing
            disk_threshold_percent: Minimum free disk space percentage
        """
        self.db_path = Path(db_path)
        self.chromadb_path = Path(chromadb_path)
        self.gemini_api_key = gemini_api_key
        self.disk_threshold = disk_threshold_percent
    
    async def check_health(self, detailed: bool = False) -> SystemHealth:
        """
        Check overall system health
        
        Args:
            detailed: If True, perform detailed checks on all components
        
        Returns:
            SystemHealth object with status of all components
        """
        start_time = time.time()
        
        # Run all health checks in parallel
        checks = [
            self.check_database(),
            self.check_vector_db(),
            self.check_disk_space(),
        ]
        
        if detailed and self.gemini_api_key:
            checks.append(self.check_gemini_api())
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        # Process results
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        for result in results:
            if isinstance(result, Exception):
                component_health = ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(result),
                    response_time_ms=0.0
                )
            else:
                component_health = result
            
            components[component_health.name] = component_health
            
            # Determine overall status
            if component_health.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif component_health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        overall_response_time = (time.time() - start_time) * 1000
        
        return SystemHealth(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            components=components,
            overall_response_time_ms=round(overall_response_time, 2)
        )
    
    async def check_database(self) -> ComponentHealth:
        """Check SQLite database connectivity and performance"""
        start_time = time.time()
        
        try:
            if not self.db_path.exists():
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database file not found",
                    response_time_ms=0.0
                )
            
            # Test connection with timeout
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            cursor = conn.cursor()
            
            # Simple query to test
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            # Check database integrity
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]
            
            conn.close()
            
            response_time = (time.time() - start_time) * 1000
            
            if result and integrity == "ok":
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database is accessible and healthy",
                    response_time_ms=round(response_time, 2),
                    details={
                        "path": str(self.db_path),
                        "integrity": integrity,
                        "size_mb": round(self.db_path.stat().st_size / 1024 / 1024, 2)
                    }
                )
            else:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.DEGRADED,
                    message="Database query failed",
                    response_time_ms=round(response_time, 2)
                )
        
        except sqlite3.OperationalError as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                response_time_ms=round((time.time() - start_time) * 1000, 2)
            )
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Unexpected error: {str(e)}",
                response_time_ms=round((time.time() - start_time) * 1000, 2)
            )
    
    async def check_vector_db(self) -> ComponentHealth:
        """Check ChromaDB availability and performance"""
        start_time = time.time()
        
        if not CHROMADB_AVAILABLE:
            return ComponentHealth(
                name="vector_db",
                status=HealthStatus.UNHEALTHY,
                message="ChromaDB not installed",
                response_time_ms=0.0
            )
        
        try:
            # Try to connect to ChromaDB
            client = chromadb.PersistentClient(path=str(self.chromadb_path))
            
            # List collections to verify accessibility
            collections = client.list_collections()
            
            response_time = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name="vector_db",
                status=HealthStatus.HEALTHY,
                message="Vector DB is accessible",
                response_time_ms=round(response_time, 2),
                details={
                    "path": str(self.chromadb_path),
                    "collections_count": len(collections),
                    "collections": [col.name for col in collections]
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="vector_db",
                status=HealthStatus.DEGRADED,
                message=f"Vector DB error: {str(e)}",
                response_time_ms=round((time.time() - start_time) * 1000, 2)
            )
    
    async def check_gemini_api(self) -> ComponentHealth:
        """Check Gemini API reachability with lightweight test"""
        start_time = time.time()
        
        if not self.gemini_api_key:
            return ComponentHealth(
                name="gemini_api",
                status=HealthStatus.DEGRADED,
                message="Gemini API key not configured",
                response_time_ms=0.0
            )
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Lightweight test: List models endpoint
                response = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": self.gemini_api_key}
                )
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return ComponentHealth(
                        name="gemini_api",
                        status=HealthStatus.HEALTHY,
                        message="Gemini API is reachable",
                        response_time_ms=round(response_time, 2),
                        details={"status_code": response.status_code}
                    )
                elif response.status_code == 401:
                    return ComponentHealth(
                        name="gemini_api",
                        status=HealthStatus.UNHEALTHY,
                        message="Gemini API authentication failed",
                        response_time_ms=round(response_time, 2),
                        details={"status_code": response.status_code}
                    )
                else:
                    return ComponentHealth(
                        name="gemini_api",
                        status=HealthStatus.DEGRADED,
                        message=f"Gemini API returned status {response.status_code}",
                        response_time_ms=round(response_time, 2),
                        details={"status_code": response.status_code}
                    )
        
        except httpx.TimeoutException:
            return ComponentHealth(
                name="gemini_api",
                status=HealthStatus.DEGRADED,
                message="Gemini API timeout",
                response_time_ms=round((time.time() - start_time) * 1000, 2)
            )
        except Exception as e:
            return ComponentHealth(
                name="gemini_api",
                status=HealthStatus.UNHEALTHY,
                message=f"Gemini API error: {str(e)}",
                response_time_ms=round((time.time() - start_time) * 1000, 2)
            )
    
    async def check_disk_space(self) -> ComponentHealth:
        """Check available disk space"""
        start_time = time.time()
        
        try:
            import shutil
            
            # Get disk usage for database path
            stat = shutil.disk_usage(self.db_path.parent)
            
            total_gb = stat.total / (1024**3)
            used_gb = stat.used / (1024**3)
            free_gb = stat.free / (1024**3)
            percent_free = (stat.free / stat.total) * 100
            
            response_time = (time.time() - start_time) * 1000
            
            if percent_free >= self.disk_threshold:
                status_level = HealthStatus.HEALTHY
                message = f"Disk space is adequate ({percent_free:.1f}% free)"
            elif percent_free >= self.disk_threshold / 2:
                status_level = HealthStatus.DEGRADED
                message = f"Disk space is low ({percent_free:.1f}% free)"
            else:
                status_level = HealthStatus.UNHEALTHY
                message = f"Disk space is critically low ({percent_free:.1f}% free)"
            
            return ComponentHealth(
                name="disk_space",
                status=status_level,
                message=message,
                response_time_ms=round(response_time, 2),
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "percent_free": round(percent_free, 2)
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk space check failed: {str(e)}",
                response_time_ms=round((time.time() - start_time) * 1000, 2)
            )
    
    async def check_cache(self) -> ComponentHealth:
        """Check cache functionality (placeholder for future implementation)"""
        start_time = time.time()
        
        try:
            # TODO: Implement actual cache check
            # For now, return healthy status
            
            response_time = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name="cache",
                status=HealthStatus.HEALTHY,
                message="Cache is functional",
                response_time_ms=round(response_time, 2),
                details={"type": "in-memory"}
            )
        
        except Exception as e:
            return ComponentHealth(
                name="cache",
                status=HealthStatus.DEGRADED,
                message=f"Cache check failed: {str(e)}",
                response_time_ms=round((time.time() - start_time) * 1000, 2)
            )


# FastAPI Router for health endpoints
health_router = APIRouter(prefix="/health", tags=["health"])

# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def init_health_checker(
    db_path: str,
    chromadb_path: str,
    gemini_api_key: Optional[str] = None
) -> None:
    """Initialize global health checker"""
    global _health_checker
    _health_checker = HealthChecker(
        db_path=db_path,
        chromadb_path=chromadb_path,
        gemini_api_key=gemini_api_key
    )


@health_router.get("")
async def health_check(response: Response) -> Dict[str, Any]:
    """
    Basic health check endpoint
    
    Returns simple health status without detailed checks.
    Suitable for load balancer health probes.
    """
    if _health_checker is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "message": "Health checker not initialized"}
    
    system_health = await _health_checker.check_health(detailed=False)
    
    if system_health.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif system_health.status == HealthStatus.DEGRADED:
        response.status_code = status.HTTP_200_OK
    
    return {
        "status": system_health.status.value,
        "timestamp": system_health.timestamp,
        "response_time_ms": system_health.overall_response_time_ms
    }


@health_router.get("/detailed")
async def detailed_health_check(response: Response) -> Dict[str, Any]:
    """
    Detailed health check endpoint
    
    Returns comprehensive health information for all components.
    """
    if _health_checker is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "message": "Health checker not initialized"}
    
    system_health = await _health_checker.check_health(detailed=True)
    
    if system_health.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif system_health.status == HealthStatus.DEGRADED:
        response.status_code = status.HTTP_200_OK
    
    return {
        "status": system_health.status.value,
        "timestamp": system_health.timestamp,
        "response_time_ms": system_health.overall_response_time_ms,
        "components": {
            name: {
                "status": comp.status.value,
                "message": comp.message,
                "response_time_ms": comp.response_time_ms,
                "details": comp.details
            }
            for name, comp in system_health.components.items()
        }
    }


@health_router.get("/live")
async def liveness_probe(response: Response) -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint
    
    Returns 200 if the application is running.
    Kubernetes will restart the pod if this fails.
    """
    return {"status": "alive"}


@health_router.get("/ready")
async def readiness_probe(response: Response) -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint
    
    Returns 200 if the application is ready to serve traffic.
    Kubernetes will remove pod from service if this fails.
    """
    if _health_checker is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "message": "Health checker not initialized"}
    
    system_health = await _health_checker.check_health(detailed=False)
    
    # Consider system ready if not completely unhealthy
    if system_health.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "message": "System is unhealthy"}
    
    return {
        "status": "ready",
        "timestamp": system_health.timestamp
    }
