import json
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from analyzer.cost_estimator import get_severity

logger = logging.getLogger(__name__)
console = Console()


def print_report(findings, total):
    """Print a rich formatted waste report to the terminal."""
    if not findings:
        console.print(Panel("[bold green]✅ No wasted resources found![/bold green]", title="AWS Waste Report"))
        return

    table = Table(title="☁️  AWS Waste Report", show_lines=True, border_style="bright_blue")
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Resource ID", style="white", width=22)
    table.add_column("Detail", style="yellow")
    table.add_column("Cost/Month", style="red", justify="right", width=12)
    table.add_column("Severity", justify="center", width=10)

    severity_styles = {
        "high": "[bold red]🔴 HIGH[/bold red]",
        "medium": "[bold yellow]🟡 MED[/bold yellow]",
        "low": "[bold green]🟢 LOW[/bold green]",
    }

    for i, f in enumerate(findings, 1):
        severity = get_severity(f["waste_usd"])
        r_type = f.get("type") or f.get("resource_type", "Unknown")
        r_id = f.get("id") or f.get("resource_id", "Unknown")
        table.add_row(
            str(i),
            r_type,
            r_id,
            f["detail"],
            f"${f['waste_usd']:.2f}",
            severity_styles.get(severity, "")
        )

    console.print()
    console.print(table)
    console.print()
    console.print(Panel(
        f"[bold red]💰 Total Monthly Waste: ${total:.2f}[/bold red]  |  "
        f"[bold white]📊 Resources: {len(findings)}[/bold white]  |  "
        f"[bold green]💵 Annual Projection: ${total * 12:.2f}[/bold green]",
        title="Summary",
        border_style="bright_red"
    ))


def build_report_text(findings, total):
    """Build a plain-text version of the report for the AI advisor."""
    lines = [f"Total waste: ${total:.2f}/month (${total * 12:.2f}/year)\n"]
    lines.append(f"Resources found: {len(findings)}\n")
    for f in findings:
        severity = get_severity(f["waste_usd"]).upper()
        r_type = f.get("type") or f.get("resource_type", "Unknown")
        r_id = f.get("id") or f.get("resource_id", "Unknown")
        region = f.get("region") or "unknown-region"
        lines.append(f"- [{r_type}] {r_id} (Region: {region}): {f['detail']} — ${f['waste_usd']:.2f}/month [{severity}]")
    return "\n".join(lines)

