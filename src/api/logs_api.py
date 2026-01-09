"""
Logs API Router - Permanent action logs with search, filter, and export
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime, timezone
import json

from src.database import get_db_context
from src.models import ActionLog

router = APIRouter(prefix="/api/logs", tags=["Logs"])

# Will be injected from main.py
_redis_client = None


def configure(redis_client):
    """Configure router with shared dependencies from main.py"""
    global _redis_client
    _redis_client = redis_client


@router.get("")
async def get_logs(
    search: Optional[str] = None,
    mode: Optional[str] = None,  # 'autonomous' or 'manual'
    service: Optional[str] = None,
    action_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    """Get permanent action logs with search, filter, and pagination"""
    try:
        logs = []
        
        # First get from database (permanent storage)
        with get_db_context() as db:
            query = db.query(ActionLog).order_by(ActionLog.created_at.desc())
            
            if mode:
                query = query.filter(ActionLog.mode == mode)
            if service:
                query = query.filter(ActionLog.service.ilike(f"%{service}%"))
            if action_type:
                query = query.filter(ActionLog.action_type == action_type)
            if status:
                query = query.filter(ActionLog.status == status)
            if search:
                query = query.filter(
                    (ActionLog.action_type.ilike(f"%{search}%")) |
                    (ActionLog.service.ilike(f"%{search}%")) |
                    (ActionLog.description.ilike(f"%{search}%")) |
                    (ActionLog.reason.ilike(f"%{search}%")) |
                    (ActionLog.executed_by.ilike(f"%{search}%"))
                )
            if start_date:
                query = query.filter(ActionLog.created_at >= start_date)
            if end_date:
                query = query.filter(ActionLog.created_at <= end_date)
            
            total = query.count()
            offset = (page - 1) * limit
            db_logs = query.offset(offset).limit(limit).all()
            
            for log in db_logs:
                logs.append({
                    "log_id": log.log_id,
                    "action_id": log.action_id,
                    "incident_id": log.incident_id,
                    "action_type": log.action_type,
                    "mode": log.mode,
                    "service": log.service,
                    "status": log.status,
                    "success": log.success,
                    "confidence": log.confidence,
                    "description": log.description,
                    "reason": log.reason,
                    "executed_by": log.executed_by,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "executed_at": log.executed_at.isoformat() if log.executed_at else None
                })
        
        # Also get from Redis (recent actions not yet in DB)
        redis_logs = []
        
        if _redis_client:
            # Get autonomous resolutions
            auto_res = _redis_client.lrange("autonomous_resolutions", 0, 99)
            for res_json in auto_res:
                try:
                    res = json.loads(res_json)
                    log_entry = {
                        "log_id": None,
                        "action_id": res.get("incident_id"),
                        "incident_id": res.get("incident_id"),
                        "action_type": res.get("execution_details", {}).get("action_type", "auto_resolve"),
                        "mode": "autonomous",
                        "service": res.get("execution_details", {}).get("service", "unknown"),
                        "status": "completed",
                        "success": True,
                        "confidence": res.get("execution_details", {}).get("confidence", 85),
                        "description": f"Auto-resolved incident via {res.get('execution_details', {}).get('action_type', 'restart')}",
                        "reason": res.get("notes"),
                        "executed_by": res.get("resolved_by", "AI Autopilot"),
                        "created_at": res.get("resolved_at"),
                        "executed_at": res.get("resolved_at")
                    }
                    # Apply filters
                    if mode and log_entry["mode"] != mode:
                        continue
                    if service and service.lower() not in log_entry["service"].lower():
                        continue
                    if search and search.lower() not in str(log_entry).lower():
                        continue
                    redis_logs.append(log_entry)
                except (json.JSONDecodeError, KeyError):
                    continue
            
            # Get audit logs
            audit_logs = _redis_client.lrange("audit_log", 0, 99)
            for log_json in audit_logs:
                try:
                    log = json.loads(log_json)
                    log_entry = {
                        "log_id": None,
                        "action_id": log.get("incident_id"),
                        "incident_id": log.get("incident_id"),
                        "action_type": log.get("action", log.get("event", "unknown")),
                        "mode": log.get("mode", "autonomous"),
                        "service": log.get("service", "unknown"),
                        "status": "completed",
                        "success": True,
                        "confidence": log.get("details", {}).get("confidence", 85),
                        "description": log.get("event", "").replace("_", " ").title(),
                        "reason": json.dumps(log.get("details", {})),
                        "executed_by": log.get("operator", "AI Autopilot"),
                        "created_at": log.get("timestamp"),
                        "executed_at": log.get("timestamp")
                    }
                    # Apply filters
                    if mode and log_entry["mode"] != mode:
                        continue
                    if service and service.lower() not in log_entry["service"].lower():
                        continue
                    if search and search.lower() not in str(log_entry).lower():
                        continue
                    redis_logs.append(log_entry)
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # Combine and sort
        all_logs = logs + redis_logs
        all_logs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        
        # Deduplicate by action_id
        seen = set()
        unique_logs = []
        for log in all_logs:
            key = f"{log.get('action_id')}_{log.get('created_at')}"
            if key not in seen:
                seen.add(key)
                unique_logs.append(log)
        
        return {
            "logs": unique_logs[:limit],
            "total": len(unique_logs),
            "page": page,
            "limit": limit,
            "total_pages": (len(unique_logs) + limit - 1) // limit
        }
        
    except Exception as e:
        print(f"[API ERROR] Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{log_id}")
async def delete_log(log_id: int):
    """Delete a specific log entry (permanent deletion)"""
    try:
        with get_db_context() as db:
            log = db.query(ActionLog).filter(ActionLog.log_id == log_id).first()
            if not log:
                raise HTTPException(status_code=404, detail="Log not found")
            
            db.delete(log)
            db.commit()
            
            return {"success": True, "message": f"Log {log_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] Failed to delete log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_logs(
    format: str = "json",  # 'json' or 'csv'
    mode: Optional[str] = None,
    service: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Export logs as JSON or CSV for download"""
    try:
        # Get all logs matching filters
        result = await get_logs(
            mode=mode,
            service=service,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Export up to 10k records
        )
        logs = result["logs"]
        
        if format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)
            
            return JSONResponse(
                content={
                    "format": "csv",
                    "filename": f"action_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "data": output.getvalue(),
                    "total": len(logs)
                }
            )
        else:
            return {
                "format": "json",
                "filename": f"action_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "data": logs,
                "total": len(logs)
            }
            
    except Exception as e:
        print(f"[API ERROR] Failed to export logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_log(log_data: dict):
    """Create a new permanent action log entry"""
    try:
        with get_db_context() as db:
            now = datetime.now(timezone.utc)
            
            new_log = ActionLog(
                action_id=log_data.get("action_id"),
                incident_id=log_data.get("incident_id"),
                action_type=log_data.get("action_type", "unknown"),
                mode=log_data.get("mode", "manual"),
                service=log_data.get("service", "unknown"),
                status=log_data.get("status", "completed"),
                success=log_data.get("success", True),
                confidence=log_data.get("confidence"),
                description=log_data.get("description"),
                reason=log_data.get("reason"),
                execution_details=log_data.get("execution_details"),
                executed_by=log_data.get("executed_by", "dashboard_user"),
                created_at=now,
                executed_at=now
            )
            
            db.add(new_log)
            db.commit()
            db.refresh(new_log)
            
            print(f"[LOGS] Created permanent log entry: {new_log.action_type} - {new_log.service}")
            
            return {
                "success": True,
                "log_id": new_log.log_id,
                "message": "Log entry created successfully"
            }
            
    except Exception as e:
        print(f"[API ERROR] Failed to create log: {e}")
        raise HTTPException(status_code=500, detail=str(e))
