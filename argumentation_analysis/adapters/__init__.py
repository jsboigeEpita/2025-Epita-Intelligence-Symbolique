"""
Adapters for external and student project components.

Each adapter wraps code that lives outside the core argumentation_analysis
package and exposes it via standard interfaces (e.g. AbstractFallacyDetector,
which is live) for composability via CapabilityRegistry.

`AbstractAnalysisService` is NOT among them: no adapter implements it
(measured 2026-09-14) — the interface exists but has no implementer, so citing
it here described an integration that never happened.
"""
