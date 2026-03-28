"""macOS native notifications for fnsvr via osascript."""
from __future__ import annotations

import logging
import platform
import subprocess

logger = logging.getLogger(__name__)


def notify(
    title: str,
    message: str,
    subtitle: str = "",
    sound: str = "Pop",
) -> bool:
    """Send a single macOS notification via osascript.

    Args:
        title: Notification title.
        message: Notification body text (truncated to 200 chars).
        subtitle: Optional subtitle line.
        sound: macOS sound name (e.g. "Pop", "Submarine").

    Returns:
        True if the notification was sent successfully, False otherwise.
    """
    if platform.system() != "Darwin":
        logger.debug("Notifications not supported on %s", platform.system())
        return False

    # Truncate message to 200 chars (notification display limit)
    if len(message) > 200:
        message = message[:197] + "..."

    # Escape double quotes for AppleScript
    title = title.replace('"', '\\"')
    message = message.replace('"', '\\"')
    subtitle = subtitle.replace('"', '\\"')

    script = (
        f'display notification "{message}" '
        f'with title "{title}" '
        f'subtitle "{subtitle}" '
        f'sound name "{sound}"'
    )

    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return True
    except subprocess.TimeoutExpired:
        logger.warning("Notification timed out")
        return False
    except OSError as exc:
        logger.warning("Notification failed: %s", exc)
        return False
    except Exception as exc:
        logger.warning("Unexpected notification error: %s", exc)
        return False


def notify_detections(detections: list[dict], config: dict) -> None:
    """Send notifications for newly detected financial emails.

    Respects the notifications.enabled config flag. Batches notifications
    when the count exceeds batch_threshold into a single summary.

    Args:
        detections: List of dicts with keys: category, priority, subject,
            account_name.
        config: Full config dict (reads notifications section).
    """
    notif_config = config.get("notifications", {})

    if not notif_config.get("enabled", True):
        return

    if platform.system() != "Darwin":
        logger.debug("Notifications not supported on %s", platform.system())
        return

    if not detections:
        return

    batch_threshold = notif_config.get("batch_threshold", 5)
    critical_sound = notif_config.get("critical_sound", "Submarine")
    normal_sound = notif_config.get("normal_sound", "Pop")

    has_critical = any(d.get("priority") == "critical" for d in detections)

    if len(detections) > batch_threshold:
        # Summary notification
        priority_counts: dict[str, int] = {}
        for d in detections:
            p = d.get("priority", "unknown")
            priority_counts[p] = priority_counts.get(p, 0) + 1

        parts = [f"{count} {prio}" for prio, count in priority_counts.items()]
        message = ", ".join(parts)
        sound = critical_sound if has_critical else normal_sound

        notify(
            title=f"fnsvr: {len(detections)} new detections",
            message=message,
            sound=sound,
        )
    else:
        # Individual notifications
        for d in detections:
            sound = critical_sound if d.get("priority") == "critical" else normal_sound
            category_label = d.get("category", "detection").replace("_", " ").title()
            notify(
                title=f"fnsvr: {category_label}",
                message=d.get("subject", ""),
                subtitle=d.get("account_name", ""),
                sound=sound,
            )
