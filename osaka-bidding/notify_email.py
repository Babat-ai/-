import logging
import os
import smtplib
import sys
from collections import defaultdict
from email.message import EmailMessage

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_digest_body(rows) -> str:
    by_municipality = defaultdict(list)
    for row in rows:
        by_municipality[row["municipality"]].append(row)

    lines = [f"新着入札案件: {len(rows)}件\n"]
    for municipality in sorted(by_municipality):
        lines.append(f"■ {municipality}")
        for row in by_municipality[municipality]:
            deadline = f"（締切: {row['deadline']}）" if row["deadline"] else ""
            lines.append(f"・{row['title']}{deadline}")
            lines.append(f"  {row['url']}")
        lines.append("")
    return "\n".join(lines)


def send_digest(rows) -> None:
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    mail_from = os.environ.get("MAIL_FROM", smtp_user)
    mail_to = os.environ["MAIL_TO"]

    msg = EmailMessage()
    msg["Subject"] = f"【大阪府入札情報】新着{len(rows)}件"
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content(build_digest_body(rows))

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)


def main() -> int:
    if not os.environ.get("SMTP_HOST"):
        logger.warning("SMTP_HOST が未設定のため、メール送信をスキップします（GitHub Secrets未設定？）。")
        return 0

    conn = db.connect()
    rows = db.fetch_unnotified(conn)

    if not rows:
        logger.info("新着案件なし。メール送信をスキップします。")
        conn.close()
        return 0

    send_digest(rows)
    db.mark_notified(conn, [row["id"] for row in rows])
    logger.info("%d件の新着案件をメール通知しました。", len(rows))
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
