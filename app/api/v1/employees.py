import math
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, require_any_permission
from app.db.session import get_db
from app.models.employee import Employee
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeProfileAccessRead,
    EmployeeRead,
    EmployeeUpdate,
    OrgChartTreeResponse,
)
from app.schemas.employee_profile import (
    EmployeeDocumentCreate,
    EmployeeDocumentRead,
    EmployeeDocumentUpdate,
    EmployeeEducationRead,
    EmployeeFilterOptionsRead,
    EmployeeTrainingRead,
    EmployeeProfileFullRead,
    EmployeeProfilePatch,
)
from app.realtime.notify import broadcast_data_changed
from app.services import audit_service
from app.services import employee_career_service as career_svc
from app.services import employee_document_service as doc_svc
from app.services import employee_custom_field_service as custom_svc
from app.services import employee_payroll_service as payroll_svc
from app.services import employee_profile_alerts_service as alerts_svc
from app.services import employee_profile_export_service as export_svc
from app.services import employee_profile_service as profile_svc
from app.services import employee_service as svc
from app.schemas.employee_profile_phase5 import (
    EmployeeProfileAlertsBundleRead,
    EmployeeProfileAlertsListRead,
    EmployeeProfileExportListRead,
)
from app.schemas.employee_profile_phase6 import (
    EmployeeCustomFieldDefCreate,
    EmployeeCustomFieldDefRead,
    EmployeeCustomFieldDefUpdate,
    EmployeePayrollEntryRead,
    EmployeePayrollEntryWrite,
)

router = APIRouter()


