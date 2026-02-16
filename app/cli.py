"""CLI utilities."""

import click
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.api.auth import get_password_hash
from app.worker.tasks import daily_monitoring_job, generate_daily_report
from datetime import date
import bcrypt


@click.group()
def cli():
    """Director Media Monitoring CLI."""
    pass


@cli.command()
@click.option("--username", required=True, prompt=True)
@click.option("--password", required=True, prompt=True, hide_input=True)
@click.option("--email", required=True, prompt=True)
@click.option("--role", default="admin", type=click.Choice(["admin", "md"]))
def create_admin(username: str, password: str, email: str, role: str):
    """Create admin user."""
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            click.echo(f"User {username} already exists")
            return

        # Use bcrypt directly for compatibility
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=UserRole.ADMIN if role == "admin" else UserRole.MD,
            is_active=True,
        )
        db.add(user)
        db.commit()
        click.echo(f"User {username} created successfully")
    finally:
        db.close()


@cli.command()
def run_scan():
    """Manually trigger monitoring scan."""
    click.echo("Triggering monitoring scan...")
    daily_monitoring_job.delay()
    click.echo("Scan queued. Check worker logs for progress.")


@cli.command()
@click.option("--date", default=None, help="Report date (YYYY-MM-DD)")
def generate_report(report_date: str):
    """Manually generate report."""
    target_date = date.fromisoformat(report_date) if report_date else date.today()
    click.echo(f"Generating report for {target_date}...")
    generate_daily_report.delay(target_date)
    click.echo("Report generation queued. Check worker logs for progress.")


if __name__ == "__main__":
    cli()

