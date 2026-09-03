# Decision Trace

The trace layer adapts existing pipeline and decision-engine dictionaries into
a deterministic graph. It records references and metadata, not image bytes.
Node IDs are content-derived and reproducible for identical inputs. Missing
optional metadata produces warnings rather than fabricated values.
