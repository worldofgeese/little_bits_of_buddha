"""Schedule and manage Dapr Jobs for per-user delivery."""

import httpx

DAPR_HTTP_PORT = 3500  # Dapr sidecar HTTP port


def schedule_daily_sutta(chat_id: str, time_utc: str = "06:00", timezone: str = "UTC"):
    """Register a daily sutta delivery job for a seeker."""
    job_name = f"daily-sutta-{chat_id}"
    # Use Dapr Jobs HTTP API (alpha)
    response = httpx.post(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0-alpha1/jobs/{job_name}",
        json={
            "data": {"chat_id": chat_id},
            "schedule": f"0 0 {int(time_utc.split(':')[0])} * * *",
            "overwrite": True,
        },
    )
    response.raise_for_status()
    return job_name


def cancel_daily_sutta(chat_id: str):
    """Cancel daily sutta delivery for a seeker."""
    job_name = f"daily-sutta-{chat_id}"
    response = httpx.delete(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0-alpha1/jobs/{job_name}"
    )
    return response.status_code == 204


def schedule_weekly_checkin(chat_id: str, day_of_week: int = 0):
    """Register a weekly check-in job (default: Sunday)."""
    job_name = f"weekly-checkin-{chat_id}"
    response = httpx.post(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0-alpha1/jobs/{job_name}",
        json={
            "data": {"chat_id": chat_id},
            "schedule": f"0 0 9 * * {day_of_week}",
            "overwrite": True,
        },
    )
    response.raise_for_status()
    return job_name


def cancel_weekly_checkin(chat_id: str):
    """Cancel weekly check-in for a seeker."""
    job_name = f"weekly-checkin-{chat_id}"
    response = httpx.delete(
        f"http://localhost:{DAPR_HTTP_PORT}/v1.0-alpha1/jobs/{job_name}"
    )
    return response.status_code == 204
