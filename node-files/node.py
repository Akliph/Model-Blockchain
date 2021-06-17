"""
Node.py is meant to handle most of the internal node logic. Methods for validating incoming transactions
and requests are defined here, and use server.py as an entry point. Dynamic information like calculated
block difficulty, median block time, block difficulty, UTXO(maybe), MEMPOOL, etc. are all calculated and stored
in a node config file here.

**NOTE
Various user-defined parameters are available via vargs to allow the ledger protocol to change based on
votes cast with computational power contributed to the system. "If you like the way a node does things,
you send your blocks to it for validation, therefore endorsing its protocol."
"""

class Node:
    pass


