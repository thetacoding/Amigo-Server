"""Unified evaluation API endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.base import ResponseModel
from app.schemas.eval import EvalRunRequest
from app.services.eval import get_eval_gateway_service

router = APIRouter()


@router.post("/run")
async def run_eval(req: EvalRunRequest):
    try:
        gateway = get_eval_gateway_service()
        data = await gateway.run(
            scene=req.scene,
            task=req.task,
            inputs=req.inputs.model_dump(exclude_none=True),
            options=req.options.model_dump(exclude_none=True),
            context={
                "session_id": req.sessionInfo.session_id,
                "interaction_id": req.sessionInfo.interaction_id,
                "user_id": req.userInfo.user_id,
                "device_id": req.DeviceInfo.device_id,
                "package_name": req.AppBaseInfo.package_name,
                "gps": req.SystemSetting.gps,
            },
        )
        return ResponseModel(data=data)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ResponseModel(code=500, msg=str(e)).model_dump(),
        )
