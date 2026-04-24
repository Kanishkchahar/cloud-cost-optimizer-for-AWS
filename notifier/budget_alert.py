"""
budget_alert.py — Budget threshold checker with email notifications.

Checks if the total monthly waste exceeds BUDGET_THRESHOLD from .env.
Sends an email alert via SMTP when the threshold is breached.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import (
    BUDGET_THRESHOLD, SMTP_HOST, SMTP_PORT,
    SMTP_USER, SMTP_PASSWORD, ALERT_FROM, ALERT_TO
)

logger = logging.getLogger(__name__)


def check_budget(total_waste, findings):
    """
    Check if total waste exceeds the budget threshold.

    Returns:
        dict with keys:
            - exceeded (bool): True if over budget
            - threshold (float): The configured threshold
            - total_waste (float): The actual waste amount
            - overage (float): How much over (0 if under)
            - percentage (float): Waste as % of threshold
    """
    exceeded = total_waste >= BUDGET_THRESHOLD
    overage = max(0, total_waste - BUDGET_THRESHOLD)
    percentage = (total_waste / BUDGET_THRESHOLD * 100) if BUDGET_THRESHOLD > 0 else 0

    result = {
        "exceeded": exceeded,
        "threshold": BUDGET_THRESHOLD,
        "total_waste": round(total_waste, 2),
        "overage": round(overage, 2),
        "percentage": round(percentage, 1),
        "timestamp": datetime.now().isoformat(),
    }

    if exceeded:
        logger.warning(
            f"BUDGET ALERT: ${total_waste:.2f} exceeds threshold of ${BUDGET_THRESHOLD:.2f} "
            f"(+${overage:.2f}, {percentage:.1f}%)"
        )
    else:
        logger.info(
            f"Budget OK: ${total_waste:.2f} / ${BUDGET_THRESHOLD:.2f} ({percentage:.1f}%)"
        )

    return result


def send_alert_email(budget_result, findings):
    """
    Send an email alert when budget threshold is exceeded.

    Requires SMTP settings to be configured in .env.
    Returns True if email was sent, False otherwise.
    """
    # Check if email is configured
    if not all([SMTP_USER, SMTP_PASSWORD, ALERT_FROM, ALERT_TO]):
        logger.warning(
            "Email not configured. Set SMTP_USER, SMTP_PASSWORD, ALERT_FROM, "
            "ALERT_TO in .env to enable email alerts."
        )
        return False

    try:
        # Build email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"[AWS Cost Alert] Budget Exceeded: "
            f"${budget_result['total_waste']:.2f} / ${budget_result['threshold']:.2f}"
        )
        msg["From"] = ALERT_FROM
        msg["To"] = ALERT_TO

        # Plain text version
        text_body = _build_text_email(budget_result, findings)

        # HTML version
        html_body = _build_html_email(budget_result, findings)

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(ALERT_FROM, ALERT_TO.split(","), msg.as_string())

        logger.info(f"Budget alert email sent to {ALERT_TO}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD in .env. "
            "For Gmail, use an App Password: https://myaccount.google.com/apppasswords"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False


def _build_text_email(budget_result, findings):
    """Build plain-text email body."""
    lines = [
        "AWS COST OPTIMIZER - BUDGET ALERT",
        "=" * 40,
        "",
        f"Monthly Waste:    ${budget_result['total_waste']:.2f}",
        f"Budget Threshold: ${budget_result['threshold']:.2f}",
        f"Over Budget By:   ${budget_result['overage']:.2f}",
        f"Usage:            {budget_result['percentage']:.1f}%",
        f"Detected At:      {budget_result['timestamp']}",
        "",
        "WASTED RESOURCES:",
        "-" * 40,
    ]

    for f in findings:
        lines.append(f"  [{f['type']}] {f['id']}: {f['detail']} - ${f['waste_usd']:.2f}/mo")

    lines.extend([
        "",
        "ACTION REQUIRED:",
        "Review and clean up these resources to reduce costs.",
        "Run: python main.py --scan --dry-run",
        "",
        "-- AWS Smart Cost Optimizer"
    ])

    return "\n".join(lines)


def _build_html_email(budget_result, findings):
    """Build premium HTML email body with modern styling."""
    pct = budget_result['percentage']
    bar_pct = min(pct, 100)
    bar_color = "#ef4444" if pct >= 100 else "#f59e0b" if pct >= 75 else "#10b981"
    overage = budget_result['overage']
    total = budget_result['total_waste']
    threshold = budget_result['threshold']
    annual = total * 12
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y at %I:%M %p")

    # Type icons (text-based for email compatibility)
    type_badges = {
        "EC2": ("#06b6d4", "#083344", "EC2"),
        "EBS": ("#6366f1", "#1e1b4b", "EBS"),
        "ElasticIP": ("#f59e0b", "#451a03", "EIP"),
        "Snapshot": ("#ec4899", "#500724", "SNAP"),
    }

    rows = ""
    for i, f in enumerate(findings):
        bg = "#111827" if i % 2 == 0 else "#0d1117"
        badge_color, badge_bg, badge_label = type_badges.get(f['type'], ("#94a3b8", "#1e293b", f['type']))
        sev_color = "#ef4444" if f['waste_usd'] >= 50 else "#f59e0b" if f['waste_usd'] >= 10 else "#10b981"
        sev_label = "HIGH" if f['waste_usd'] >= 50 else "MED" if f['waste_usd'] >= 10 else "LOW"
        rows += f"""
        <tr style="background:{bg}">
            <td style="padding:14px 16px">
                <span style="display:inline-block;padding:4px 10px;border-radius:100px;font-size:11px;font-weight:700;color:{badge_color};background:{badge_bg};border:1px solid {badge_color}33;letter-spacing:0.5px">{badge_label}</span>
            </td>
            <td style="padding:14px 16px;font-family:'Courier New',monospace;color:#e2e8f0;font-size:13px">{f['id']}</td>
            <td style="padding:14px 16px;color:#94a3b8;font-size:13px">{f['detail']}</td>
            <td style="padding:14px 16px;font-weight:800;color:{sev_color};font-size:14px;text-align:right">${f['waste_usd']:.2f}</td>
            <td style="padding:14px 16px;text-align:center">
                <span style="display:inline-block;padding:3px 8px;border-radius:100px;font-size:10px;font-weight:700;color:{sev_color};background:{sev_color}18;border:1px solid {sev_color}30">{sev_label}</span>
            </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#06080f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;-webkit-font-smoothing:antialiased">

    <!-- Outer wrapper -->
    <div style="max-width:680px;margin:0 auto;padding:24px 16px">

        <!-- Header with gradient banner -->
        <div style="background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 50%,#0c1220 100%);border-radius:16px 16px 0 0;border:1px solid #6366f133;border-bottom:none;padding:32px 32px 24px;text-align:center">
            <!-- Logo -->
            <div style="display:inline-block;padding:10px 14px;background:#6366f118;border:1px solid #6366f130;border-radius:12px;margin-bottom:16px">
                <span style="font-size:22px">☁️</span>
            </div>
            <h1 style="color:#f1f5f9;font-size:22px;font-weight:800;margin:0 0 4px;letter-spacing:-0.5px">AWS Smart Cost Optimizer</h1>
            <p style="color:#64748b;font-size:13px;margin:0">Cloud Intelligence Platform</p>
        </div>

        <!-- Alert banner -->
        <div style="background:linear-gradient(90deg,#ef4444,#dc2626);padding:16px 32px;text-align:center">
            <span style="color:#fff;font-size:15px;font-weight:700;letter-spacing:0.3px">⚠️&nbsp; BUDGET THRESHOLD EXCEEDED &nbsp;⚠️</span>
        </div>

        <!-- Main content area -->
        <div style="background:#0d1117;border-left:1px solid #6366f118;border-right:1px solid #6366f118;padding:0">

            <!-- Date -->
            <div style="padding:20px 32px 0;text-align:center">
                <span style="color:#64748b;font-size:12px">{date_str}</span>
            </div>

            <!-- Key metrics -->
            <div style="padding:24px 32px">
                <table style="width:100%;border-collapse:separate;border-spacing:10px 0">
                    <tr>
                        <td style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:20px;text-align:center;width:33%">
                            <div style="color:#64748b;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Monthly Waste</div>
                            <div style="color:#ef4444;font-size:28px;font-weight:800;letter-spacing:-1px">${total:.2f}</div>
                        </td>
                        <td style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:20px;text-align:center;width:33%">
                            <div style="color:#64748b;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Threshold</div>
                            <div style="color:#f1f5f9;font-size:28px;font-weight:800;letter-spacing:-1px">${threshold:.2f}</div>
                        </td>
                        <td style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:20px;text-align:center;width:33%">
                            <div style="color:#64748b;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Over By</div>
                            <div style="color:#f97316;font-size:28px;font-weight:800;letter-spacing:-1px">+${overage:.2f}</div>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Progress bar -->
            <div style="padding:0 32px 24px">
                <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                    <span style="color:#94a3b8;font-size:12px;font-weight:600">Budget Usage</span>
                    <span style="color:{bar_color};font-size:13px;font-weight:800">{pct:.1f}%</span>
                </div>
                <div style="background:#1e293b;border-radius:8px;height:14px;overflow:hidden">
                    <div style="background:linear-gradient(90deg,{bar_color},{bar_color}cc);height:100%;width:{bar_pct:.0f}%;border-radius:8px"></div>
                </div>
            </div>

            <!-- Annual projection callout -->
            <div style="margin:0 32px 24px;background:linear-gradient(135deg,#6366f110,#06b6d410);border:1px solid #6366f125;border-radius:12px;padding:16px 20px;text-align:center">
                <span style="color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">Annual Projection at Current Rate</span>
                <div style="color:#818cf8;font-size:32px;font-weight:800;margin-top:4px;letter-spacing:-1px">${annual:.2f}</div>
            </div>

            <!-- Resource table -->
            <div style="margin:0 32px 24px;border:1px solid #1e293b;border-radius:12px;overflow:hidden">
                <div style="padding:14px 16px;background:#111827;border-bottom:1px solid #1e293b">
                    <span style="color:#f1f5f9;font-size:14px;font-weight:700">🔍 Wasted Resources ({len(findings)})</span>
                </div>
                <table style="width:100%;border-collapse:collapse">
                    <thead>
                        <tr style="background:#0a0e17">
                            <th style="padding:10px 16px;text-align:left;color:#475569;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px">Type</th>
                            <th style="padding:10px 16px;text-align:left;color:#475569;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px">Resource ID</th>
                            <th style="padding:10px 16px;text-align:left;color:#475569;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px">Detail</th>
                            <th style="padding:10px 16px;text-align:right;color:#475569;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px">Cost/Mo</th>
                            <th style="padding:10px 16px;text-align:center;color:#475569;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px">Risk</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                    <tfoot>
                        <tr style="background:#111827;border-top:2px solid #1e293b">
                            <td colspan="3" style="padding:14px 16px;color:#94a3b8;font-size:13px;font-weight:700">TOTAL MONTHLY WASTE</td>
                            <td style="padding:14px 16px;text-align:right;color:#ef4444;font-size:16px;font-weight:800">${total:.2f}</td>
                            <td></td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <!-- Recommendations -->
            <div style="margin:0 32px 24px;background:#111827;border:1px solid #1e293b;border-radius:12px;padding:20px">
                <div style="color:#f1f5f9;font-size:14px;font-weight:700;margin-bottom:12px">💡 Recommended Actions</div>
                <div style="padding:8px 0;border-bottom:1px solid #1e293b40">
                    <span style="color:#10b981;font-weight:700;margin-right:8px">1.</span>
                    <span style="color:#94a3b8;font-size:13px">Review detected resources in the dashboard</span>
                </div>
                <div style="padding:8px 0;border-bottom:1px solid #1e293b40">
                    <span style="color:#10b981;font-weight:700;margin-right:8px">2.</span>
                    <span style="color:#94a3b8;font-size:13px">Delete unused EBS volumes and old snapshots</span>
                </div>
                <div style="padding:8px 0;border-bottom:1px solid #1e293b40">
                    <span style="color:#10b981;font-weight:700;margin-right:8px">3.</span>
                    <span style="color:#94a3b8;font-size:13px">Right-size or terminate idle EC2 instances</span>
                </div>
                <div style="padding:8px 0">
                    <span style="color:#10b981;font-weight:700;margin-right:8px">4.</span>
                    <span style="color:#94a3b8;font-size:13px">Release unassociated Elastic IPs</span>
                </div>
            </div>

            <!-- CTA Button -->
            <div style="padding:0 32px 32px;text-align:center">
                <span style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#6366f1,#4f46e5);color:#fff;font-size:14px;font-weight:700;border-radius:10px;text-decoration:none;letter-spacing:0.3px">Open Dashboard to Take Action →</span>
            </div>
        </div>

        <!-- Footer -->
        <div style="background:#080a12;border-radius:0 0 16px 16px;border:1px solid #6366f118;border-top:1px solid #1e293b;padding:24px 32px;text-align:center">
            <div style="color:#475569;font-size:11px;line-height:1.6">
                <div style="margin-bottom:4px">Sent by <strong style="color:#818cf8">AWS Smart Cost Optimizer</strong></div>
                <div>You're receiving this because your monthly waste exceeded $<strong>{threshold:.2f}</strong></div>
                <div style="margin-top:8px;color:#334155">Adjust your threshold in Settings → Budget Threshold</div>
            </div>
        </div>

    </div>
</body>
</html>"""

