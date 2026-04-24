import argparse
import logging
import sys
import io

# Force UTF-8 encoding for Windows terminals to prevent emoji crashes
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

from db.database import setup_db, save_scan, save_resource, save_alert
from data_source import get_findings, get_ai_advice, USE_DEMO_DATA
from analyzer.cost_estimator import estimate_total, get_breakdown_by_type
from analyzer.reporter import print_report, build_report_text, save_report_json
from actor.cleaner import cleanup_resource
from notifier.budget_alert import check_budget, send_alert_email
from config import BUDGET_THRESHOLD

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("optimizer.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_scan():
    """Run scan using data_source (demo or real AWS based on USE_DEMO_DATA flag)."""
    mode = "DEMO" if USE_DEMO_DATA else "AWS"
    console.print(f"[bold blue]Running scan in {mode} mode...[/bold blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Scanning ({mode})...", total=1)
        findings = get_findings()
        progress.advance(task)

    logger.info(f"Scan complete ({mode}): {len(findings)} resources found")
    return findings


def main():
    parser = argparse.ArgumentParser(
        description="☁️  AWS Smart Cost Optimizer — Find and eliminate cloud waste",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --scan              Scan for wasted resources
  python main.py --scan --ai         Scan + get AI recommendations
  python main.py --scan --dry-run    Preview what would be deleted
  python main.py --scan --execute    Delete wasted resources (with confirmation)
  python main.py --dashboard         Launch the web dashboard
        """
    )
    parser.add_argument("--scan", action="store_true", help="Run a full scan of your AWS account")
    parser.add_argument("--dry-run", action="store_true", help="Show what actions would be taken (safe)")
    parser.add_argument("--execute", action="store_true", help="Execute cleanup actions (asks for confirmation)")
    parser.add_argument("--ai", action="store_true", help="Get AI-powered recommendations via Ollama")
    parser.add_argument("--dashboard", action="store_true", help="Launch the web dashboard")
    args = parser.parse_args()

    # Show banner
    console.print(Panel(
        "[bold cyan]☁️  AWS Smart Cost Optimizer[/bold cyan]\n"
        "[dim]Find waste. Save money. Sleep better.[/dim]",
        border_style="bright_cyan"
    ))

    setup_db()

    if args.dashboard:
        from dashboard.app import start_dashboard
        start_dashboard()
        return

    if not args.scan and not args.dashboard:
        parser.print_help()
        return

    if args.scan:
        console.print()
        findings = run_scan()
        total = estimate_total(findings)

        # Print the report
        print_report(findings, total)

        # Show breakdown
        if findings:
            breakdown = get_breakdown_by_type(findings)
            console.print()
            console.print("[bold]📊 Waste Breakdown by Service:[/bold]")
            for svc, cost in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                bar_len = int(cost / total * 30) if total > 0 else 0
                bar = "█" * bar_len
                console.print(f"  [cyan]{svc:12}[/cyan] [red]{bar}[/red] ${cost:.2f}")

        # Save to database
        scan_id = save_scan(total, len(findings))
        for f in findings:
            save_resource(scan_id, f["type"], f["id"], f["detail"], f["waste_usd"], f["region"])

        # Save JSON report
        save_report_json(findings, total)

        # Budget check
        console.print()
        budget = check_budget(total, findings)
        if budget["exceeded"]:
            console.print(Panel(
                f"[bold red]BUDGET ALERT: ${budget['total_waste']:.2f} exceeds "
                f"threshold of ${budget['threshold']:.2f} (+${budget['overage']:.2f})[/bold red]\n"
                f"[yellow]Usage: {budget['percentage']:.1f}% of budget[/yellow]",
                title="Budget Alert",
                border_style="bright_red"
            ))
            email_sent = send_alert_email(budget, findings)
            save_alert("budget_exceeded",
                f"Waste ${budget['total_waste']:.2f} exceeds threshold ${budget['threshold']:.2f}",
                budget['total_waste'], budget['threshold'], email_sent)
            if email_sent:
                console.print("[green]  Alert email sent successfully.[/green]")
            else:
                console.print("[dim]  Email not sent (configure SMTP in .env to enable).[/dim]")
        else:
            console.print(Panel(
                f"[bold green]Budget OK: ${budget['total_waste']:.2f} / "
                f"${budget['threshold']:.2f} ({budget['percentage']:.1f}%)[/bold green]",
                title="Budget Status",
                border_style="green"
            ))

        # AI advice
        if args.ai:
            console.print()
            console.print(Panel("[bold]🤖 Asking AI for recommendations...[/bold]", border_style="bright_magenta"))
            report_text = build_report_text(findings, total)
            advice = get_ai_advice(report_text)
            console.print()
            console.print(Panel(advice, title="🤖 AI Recommendation", border_style="bright_magenta"))

        # Dry run
        if args.dry_run and findings:
            console.print()
            console.print(Panel("[bold yellow]🧪 Dry Run — No changes will be made[/bold yellow]", border_style="yellow"))
            for f in findings:
                cleanup_resource(f, dry_run=True)

        # Execute
        if args.execute and findings:
            console.print()
            console.print("[bold red]⚠️  WARNING: This will permanently delete resources![/bold red]")
            confirm = console.input("[bold]Type 'yes' to confirm: [/bold]")
            if confirm.strip().lower() == "yes":
                console.print()
                success = 0
                for f in findings:
                    if cleanup_resource(f, dry_run=False):
                        success += 1
                console.print(Panel(
                    f"[bold green]✅ Cleaned up {success}/{len(findings)} resources[/bold green]",
                    border_style="green"
                ))
            else:
                console.print("[yellow]Cleanup cancelled.[/yellow]")

        console.print()
        logger.info("Scan complete.")


if __name__ == "__main__":
    main()
