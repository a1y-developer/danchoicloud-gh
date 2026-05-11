from app.db import models
from app.db.session import SessionLocal


def get_active_channels(
    scope_type: str, scope_name: str
) -> list[models.NotificationChannel]:
    with SessionLocal() as session:
        return (
            session.query(models.NotificationChannel)
            .filter(models.NotificationChannel.scope_type == scope_type)
            .filter(models.NotificationChannel.scope_name == scope_name)
            .filter(models.NotificationChannel.is_active.is_(True))
            .order_by(models.NotificationChannel.id.asc())
            .all()
        )


def resolve_channels(
    org_name: str | None, repo_full_name: str | None
) -> list[models.NotificationChannel]:
    channels: list[models.NotificationChannel] = []
    seen_ids: set[int] = set()

    if org_name:
        for channel in get_active_channels("org", org_name):
            if channel.id not in seen_ids:
                channels.append(channel)
                seen_ids.add(channel.id)

    if repo_full_name:
        for channel in get_active_channels("repo", repo_full_name):
            if channel.id not in seen_ids:
                channels.append(channel)
                seen_ids.add(channel.id)

    return channels
