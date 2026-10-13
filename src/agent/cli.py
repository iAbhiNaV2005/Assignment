import sys
import uuid
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)
from agent.budget import BudgetTracker
from agent.cache import DiskCache
from agent.clients.exa import ExaClient
from agent.clients.hunter import HunterClient
from agent.clients.mailer import GmailSMTPMailer, get_mailer
from agent.clients.sheets import SheetsMirror
from agent.clients.yutori import YutoriClient
from agent.config import (
    get_config_placeholders,
    load_env_settings,
    load_templates_config,
    load_upthrust_config,
    PROJECT_ROOT,
)
from agent.db import Database
from agent.llm import LLMClient
from agent.pipeline import OutboundPipeline
from agent.steps.discover import DiscoveryStep

app = typer.Typer(help="Upthrust AI Outbound Agent CLI", no_args_is_help=True)
suppress_app = typer.Typer(help="Manage suppression list")
app.add_typer(suppress_app, name="suppress")
cache_app = typer.Typer(help="Manage local disk cache")
app.add_typer(cache_app, name="cache")

# console initialized above with force_terminal=True, legacy_windows=False


@app.command()
def doctor():
    """Check credentials, connectivity, services, and configurations."""
    settings = load_env_settings()
    db = Database()
    table = Table(title="Upthrust Outbound Agent - Doctor Diagnostic Check", show_lines=True)
    table.add_column("Component", style="bold cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    critical_failures = 0

    # 1. Configs Check
    try:
        load_upthrust_config()
        load_templates_config()
        placeholders = get_config_placeholders()
        if placeholders:
            table.add_row("Config Files", "[yellow]WARN[/yellow]", f"Valid YAML, but open placeholders: {'; '.join(placeholders)}")
        else:
            table.add_row("Config Files", "[green]PASS[/green]", "All YAML files valid and populated")
    except Exception as e:
        table.add_row("Config Files", "[red]FAIL[/red]", str(e))
        critical_failures += 1

    # 2. Database Check
    try:
        db.init_db()
        table.add_row("SQLite Database", "[green]PASS[/green]", f"Ready at {db.db_path.name}")
    except Exception as e:
        table.add_row("SQLite Database", "[red]FAIL[/red]", str(e))
        critical_failures += 1

    # 3. LLM Provider Check
    if not settings.llm_api_key:
        table.add_row(f"LLM ({settings.llm_provider})", "[yellow]MISSING KEY[/yellow]", f"Set LLM_API_KEY in .env for {settings.llm_provider}")
    else:
        try:
            llm = LLMClient(settings=settings)
            # Fast ping or verification
            table.add_row(f"LLM ({settings.llm_provider})", "[green]PASS[/green]", f"Model: {settings.llm_model} (API key configured)")
        except Exception as e:
            table.add_row(f"LLM ({settings.llm_provider})", "[red]FAIL[/red]", str(e))

    # 4. Exa Search (Primary Discovery Provider)
    if settings.exa_api_key:
        try:
            exa = ExaClient(settings=settings)
            table.add_row("Exa Search (Primary)", "[green]PASS[/green]", "API Key configured (fast company search)")
        except Exception as e:
            table.add_row("Exa Search (Primary)", "[yellow]WARN[/yellow]", f"Check failed: {e}")
    else:
        table.add_row("Exa Search (Primary)", "[dim]OPTIONAL / SKIPPED[/dim]", "No EXA_API_KEY. Will use Seed CSV fallback.")

    # 5. Yutori Discovery (Optional)
    if settings.yutori_api_key:
        try:
            yutori = YutoriClient(settings=settings)
            yutori.check_usage()
            table.add_row("Yutori Discovery (Optional)", "[green]PASS[/green]", "API reachable & authenticated")
        except Exception as e:
            table.add_row("Yutori Discovery (Optional)", "[yellow]WARN[/yellow]", f"Check failed: {e}")
    else:
        table.add_row("Yutori Discovery (Optional)", "[dim]OPTIONAL / SKIPPED[/dim]", "No YUTORI_API_KEY. (Optional provider)")

    # 6. Hunter Contact (Optional)
    if settings.hunter_api_key:
        try:
            hunter = HunterClient(settings=settings)
            acct = hunter.check_account()
            plan = acct.get("data", {}).get("plan_name", "Free")
            table.add_row("Hunter Contact (Optional)", "[green]PASS[/green]", f"Authenticated (Plan: {plan})")
        except Exception as e:
            table.add_row("Hunter Contact (Optional)", "[yellow]WARN[/yellow]", f"Check failed: {e}")
    else:
        table.add_row("Hunter Contact (Optional)", "[dim]OPTIONAL / SKIPPED[/dim]", "No HUNTER_API_KEY. Using site mailto & role inbox fallback.")

    # 7. Mailer Check
    if settings.mail_provider == "gmail":
        try:
            mailer = GmailSMTPMailer(settings=settings)
            mailer.check_connection()
            table.add_row("Email (Gmail SMTP)", "[green]PASS[/green]", f"Connected as {settings.smtp_user}")
        except Exception as e:
            table.add_row("Email (Gmail SMTP)", "[red]FAIL[/red]", f"SMTP login failed: {e}")
            critical_failures += 1
    elif settings.mail_provider == "resend":
        if settings.resend_api_key:
            table.add_row("Email (Resend)", "[green]PASS[/green]", "API Key configured")
        else:
            table.add_row("Email (Resend)", "[red]FAIL[/red]", "Missing RESEND_API_KEY")
            critical_failures += 1
    else:
        table.add_row("Email (DryRun)", "[green]PASS[/green]", "Dry-run mailer active (emails saved to runs/)")

    # 8. Safe Mode Setting
    if settings.safe_mode:
        table.add_row("Safe Mode", "[green]ENABLED[/green]", f"Live sends blocked. Test recipient: {settings.test_recipient or 'test inbox'}")
    else:
        table.add_row("Safe Mode", "[bold yellow]DISABLED (LIVE)[/bold yellow]", "Caution: Emails will be dispatched to real prospects!")

    # 9. Google Sheets Check
    if not settings.google_sheet_id:
        table.add_row("Google Sheets", "[dim]OPTIONAL / SKIPPED[/dim]", "No GOOGLE_SHEET_ID set. Local CSV logging fallback active.")
    else:
        try:
            sheets = SheetsMirror(settings=settings)
            sheets.check_connection()
            table.add_row("Google Sheets", "[green]PASS[/green]", "Sheet connected via Service Account")
        except Exception as e:
            table.add_row("Google Sheets", "[yellow]WARN[/yellow]", f"Sheet connection error: {e}. CSV fallback active.")

    console.print(table)
    if critical_failures > 0:
        console.print(f"[bold red]Doctor reported {critical_failures} critical failure(s). Fix issues before running.[/bold red]")
        sys.exit(1)
    else:
        console.print("[bold green]System is ready to operate.[/bold green]")


@app.command()
def discover(
    provider: str = typer.Option("auto", "--provider", "--source", help="Provider: 'auto', 'exa', 'yutori', or 'seed'"),
    n: int = typer.Option(15, "--n", help="Number of prospects to discover"),
    with_control: bool = typer.Option(False, "--with-control", help="Include 1 known poor-fit company for rejection testing"),
    resume: Optional[str] = typer.Option(None, "--resume", help="Resume existing Yutori research task ID"),
    fresh: bool = typer.Option(False, "--fresh", "--no-cache", help="Bypass disk cache to discover brand new live prospects"),
):
    """Discover new prospects and add them to the candidate pool."""
    db = Database()
    settings = load_env_settings()
    discovery_step = DiscoveryStep(db=db, settings=settings)

    console.print(f"[bold cyan]Starting discovery via provider '{provider}' (target: {n})...[/bold cyan]")
    candidates = discovery_step.run(source=provider, limit=n, with_control=with_control, resume_task_id=resume, fresh=fresh)

    table = Table(title=f"Discovered Prospects Added ({len(candidates)})", show_lines=True)
    table.add_column("Company", style="bold")
    table.add_column("Domain")
    table.add_column("Industry")
    table.add_column("Location")
    table.add_column("Source")

    for c in candidates:
        table.add_row(c.company_name, c.domain, c.industry or "N/A", c.location or "N/A", c.source)

    console.print(table)


@app.command()
def pool():
    """List all prospects in the database and their pipeline states."""
    db = Database()
    prospects = db.list_prospects()

    if not prospects:
        console.print("[yellow]Prospect pool is empty. Run 'agent discover' first.[/yellow]")
        return

    table = Table(title=f"Prospect Pool ({len(prospects)})", show_lines=True)
    table.add_column("Domain", style="bold cyan")
    table.add_column("Company")
    table.add_column("State", style="bold")
    table.add_column("Source")
    table.add_column("Created")

    for p in prospects:
        state_color = "green" if p["state"] in ("SENT", "LOGGED", "QUALIFIED") else "red" if p["state"] in ("REJECTED", "BLOCKED") else "yellow"
        table.add_row(
            p["domain"],
            p["company_name"],
            f"[{state_color}]{p['state']}[/{state_color}]",
            p["source"],
            p["created_at"][:19],
        )

    console.print(table)


@app.command()
def run(
    limit: int = typer.Option(3, "--limit", help="Number of prospects to process"),
    max_send: int = typer.Option(1, "--max-send", help="Maximum emails to send in this run"),
    domain: Optional[str] = typer.Option(None, "--domain", help="Process a specific domain"),
    approve: bool = typer.Option(False, "--approve", help="Prompt for manual review before sending"),
    live: bool = typer.Option(False, "--live", help="Execute live send to recipient"),
    replay: bool = typer.Option(False, "--replay", help="Offline replay mode (no external network calls)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass disk cache for fresh network calls"),
):
    """Run the complete outbound pipeline for pending prospects."""
    settings = load_env_settings()
    db = Database()
    cache = DiskCache(enabled=not no_cache, replay=replay)
    budget = BudgetTracker(sends_max=max_send)
    pipeline = OutboundPipeline(db=db, settings=settings, cache=cache, budget=budget)

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    console.print(f"[bold magenta]> Starting Pipeline Run {run_id}[/bold magenta]")

    if domain:
        domains_to_process = [domain.strip().lower()]
    else:
        # Pick next DISCOVERED prospects
        pending = db.list_prospects(state="DISCOVERED", limit=limit)
        if not pending:
            console.print("[yellow]No DISCOVERED prospects in pool. Run 'agent discover' first.[/yellow]")
            return
        domains_to_process = [p["domain"] for p in pending]

    results = []
    for d in domains_to_process:
        if budget.sends_used >= max_send:
            console.print(f"[yellow]Reached max sends limit ({max_send}). Halting run.[/yellow]")
            break
        res = pipeline.process_prospect(domain=d, run_id=run_id, approve=approve, live=live)
        results.append(res)

    console.print(f"\n[bold green]Pipeline Run {run_id} completed. Processed: {len(results)} prospect(s).[/bold green]")


@app.command()
def show(domain: str):
    """Show detailed audit trail for a specific prospect."""
    db = Database()
    norm = domain.strip().lower()
    prospect = db.get_prospect(norm)
    if not prospect:
        console.print(f"[red]Prospect '{norm}' not found in database.[/red]")
        return

    enrichment = db.get_enrichment(norm)
    qual = db.get_qualification(norm)
    contact = db.get_contact(norm)
    email = db.get_email(norm)
    send = db.get_send(norm)

    console.print(Panel(f"[bold cyan]Company:[/bold cyan] {prospect['company_name']}\n"
                        f"[bold cyan]Domain:[/bold cyan] {norm}\n"
                        f"[bold cyan]State:[/bold cyan] {prospect['state']}\n"
                        f"[bold cyan]Source:[/bold cyan] {prospect['source']}", title=f"Audit: {norm}"))

    if qual:
        console.print(Panel(f"Fit Score: {qual['final_score']}/100 | Fit: {qual['fit']}\n"
                            f"Primary Service: {qual['primary_service']}\n"
                            f"Disqualifier: {qual.get('disqualifier')}\n"
                            f"Subscores: {qual['subscores']}\n"
                            f"Pain Points: {qual['pain_points']}", title="Qualification"))

    if contact:
        console.print(Panel(f"Name: {contact.get('first_name')} {contact.get('last_name')}\n"
                            f"Email: {contact.get('email')} ({contact.get('verification')})\n"
                            f"Title: {contact.get('position')} | Source: {contact.get('source')}", title="Contact"))

    if email:
        console.print(Panel(f"Template: {email['template_id']}\n"
                            f"Subject: {email['subject']}\n\n"
                            f"{email['body_text']}", title="Composed Email"))

    if send:
        console.print(Panel(f"Mode: {send['mode']}\n"
                            f"Status: {send['status']}\n"
                            f"Intended: {send['intended_to']} -> Actual: {send['actual_to']}\n"
                            f"Message-ID: {send.get('message_id')}\n"
                            f"Provider Response: {send.get('provider_response')}", title="Send Dispatch"))


@app.command()
def report():
    """Print run statistics and funnel conversion report."""
    db = Database()
    stats = db.get_run_stats()

    table = Table(title="Upthrust Outbound Pipeline Report", show_lines=True)
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="bold cyan")

    table.add_row("Total Prospects in Pool", str(stats["total_prospects"]))
    table.add_row("Total Outbound Sent", str(stats["total_sent"]))

    for state, cnt in stats["by_state"].items():
        table.add_row(f"State: {state}", str(cnt))

    for provider, cost in stats["costs"].items():
        table.add_row(f"Cost ({provider})", f"${cost:.3f}")

    console.print(table)


