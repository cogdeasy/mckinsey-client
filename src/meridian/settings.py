"""Project settings (kedro >= 0.17)."""
from meridian.hooks import data_quality_hooks, project_hooks

HOOKS = (project_hooks, data_quality_hooks)

# Installed plugin hooks we do not want on the engagement laptops.
DISABLE_HOOKS_FOR_PLUGINS = ("kedro-telemetry",)

CONF_ROOT = "conf"
