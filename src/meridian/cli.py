"""Project specific CLI commands.

`kedro nfk-export` re-runs only the hand-off file from an existing forecast,
which the replenishment team ask for roughly once a fortnight when their
loader falls over.
"""
import click
from kedro.framework.session import KedroSession


@click.group(name="meridian")
def cli():
    """Meridian commands."""


@cli.command(name="nfk-export")
@click.option("--env", "-e", default="local", help="Kedro environment.")
@click.option("--week", default=None, help="Fiscal week label, e.g. 202339.")
def nfk_export(env, week):
    """Rebuild the NFK-IF-014 hand-off file from the stored forecast."""
    extra_params = {"anchor_week": week} if week else {}
    with KedroSession.create("meridian", env=env, extra_params=extra_params) as session:
        session.run(pipeline_name="scoring", node_names=["export_forecast_node"])


@cli.command(name="nfk-vintage")
@click.option("--env", "-e", default="local")
def nfk_vintage(env):
    """Print the extract vintage the catalogue is pointing at."""
    with KedroSession.create("meridian", env=env) as session:
        context = session.load_context()
        click.echo(context.params.get("extract_vintage", "unknown"))
