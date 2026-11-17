"""Audit Factory — website and contactability audits for local businesses.

Deterministic, $0 to run: fetches a business website, checks the things a
prospect can verify on the page itself, scores the result out of 100, and
renders a branded Markdown / HTML / PDF audit.

The audit is the sales engine for the AI Operations Manager: every failed
check maps to a concrete fix that service delivers. No check claims data
the page does not show — anything not verifiable from the page (Google
reviews, call answering, response times by phone) is reported as
"not checked", never invented.
"""

__version__ = "0.1.0"