def _employee_read(e: Employee) -> EmployeeRead:
    area_name = e.area.name if e.area is not None else ""
    leader_name = e.leader_user.name if e.leader_user is not None else None
    temporal_name = e.temporal_category.name if e.temporal_category is not None else ""
    return EmployeeRead(
        id=e.id,
        name=e.name,
        identification_number=e.identification_number,
        position=e.position,
        area_id=e.area_id,
        area_name=area_name,
        leader_id=e.leader_id,
        leader_name=leader_name,
        temporal_category_id=e.temporal_category_id,
        temporal_category_name=temporal_name,
        status=e.status,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


@router.get("", response_model=PaginatedResponse[EmployeeRead])
async def list_employees(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.view"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    area_id: int | None = None,
    leader_id: int | None = None,
    search: str | None = Query(None, description="Buscar por nombre o número de identificación"),
    team_only: bool = Query(
        False,
        description="Solo empleados asignados al usuario como líder (ignora area_id)",
    ),
    status: str | None = Query(None, description="Estado del registro (active/inactive)"),
    work_site_city: str | None = None,
    hierarchical_level: str | None = None,
    contract_type: str | None = None,
    collaborator_status: str | None = None,
    linkage_type: str | None = None,
) -> PaginatedResponse[EmployeeRead]:
    items, total = await svc.list_employees_for_actor(
        db,
        current,
        page=page,
        page_size=page_size,
        area_id=area_id,
        leader_id=leader_id,
        search=search,
        team_only=team_only,
        status=status,
        work_site_city=work_site_city,
        hierarchical_level=hierarchical_level,
        contract_type=contract_type,
        collaborator_status=collaborator_status,
        linkage_type=linkage_type,
    )
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.list",
        entity_type="employee",
        ip_address=client_ip(request),
    )
    await db.commit()
    pages = math.ceil(total / page_size) if page_size else None
    return PaginatedResponse(
        items=[_employee_read(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/custom-field-definitions", response_model=list[EmployeeCustomFieldDefRead])
async def list_custom_field_definitions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.custom_fields.manage"))],
    include_inactive: bool = Query(False),
) -> list[EmployeeCustomFieldDefRead]:
    if include_inactive:
        return await custom_svc.list_all_definitions_admin(db, current)
    return await custom_svc.list_field_definitions(db, current, active_only=False)


@router.post("/custom-field-definitions", response_model=EmployeeCustomFieldDefRead)
async def create_custom_field_definition(
    request: Request,
    body: EmployeeCustomFieldDefCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.custom_fields.manage"))],
) -> EmployeeCustomFieldDefRead:
    row = await custom_svc.create_field_definition(db, current, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.custom_fields.create",
        entity_type="employee_custom_field_def",
        entity_id=row.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return row


@router.patch("/custom-field-definitions/{field_id}", response_model=EmployeeCustomFieldDefRead)
async def update_custom_field_definition(
    request: Request,
    field_id: int,
    body: EmployeeCustomFieldDefUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.custom_fields.manage"))],
) -> EmployeeCustomFieldDefRead:
    row = await custom_svc.update_field_definition(db, current, field_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.custom_fields.update",
        entity_type="employee_custom_field_def",
        entity_id=field_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return row


@router.delete("/custom-field-definitions/{field_id}")
async def delete_custom_field_definition(
    request: Request,
    field_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.custom_fields.manage"))],
) -> dict[str, str]:
    await custom_svc.delete_field_definition(db, current, field_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.custom_fields.delete",
        entity_type="employee_custom_field_def",
        entity_id=field_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return {"detail": "Operación correcta"}


@router.get("/profile-alerts", response_model=EmployeeProfileAlertsListRead)
async def list_employee_profile_alerts(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.alerts"))],
) -> EmployeeProfileAlertsListRead:
    data = await alerts_svc.list_all_profile_alerts(db, current)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.profile.alerts.list",
        entity_type="employee",
        ip_address=client_ip(request),
    )
    await db.commit()
    return data


@router.get("/profile-export", response_model=EmployeeProfileExportListRead)
async def export_employee_profiles(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.export"))],
    active_only: bool = Query(True, description="Solo colaboradores activos"),
) -> EmployeeProfileExportListRead:
    data = await export_svc.export_profile_summary(db, current, active_only=active_only)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.profile.export",
        entity_type="employee",
        ip_address=client_ip(request),
    )
    await db.commit()
    return data


@router.get("/filter-options", response_model=EmployeeFilterOptionsRead)
async def employee_filter_options(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.view"))],
) -> EmployeeFilterOptionsRead:
    return await svc.get_employee_filter_options(db, current)


@router.get("/org-chart", response_model=OrgChartTreeResponse)
async def get_organization_chart(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.org_chart"))],
) -> OrgChartTreeResponse:
    data = await svc.get_organization_chart(db)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.org_chart",
        entity_type="employee",
        ip_address=client_ip(request),
    )
    await db.commit()
    return data


@router.post("", response_model=EmployeeRead)
async def create_employee(
    request: Request,
    body: EmployeeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.create"))],
) -> EmployeeRead:
    e = await svc.create_employee(db, body, actor=current)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.create",
        entity_type="employee",
        entity_id=e.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["employees"])
    return _employee_read(e)


@router.get("/{employee_id}/profile/alerts", response_model=EmployeeProfileAlertsBundleRead)
async def get_employee_profile_alerts(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.alerts"))],
) -> EmployeeProfileAlertsBundleRead:
    data = await alerts_svc.get_employee_alerts(db, current, employee_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.profile.alerts.get",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return data


@router.get("/{employee_id}/profile", response_model=EmployeeProfileFullRead)
async def get_employee_profile(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.full"))],
) -> EmployeeProfileFullRead:
    data = await profile_svc.get_full_profile(db, current, employee_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.profile.get",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return data


@router.patch("/{employee_id}/profile", response_model=EmployeeProfileFullRead)
async def patch_employee_profile(
    request: Request,
    employee_id: int,
    body: EmployeeProfilePatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.edit"))],
) -> EmployeeProfileFullRead:
    data = await profile_svc.update_profile(db, current, employee_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.profile.update",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["employees"])
    return data


@router.post("/{employee_id}/profile/photo", response_model=EmployeeProfileFullRead)
async def upload_employee_profile_photo(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.edit"))],
    file: UploadFile = File(...),
) -> EmployeeProfileFullRead:
    data = await profile_svc.upload_profile_photo(db, current, employee_id, file)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.profile.photo.upload",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["employees"])
    return data


@router.post(
    "/{employee_id}/education/{record_id}/certificate",
    response_model=EmployeeEducationRead,
)
async def upload_education_certificate(
    request: Request,
    employee_id: int,
    record_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.edit"))],
    file: UploadFile = File(...),
) -> EmployeeEducationRead:
    row = await career_svc.upload_education_certificate(db, current, employee_id, record_id, file)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.education.certificate",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return row


@router.post(
    "/{employee_id}/training/{record_id}/certificate",
    response_model=EmployeeTrainingRead,
)
async def upload_training_certificate(
    request: Request,
    employee_id: int,
    record_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.edit"))],
    file: UploadFile = File(...),
) -> EmployeeTrainingRead:
    row = await career_svc.upload_training_certificate(db, current, employee_id, record_id, file)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.training.certificate",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return row


@router.get("/{employee_id}/documents", response_model=list[EmployeeDocumentRead])
async def list_employee_documents(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.full"))],
) -> list[EmployeeDocumentRead]:
    docs = await doc_svc.list_documents(db, current, employee_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.documents.list",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return docs


@router.post("/{employee_id}/documents", response_model=EmployeeDocumentRead)
async def upload_employee_document(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.edit"))],
    file: UploadFile = File(...),
    document_kind: str = Form(...),
    display_name: Optional[str] = Form(None),
    status: str = Form("vigente"),
    expires_at: Optional[date] = Form(None),
) -> EmployeeDocumentRead:
    meta = EmployeeDocumentCreate(
        document_kind=document_kind,  # type: ignore[arg-type]
        display_name=display_name,
        status=status,  # type: ignore[arg-type]
        expires_at=expires_at,
    )
    doc = await doc_svc.create_document(db, current, employee_id, meta, file)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.documents.upload",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["employees"])
    return doc


@router.patch("/{employee_id}/documents/{document_id}", response_model=EmployeeDocumentRead)
async def patch_employee_document(
    request: Request,
    employee_id: int,
    document_id: int,
    body: EmployeeDocumentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.edit"))],
) -> EmployeeDocumentRead:
    doc = await doc_svc.update_document(db, current, employee_id, document_id, body)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.documents.update",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return doc


@router.delete("/{employee_id}/documents/{document_id}")
async def delete_employee_document(
    request: Request,
    employee_id: int,
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.profile.edit"))],
) -> dict[str, str]:
    await doc_svc.delete_document(db, current, employee_id, document_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.documents.delete",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["employees"])
    return {"detail": "Operación correcta"}


@router.get("/{employee_id}/profile-access", response_model=EmployeeProfileAccessRead)
async def get_employee_profile_access(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.view"))],
) -> EmployeeProfileAccessRead:
    e = await svc.get_employee(db, employee_id)
    if not e:
        from app.core.exceptions import not_found

        raise not_found()
    access = await profile_svc.resolve_profile_access(db, current, e)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.profile_access",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return access


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.view"))],
) -> EmployeeRead:
    e = await svc.get_employee(db, employee_id)
    if not e:
        from app.core.exceptions import not_found

        raise not_found()
    svc.ensure_employee_access(current, e)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.get",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    return _employee_read(e)


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    request: Request,
    employee_id: int,
    body: EmployeeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.edit"))],
) -> EmployeeRead:
    e = await svc.get_employee(db, employee_id)
    if not e:
        from app.core.exceptions import not_found

        raise not_found()
    e2 = await svc.update_employee(db, employee_id, body, actor=current)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.update",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["employees"])
    return _employee_read(e2)


@router.delete("/{employee_id}")
async def delete_employee(
    request: Request,
    employee_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(require_any_permission("employees.delete"))],
) -> dict[str, str]:
    await svc.delete_employee(db, employee_id)
    await audit_service.write_audit(
        db,
        user_id=current.id,
        action="employees.delete",
        entity_type="employee",
        entity_id=employee_id,
        ip_address=client_ip(request),
    )
    await db.commit()
    await broadcast_data_changed(["employees"])
    return {"detail": "Operación correcta"}
