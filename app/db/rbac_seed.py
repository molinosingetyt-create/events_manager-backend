"""Datos iniciales de permissions / profiles / profile_permissions (migración 006 y reparación)."""

from sqlalchemy import Connection, text

PERMISSIONS = [
    ("users.view", "Ver usuarios"),
    ("users.create", "Crear usuarios"),
    ("users.edit", "Editar usuarios"),
    ("users.delete", "Eliminar / desactivar usuarios"),
    ("employees.view", "Ver empleados"),
    ("employees.create", "Crear empleados"),
    ("employees.edit", "Editar empleados"),
    ("employees.delete", "Eliminar empleados"),
    ("areas.view", "Ver áreas"),
    ("areas.create", "Crear áreas"),
    ("areas.edit", "Editar áreas"),
    ("areas.delete", "Eliminar áreas"),
    ("overtime.view", "Ver horas extra"),
    ("overtime.create", "Crear solicitudes de horas extra"),
    ("overtime.edit", "Editar horas extra"),
    ("overtime.delete", "Eliminar horas extra"),
    ("overtime.approve", "Aprobar / rechazar horas extra"),
    ("incapacity.view", "Ver incapacidades y notas"),
    ("incapacity.create", "Crear incapacidades / notas"),
    ("incapacity.edit", "Editar incapacidades / notas"),
    ("incapacity.delete", "Eliminar incapacidades / notas"),
    ("incapacity.approve", "Aprobar / rechazar incapacidades"),
    ("catalog.settings", "Catálogos (temporal, EPS/ARL, diagnósticos)"),
    ("security.profiles", "Administrar perfiles"),
    ("security.permissions", "Administrar permisos"),
]


def seed_rbac_sync(conn: Connection) -> None:
    """Inserta permisos, perfiles y vínculos (idempotente si ya hay filas en permissions)."""
    existing = conn.execute(text("SELECT COUNT(*) FROM permissions")).scalar()
    if existing and existing > 0:
        return

    for i, (code, name) in enumerate(PERMISSIONS):
        conn.execute(
            text(
                """
                INSERT INTO permissions (code, name, description, is_system, sort_order)
                VALUES (:code, :name, NULL, true, :so)
                """
            ),
            {"code": code, "name": name, "so": i},
        )

    profiles_seed = [
        ("ADMIN", "Administrador", "Acceso completo y catálogos", "ADMIN"),
        ("HR", "Recursos humanos", "Gestión de personas y registros", "HR"),
        ("MANAGEMENT", "Gerencia", "Aprobaciones y visión global", "MANAGEMENT"),
        ("LEADER", "Líder", "Equipo y área asignada", "LEADER"),
    ]
    for i, (code, name, desc, bk) in enumerate(profiles_seed):
        conn.execute(
            text(
                """
                INSERT INTO profiles (code, name, description, behavior_key, is_system, sort_order)
                VALUES (:code, :name, :desc, :bk, true, :so)
                """
            ),
            {"code": code, "name": name, "desc": desc, "bk": bk, "so": i},
        )

    all_codes = [p[0] for p in PERMISSIONS]
    admin_codes = all_codes
    hr_codes = [
        c
        for c in all_codes
        if c
        not in (
            "overtime.approve",
            "incapacity.approve",
            "catalog.settings",
            "security.profiles",
            "security.permissions",
        )
    ]
    mgmt_codes = [
        "users.view",
        "employees.view",
        "overtime.view",
        "overtime.create",
        "overtime.edit",
        "overtime.approve",
        "incapacity.view",
        "incapacity.create",
        "incapacity.edit",
    ]
    leader_codes = [
        "employees.view",
        "overtime.view",
        "overtime.create",
        "overtime.edit",
        "incapacity.view",
        "incapacity.create",
        "incapacity.edit",
    ]

    for profile_code, codes in [
        ("ADMIN", admin_codes),
        ("HR", hr_codes),
        ("MANAGEMENT", mgmt_codes),
        ("LEADER", leader_codes),
    ]:
        pid = conn.execute(text("SELECT id FROM profiles WHERE code = :c"), {"c": profile_code}).scalar_one()
        for perm_code in codes:
            rid = conn.execute(
                text("SELECT id FROM permissions WHERE code = :c"),
                {"c": perm_code},
            ).scalar_one_or_none()
            if rid is None:
                continue
            conn.execute(
                text("INSERT INTO profile_permissions (profile_id, permission_id) VALUES (:p, :m)"),
                {"p": pid, "m": rid},
            )
