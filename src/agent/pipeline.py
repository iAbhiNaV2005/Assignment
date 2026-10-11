import sys
import time
import uuid
from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)

from agent.budget import BudgetTracker
from agent.cache import DiskCache
from agent.clients.hunter import HunterClient
from agent.clients.mailer import Mailer, get_mailer
from agent.clients.sheets import SheetsMirror
from agent.config import EnvSettings, load_env_settings
from agent.db import Database
from agent.llm import LLMClient
from agent.models import Candidate, ComposedEmail, Contact, SendResult
from agent.steps.compose import ComposeStep
from agent.steps.contact import ContactStep
from agent.steps.enrich import EnrichmentStep
from agent.steps.guardrails import GuardrailsStep
from agent.steps.qualify import QualificationStep
from agent.steps.record import RecordStep
from agent.steps.send import SendStep

console = Console()


class OutboundPipeline:
    def __init__(
        self,
        db: Database | None = None,
        settings: EnvSettings | None = None,
        cache: DiskCache | None = None,
        budget: BudgetTracker | None = None,
        llm: LLMClient | None = None,
        mailer: Mailer | None = None,
    ):
        self.db = db or Database()
        self.settings = settings or load_env_settings()
        self.cache = cache or DiskCache()
        self.budget = budget or BudgetTracker()
        self.llm = llm or LLMClient(settings=self.settings, cache=self.cache)
        self.mailer = mailer or get_mailer(self.settings)

        self.enrich_step = EnrichmentStep(db=self.db)
        self.qualify_step = QualificationStep(db=self.db, llm=self.llm)
        self.contact_step = ContactStep(db=self.db, hunter_client=HunterClient(settings=self.settings, cache=self.cache, budget=self.budget))
        self.compose_step = ComposeStep(db=self.db, llm=self.llm)
        self.guardrails_step = GuardrailsStep(db=self.db, llm=self.llm)
        self.send_step = SendStep(db=self.db, mailer=self.mailer, settings=self.settings, budget=self.budget)
        self.record_step = RecordStep(db=self.db, sheets=SheetsMirror(settings=self.settings))

    def process_prospect(
        self,
        domain: str,
        run_id: str | None = None,
        approve: bool = False,
        live: bool = False,
        approval_callback: Callable[[ComposedEmail, Contact], bool] | None = None,
    ) -> dict[str, Any]:
        """
        Processes one prospect through all pipeline steps:
        ENRICH -> QUALIFY -> CONTACT -> COMPOSE -> GUARDRAILS -> SEND -> RECORD
        """
        run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
        norm_domain = domain.strip().lower()
        start_time = time.time()

        console.print(f"\n[bold cyan]─── Processing Prospect: {norm_domain} ───[/bold cyan]")

        # Step 2: ENRICH
        console.print("[dim]Step 2: Fetching website & extracting deterministic signals...[/dim]")
        enrichment = self.enrich_step.run(norm_domain)
        if not enrichment or enrichment.errors:
            console.print(f"[yellow]Enrichment issue: {enrichment.errors if enrichment else 'Unknown'}[/yellow]")
            duration = time.time() - start_time
            self.record_step.record_run_outcome(run_id, norm_domain, duration)
            return {"domain": norm_domain, "status": "ENRICH_FAILED"}

        signal_keys = [s.key for s in enrichment.signals if s.value]
        console.print(f"[green]✓ Enriched:[/green] {len(enrichment.signals)} signals extracted ({', '.join(signal_keys[:4])})")

        # Step 3: QUALIFY
        console.print("[dim]Step 3: Evaluating qualification & fit...[/dim]")
        qual = self.qualify_step.run(norm_domain)
        console.print(
            f"[bold]Fit Score:[/bold] {qual.final_score}/100 | "
            f"[bold]Fit:[/bold] {'[green]YES[/green]' if qual.fit else '[red]NO[/red]'} | "
            f"Focus: {qual.primary_service}"
        )

        if not qual.fit:
            console.print(f"[yellow]Prospect Rejected:[/yellow] {qual.disqualifier or 'Did not meet score threshold'}")
            duration = time.time() - start_time
            self.record_step.record_run_outcome(run_id, norm_domain, duration)
            return {"domain": norm_domain, "status": "REJECTED", "qualification": qual}

        # Step 4: CONTACT
        console.print("[dim]Step 4: Finding & verifying contact...[/dim]")
        contact = self.contact_step.run(norm_domain, safe_mode=not live)
        if not contact:
            console.print("[yellow]No viable contact address found.[/yellow]")
            duration = time.time() - start_time
            self.record_step.record_run_outcome(run_id, norm_domain, duration)
            return {"domain": norm_domain, "status": "NO_CONTACT", "qualification": qual}

        console.print(
            f"[green]✓ Contact:[/green] {contact.first_name or ''} {contact.last_name or ''} "
            f"<{contact.email}> ({contact.verification}, conf: {contact.confidence}%)"
        )

        # Step 5: COMPOSE
        console.print("[dim]Step 5: Selecting template & filling variables...[/dim]")
        email = self.compose_step.run(norm_domain)
        console.print(f"[green]✓ Composed Email:[/green] Template '{email.template_id}' | Subject: '{email.subject}'")

        # Step 6: GUARDRAILS
        console.print("[dim]Step 6: Running deterministic guardrails & claim-check...[/dim]")
        guard_result = self.guardrails_step.run(norm_domain, email)
        if not guard_result.passed:
            console.print(f"[red]✗ Guardrails Failed:[/red] {'; '.join(guard_result.failures)}")
            duration = time.time() - start_time
            self.record_step.record_run_outcome(run_id, norm_domain, duration)
            return {"domain": norm_domain, "status": "BLOCKED", "email": email, "failures": guard_result.failures}

        console.print("[green]✓ Guardrails Passed![/green] 0 leaks, word count verified, evidence claims checked.")

        # Approval Check (--approve)
        if approve:
            console.print(Panel(f"[bold]Subject:[/bold] {email.subject}\n\n{email.body_text}", title="Review Outbound Email"))
            if approval_callback:
                approved = approval_callback(email, contact)
            else:
                answer = console.input("[bold yellow]Approve this email for dispatch? [y/N]: [/bold yellow]")
                approved = answer.strip().lower() in ("y", "yes")

            if not approved:
                console.print("[yellow]Email send skipped by reviewer.[/yellow]")
                self.db.update_state(norm_domain, "SKIPPED")
                duration = time.time() - start_time
                self.record_step.record_run_outcome(run_id, norm_domain, duration)
                return {"domain": norm_domain, "status": "SKIPPED", "email": email}

        # Step 7: SEND
        console.print(f"[dim]Step 7: Dispatching email (mode: {'LIVE' if live else 'SAFE TEST'})...[/dim]")
        send_res = self.send_step.run(norm_domain, email, contact, live=live)
        if send_res.status == "sent":
            console.print(f"[bold green]✓ Email Sent successfully![/bold green] (Message-ID: {send_res.message_id})")
        else:
            console.print(f"[red]✗ Send Failed:[/red] {send_res.error}")

        # Step 8: RECORD
        duration = time.time() - start_time
        metrics = {
            "hunter_credits": self.budget.hunter_credits_used,
            "llm_tokens": self.budget.llm_prompt_tokens + self.budget.llm_completion_tokens,
        }
        self.record_step.record_run_outcome(run_id, norm_domain, duration, extra_metrics=metrics)
        console.print(f"[dim]Step 8: Results recorded in SQLite and CSV mirror ({duration:.1f}s)[/dim]")

        return {
            "domain": norm_domain,
            "status": send_res.status,
            "email": email,
            "contact": contact,
            "send_result": send_res,
            "duration_s": duration,
        }
