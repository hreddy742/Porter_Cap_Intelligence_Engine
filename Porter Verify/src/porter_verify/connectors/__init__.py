"""Source connector layer.

Connectors talk to external data sources behind one swappable contract
(``SourceConnector``). The verify flow never depends on a specific vendor — it
selects a connector from the registry by capability and state coverage.
"""
