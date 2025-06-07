#!/usr/bin/env python3
try:
    from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent
    print("Import OracleBaseAgent réussi !")
except Exception as e:
    print(f"Erreur import OracleBaseAgent: {e}")
    import traceback
    traceback.print_exc()