"""Orchestration layer: flows that sequence services + connectors into one run.

In the MVP the verify flow runs synchronously inside a request/job. It is written
to be Prefect-wrapped later (each step is already a discrete, retry-safe unit).
"""
