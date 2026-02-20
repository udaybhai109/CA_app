import json

from .models import AuditLog


def log_action(session, user_id, action, entity_type, entity_id, metadata=None):
    metadata_text = None
    if metadata is not None:
        metadata_text = json.dumps(metadata)

    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_text=metadata_text,
    )
    session.add(audit_log)
    session.commit()
    session.refresh(audit_log)
    return audit_log
