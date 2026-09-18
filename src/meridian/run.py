"""Project context and package entry point.

Still on the ProjectContext style rather than the session API: the client's
Airflow plugin (nfk-kedro-operator 0.3.2) imports ProjectContext directly, so
the two have to move together. Ticket NFK-PLT-311 has been open since
sprint 12. -- JL
"""
import logging
from pathlib import Path

from kedro.config import TemplatedConfigLoader
from kedro.framework.context import KedroContext
from kedro.framework.session import KedroSession
from kedro.pipeline import Pipeline

from meridian.pipeline_registry import register_pipelines

logger = logging.getLogger(__name__)

PROJECT_NAME = "Meridian - Nordfalk demand forecasting"
PROJECT_VERSION = "0.17.5"
PACKAGE_NAME = "meridian"


class ProjectContext(KedroContext):
    """Nordfalk deployment context."""

    project_name = PROJECT_NAME
    project_version = PROJECT_VERSION
    package_name = PACKAGE_NAME

    def _get_pipelines(self):
        return register_pipelines()

    def _create_config_loader(self, conf_paths):
        return TemplatedConfigLoader(
            conf_paths,
            globals_pattern="*globals.yml",
            globals_dict={
                "client_code": "NFK",
                "raw_root": "data/01_raw",
                "mart_root": "data/01_raw/marts",
            },
        )

    def _get_pipeline(self, name=None):
        pipelines = self._get_pipelines()
        if name is None:
            return pipelines["__default__"]
        if name not in pipelines:
            raise ValueError(
                "Unknown pipeline %r. Available: %s" % (name, sorted(pipelines))
            )
        return pipelines[name]

    def run_pipeline(self, name=None, tags=None, node_names=None):
        pipeline = self._get_pipeline(name)
        if tags:
            pipeline = pipeline.only_nodes_with_tags(*tags)
        if node_names:
            pipeline = pipeline.only_nodes(*node_names)
        if not isinstance(pipeline, Pipeline) or not pipeline.nodes:
            raise ValueError("Nothing to run for pipeline %r" % name)
        return self.run(pipeline_name=name, tags=tags, node_names=node_names)


def run_package():
    """Entry point installed as the `meridian` console script."""
    project_path = Path(__file__).resolve().parents[2]
    with KedroSession.create(PACKAGE_NAME, project_path) as session:
        session.run()


if __name__ == "__main__":
    run_package()
