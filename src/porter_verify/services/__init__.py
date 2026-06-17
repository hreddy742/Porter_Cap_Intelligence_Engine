"""Service layer: all business logic, kept free of HTTP/framework concerns.

Each module owns one responsibility (normalization, evidence, audit, resolution,
scoring, ...) and is unit-testable in isolation.
"""
