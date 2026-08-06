# SPDX-License-Identifier: AGPL-3.0-or-later
"""Typed error taxonomy for ConfigStream domain and operational boundaries."""

from __future__ import annotations


class ConfigStreamError(Exception):
    """Base class for expected ConfigStream failures."""


class AcquisitionError(ConfigStreamError):
    """A source could not be acquired under the configured safety contract."""


class SourcePolicyError(AcquisitionError):
    """A source failed admission, provenance, freshness, or trust policy."""


class ParseError(ConfigStreamError):
    """Fetched content could not be parsed into a supported proxy record."""


class ValidationError(ConfigStreamError):
    """A candidate model or artifact violated a validation contract."""


class TesterInfrastructureError(ConfigStreamError):
    """A tester failed for infrastructure reasons, not proxy behavior."""


class PublicationError(ConfigStreamError):
    """Candidate artifact generation or transactional publication failed."""


class ExternalNotificationError(ConfigStreamError):
    """An optional notification integration failed after core work completed."""
