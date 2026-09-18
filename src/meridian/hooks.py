"""Project hooks.

Two things happen here that are worth knowing about:

  * the catalogue is assembled from catalog.yml plus catalog_scoring.yml,
    because the scoring run is scheduled separately on the client's Control-M;
  * every run writes a one line audit record to logs/run_audit.csv. The
    client's model risk team asked for this after the wave-1 review and it is
    a condition of the asset staying in production.
"""
import csv
import datetime as dt
import logging
import os

from kedro.config import TemplatedConfigLoader
from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog
from kedro.versioning import Journal

logger = logging.getLogger(__name__)

AUDIT_PATH = os.path.join("logs", "run_audit.csv")
AUDIT_HEADER = ["run_started", "run_finished", "pipeline", "nodes", "model_version", "user"]


class ProjectHooks:
    @hook_impl
    def register_config_loader(self, conf_paths, env, extra_params):
        return TemplatedConfigLoader(
            conf_paths,
            globals_pattern="*globals.yml",
            globals_dict=extra_params or {},
        )

    @hook_impl
    def register_catalog(
        self, catalog, credentials, load_versions, save_version, journal
    ):
        return DataCatalog.from_config(
            catalog, credentials, load_versions, save_version, journal
        )

    @hook_impl
    def before_pipeline_run(self, run_params, pipeline, catalog):
        self._started = dt.datetime.now()
        self._pipeline_name = run_params.get("pipeline_name") or "__default__"
        logger.info(
            "Starting %s with %d nodes (extract vintage %s)",
            self._pipeline_name,
            len(pipeline.nodes),
            run_params.get("extra_params", {}).get("extract_vintage", "unknown"),
        )
        self._node_count = len(pipeline.nodes)

    @hook_impl
    def after_pipeline_run(self, run_params, run_result, pipeline, catalog):
        self._write_audit_row(
            pipeline_name=run_params.get("pipeline_name") or "__default__",
            nodes=len(pipeline.nodes),
        )

    @hook_impl
    def on_pipeline_error(self, error, run_params, pipeline, catalog):
        logger.error(
            "Pipeline %s failed: %s", run_params.get("pipeline_name"), error
        )
        self._write_audit_row(
            pipeline_name=(run_params.get("pipeline_name") or "__default__") + " [FAILED]",
            nodes=len(pipeline.nodes),
        )

    @hook_impl
    def before_node_run(self, node, catalog, inputs, is_async, run_id):
        logger.debug("node %s <- %s", node.name, sorted(inputs))

    def _write_audit_row(self, pipeline_name, nodes):
        started = getattr(self, "_started", dt.datetime.now())
        directory = os.path.dirname(AUDIT_PATH)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        write_header = not os.path.isfile(AUDIT_PATH)
        with open(AUDIT_PATH, "a", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            if write_header:
                writer.writerow(AUDIT_HEADER)
            writer.writerow(
                [
                    started.strftime("%d/%m/%Y %H:%M:%S"),
                    dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    pipeline_name,
                    nodes,
                    "meridian-2.4.1",
                    os.environ.get("USER") or os.environ.get("USERNAME") or "unknown",
                ]
            )


project_hooks = ProjectHooks()


class DataQualityHooks:
    """Row count guard rails.

    The extract has arrived truncated twice (2022-06-17 and 2023-02-10) and
    the pipeline happily retrained on a third of the data both times.
    """

    MIN_SALES_ROWS = 5000

    @hook_impl
    def after_dataset_loaded(self, dataset_name, data, node):
        if not dataset_name.startswith("sales_weekly"):
            return
        rows = len(data)
        if rows < self.MIN_SALES_ROWS:
            logger.warning(
                "%s only has %d rows, expected at least %d - check the SFTP drop",
                dataset_name,
                rows,
                self.MIN_SALES_ROWS,
            )


data_quality_hooks = DataQualityHooks()
