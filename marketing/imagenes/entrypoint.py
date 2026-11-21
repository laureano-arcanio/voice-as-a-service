"""Entrypoint de vLLM-Omni con los parches de patches.py aplicados antes de arrancar."""

import sys

import patches  # noqa: F401

from vllm_omni.entrypoints.cli.main import main  # noqa: E402

sys.exit(main())
