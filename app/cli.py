# -*- coding: utf-8 -*-
"""Comandos CLI de Bitácora."""
import click
from flask.cli import AppGroup


marketing_cli = AppGroup('marketing')


@marketing_cli.command('run-due-jobs')
def run_due_jobs_command():
    """Ejecuta CronJobs vencidos de marketing."""
    from .services.marketing_service import run_due_marketing_jobs

    processed = run_due_marketing_jobs()
    click.echo(f'CronJobs procesados: {len(processed)}')
    for item in processed:
        click.echo(f"- #{item.get('id')}: {item.get('status')}")


def register_cli(app):
    """Registra grupos CLI en la aplicación."""
    app.cli.add_command(marketing_cli)