@suppress_app.command("add")
def suppress_add(value: str, reason: str = typer.Option("manual", "--reason")):
    """Add a domain or email to the suppression list."""
    db = Database()
    db.add_suppression(value, reason=reason)
    console.print(f"[green]Added '{value}' to suppression list (reason: {reason}).[/green]")


@cache_app.command("clear")
def cache_clear():
    """Clear all cached API responses in data/cache."""
    cache = DiskCache()
    deleted = cache.clear()
    console.print(f"[bold green]Cleared {deleted} cached file(s) from {cache.cache_dir}.[/bold green]")


@cache_app.command("status")
def cache_status():
    """Show cache status and number of cached entries."""
    cache = DiskCache()
    total = cache.count()
    console.print(f"[cyan]Cache directory: {cache.cache_dir}[/cyan]")
    console.print(f"[bold green]{total} cached file(s) on disk.[/bold green]")


@app.command()
def reset(
    include_suppression: bool = typer.Option(False, "--include-suppression", help="Also clear the suppression list"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt"),
):
    """Clear all prospects, runs, and pipeline data from the database."""
    if not yes:
        confirm = typer.confirm("Are you sure you want to clear all prospects and run history from the database?")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]")
            return
    db = Database()
    db.clear_all(include_suppression=include_suppression)
    console.print("[bold green]Database cleared. The prospect pool is now fresh and empty.[/bold green]")


@app.command()
def dashboard(
    port: int = typer.Option(8000, "--port", help="Port to run web dashboard on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface"),
):
    """Launch the Upthrust Outbound Interactive Web Dashboard."""
    import uvicorn
    from agent.dashboard.server import create_dashboard_app
    console.print(f"[bold green]Starting Upthrust Outbound Dashboard at http://{host}:{port}[/bold green]")
    app_instance = create_dashboard_app()
    uvicorn.run(app_instance, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
