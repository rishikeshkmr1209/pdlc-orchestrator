#!/usr/bin/env python3
"""Prompt Scanner — Claude Code UserPromptSubmit Hook

Intercepts every user prompt BEFORE it is dispatched to the LLM and
blocks prompts that accidentally contain credentials, secrets, or PII.

Detects (and blocks by default):
  Provider   — AWS, Azure, GCP, GitHub, GitLab, Bitbucket, Anthropic, OpenAI,
  keys         Stripe, Square, PayPal/Braintree, Slack, SendGrid, Twilio,
               Mailgun, Mailchimp, npm, PyPI, Docker Hub, Heroku, Vercel,
               Netlify, Supabase, Firebase, Hashicorp Vault, Terraform Cloud,
               CircleCI, Datadog, New Relic, Sentry, PagerDuty, LaunchDarkly,
               Shopify, Atlassian/Jira, Cloudflare, DigitalOcean, Linear,
               Algolia, Mapbox, Contentful, Okta, Auth0, Confluent/Kafka.
  Crypto     — PEM private keys, SSH private keys, PGP private key blocks.
  Auth       — JWT tokens, Bearer tokens, Basic Auth in URLs, OAuth tokens.
  DB         — Connection strings with embedded passwords (Postgres, MySQL,
               MongoDB, Redis, MSSQL, MariaDB, CockroachDB, etc.).
  Natural    — "my api key is X", "here is my token: X", "the password is X",
  language     "I set the secret to X", "credentials: X", and 30+ variations
               of conversational credential disclosure.
  Shell/CLI  — export SECRET=X, --api-key=X, curl -u user:pass, docker -e,
               AWS env vars, .env file contents pasted into prompts.
  Config     — Inline YAML/JSON/TOML secrets, URL query param secrets.
  Entropy    — High-entropy strings (>4.5 bits/char) near credential keywords
               as a catch-all for unknown/custom secret formats.
  PII        — Credit card numbers (Luhn-validated), US SSN, ITIN.

Warns (prompt still sent, message shown):
  PII        — Email addresses, US/intl phone numbers, IP addresses
               (reminder: use the project IP library for IP handling).
  Weak creds — Test/staging API keys, hardcoded password/secret assignments
               (both quoted and unquoted), PEM certificates.

Exit codes (Claude Code UserPromptSubmit hook contract):
  0 — clean or warnings only; prompt is dispatched, stdout shown as note
  2 — blocking finding; prompt suppressed, stderr shown as error

Configuration via environment variable:
  PROMPT_SCANNER_MODE=standard   (default) block secrets/CC/SSN, warn PII
  PROMPT_SCANNER_MODE=strict     block everything including warn-level
  PROMPT_SCANNER_MODE=audit      log findings to stderr, never block

Reference pattern sources:
  gitleaks  github.com/gitleaks/gitleaks (config/gitleaks.toml)
  Yelp      github.com/Yelp/detect-secrets
  OWASP     owasp.org/www-community/vulnerabilities/Sensitive_Data_Exposure
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import NamedTuple


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Pattern:
    """A single detection rule."""
    name: str
    regex: str
    severity: str   # "block" | "warn"
    category: str
    redact: int = 8  # characters to reveal before *** in user-facing output
    _compiled: re.Pattern = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(
            self.regex, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

    def search(self, text: str) -> re.Match | None:
        return self._compiled.search(text)


class Finding(NamedTuple):
    name: str
    category: str
    severity: str
    snippet: str  # redacted, safe to display


# ─────────────────────────────────────────────────────────────────────────────
# Shared building blocks for natural-language patterns
# ─────────────────────────────────────────────────────────────────────────────

# Credential keyword alternation — reused across multiple NL patterns.
_CRED_WORDS = (
    r"(?:password|passwd|passphrase|secret|pin[\s_\-]?code|"
    r"api[\s_\-]?keys?|access[\s_\-]?keys?|secret[\s_\-]?keys?|"
    r"auth[\s_\-]?tokens?|access[\s_\-]?tokens?|bearer[\s_\-]?tokens?|"
    r"refresh[\s_\-]?tokens?|session[\s_\-]?tokens?|"
    r"private[\s_\-]?keys?|client[\s_\-]?secrets?|client[\s_\-]?ids?|"
    r"credentials?|tokens?|signing[\s_\-]?keys?|encryption[\s_\-]?keys?|"
    r"master[\s_\-]?keys?|service[\s_\-]?keys?|"
    r"ssh[\s_\-]?keys?|gpg[\s_\-]?keys?|"
    r"webhook[\s_\-]?(?:url|secret)s?|"
    r"connection[\s_\-]?strings?|"
    r"database[\s_\-]?(?:password|url|uri)s?|"
    r"db[\s_\-]?(?:password|url|uri)s?)"
)

# Negative lookahead — words that legitimately follow "is/are" after a
# credential keyword in normal conversation ("the token is expired").
_NL_SAFE_WORDS = (
    r"(?!(?:"
    # State / status words
    r"expired|invalid|missing|required|optional|empty|null|nil|none|"
    r"undefined|blank|absent|"
    # Negation / articles / prepositions
    r"not\b|no\b|the\b|a\b|an\b|in\b|on\b|at\b|to\b|for\b|from\b|"
    r"being\b|about\b|like\b|just\b|only\b|also\b|"
    # Storage / lifecycle verbs
    r"stored|saved|kept|managed|rotated|revoked|refreshed|generated|"
    r"created|deleted|removed|reset|updated|changed|"
    r"injected|loaded|fetched|retrieved|cached|persisted|"
    # Configuration / availability
    r"set\b|configured|available|needed|used|sent|passed|returned|"
    r"provided|defined|specified|supplied|obtained|derived|"
    # Correctness / status
    r"correct|wrong|working|broken|failing|valid|verified|"
    r"active|inactive|enabled|disabled|pending|blocked|"
    r"deprecated|obsolete|stale|outdated|"
    # Encoding / security
    r"base64|encrypted|hashed|encoded|obfuscated|masked|redacted|"
    r"sanitized|scrubbed|filtered|stripped|truncated|hidden|"
    # Descriptive / comparison
    r"too\b|very\b|usually\b|typically\b|always\b|never\b|often\b|"
    r"similar\b|different\b|longer\b|shorter\b|"
    # Technical context
    r"located|found|read\b|written|logged|printed|displayed|shown|"
    r"exposed|leaked|compromised|vulnerable|insecure|secure|safe"
    r")(?:\s|$|[.,;:!?]))"
)

# Placeholder values that should NOT trigger warnings in assignments.
_PLACEHOLDER_WORDS = (
    r"(?:your[_\-]|example|placeholder|changeme|change[._]me|"
    r"todo|xxx|test[_\-]|fake[_\-]?|dummy|sample|demo|mock|"
    r"replace[._]me|fill[._]in|insert|REDACTED|CHANGE[_]ME|"
    r"TBD|fixme|temp[_\-]|tmp[_\-]|\*{2,}|<[^>]+>)"
)


# ─────────────────────────────────────────────────────────────────────────────
# Pattern catalogue
# ─────────────────────────────────────────────────────────────────────────────
#
# Patterns are ordered from most-specific (highest confidence) to broadest.
# Severity "block" suppresses the prompt; "warn" notifies but allows through.
#
# Sources: gitleaks.toml, detect-secrets, manual additions for project context.

PATTERNS: list[Pattern] = [

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 1: Provider-specific keys (highest confidence — unique prefixes)
    # ═══════════════════════════════════════════════════════════════════════════

    # ── AWS ──────────────────────────────────────────────────────────────────
    Pattern(
        name="AWS Access Key ID",
        regex=r"\b((?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z2-7]{16})\b",
        severity="block",
        category="Cloud Credential",
        redact=8,
    ),
    Pattern(
        name="AWS Secret Access Key (contextual)",
        regex=(
            r"(?:aws|amazon).{0,30}"
            r"(?:secret|secret_access_key|secret.key).{0,10}"
            r"[=:\s]+[\"']?([A-Za-z0-9/+=]{40})[\"']?"
        ),
        severity="block",
        category="Cloud Credential",
        redact=8,
    ),
    Pattern(
        name="AWS MWS Auth Token",
        regex=r"\bamzn\.mws\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        severity="block",
        category="Cloud Credential",
        redact=12,
    ),

    # ── Azure ───────────────────────────────────────────────────────────────
    Pattern(
        name="Azure Storage Account Key",
        regex=r"(?i)accountkey=[a-zA-Z0-9+/]{43}={0,2}",
        severity="block",
        category="Cloud Credential",
        redact=14,
    ),
    Pattern(
        name="Azure SAS Token",
        regex=r"(?i)sig=[a-zA-Z0-9%+/]{40,}(?:&|$)",
        severity="block",
        category="Cloud Credential",
        redact=8,
    ),
    Pattern(
        name="Azure AD Client Secret",
        regex=r"\b[a-zA-Z0-9~._\-]{34}(?:\.[a-zA-Z0-9~._\-]{34})?\b",
        severity="warn",  # broad pattern — warn only with context
        category="Cloud Credential",
        redact=8,
    ),

    # ── Google / GCP ─────────────────────────────────────────────────────────
    Pattern(
        name="Google API Key",
        regex=r"\bAIza[0-9A-Za-z\-_]{35}\b",
        severity="block",
        category="Cloud Credential",
        redact=8,
    ),
    Pattern(
        name="Google OAuth Client Secret",
        regex=r"\bGOCSPS[a-zA-Z0-9\-_]{28}\b",
        severity="block",
        category="Cloud Credential",
        redact=8,
    ),
    Pattern(
        name="Google OAuth Access Token",
        regex=r"\bya29\.[0-9A-Za-z\-_]+\b",
        severity="block",
        category="Cloud Credential",
        redact=8,
    ),
    Pattern(
        name="Firebase Cloud Messaging Server Key",
        regex=r"\bAAAA[a-zA-Z0-9_\-]{7}:[a-zA-Z0-9_\-]{140}\b",
        severity="block",
        category="Cloud Credential",
        redact=12,
    ),

    # ── GitHub ──────────────────────────────────────────────────────────────
    Pattern(
        name="GitHub Classic PAT",
        regex=r"\bghp_[0-9a-zA-Z]{36}\b",
        severity="block",
        category="VCS Token",
        redact=8,
    ),
    Pattern(
        name="GitHub Fine-Grained PAT",
        regex=r"\bgithub_pat_[0-9a-zA-Z_]{82}\b",
        severity="block",
        category="VCS Token",
        redact=12,
    ),
    Pattern(
        name="GitHub OAuth / Actions Token",
        regex=r"\bgh[oseiru]_[0-9a-zA-Z]{36,255}\b",
        severity="block",
        category="VCS Token",
        redact=8,
    ),
    Pattern(
        name="GitHub App Installation Token",
        regex=r"\bghs_[0-9a-zA-Z]{36}\b",
        severity="block",
        category="VCS Token",
        redact=8,
    ),

    # ── GitLab ──────────────────────────────────────────────────────────────
    Pattern(
        name="GitLab Personal Access Token",
        regex=r"\bglpat-[0-9a-zA-Z\-_]{20,}\b",
        severity="block",
        category="VCS Token",
        redact=10,
    ),
    Pattern(
        name="GitLab Pipeline / Runner / CI Token",
        regex=r"\bglrt-[0-9a-zA-Z\-_]{20,}\b",
        severity="block",
        category="VCS Token",
        redact=10,
    ),

    # ── Bitbucket ───────────────────────────────────────────────────────────
    Pattern(
        name="Bitbucket App Password",
        regex=r"\bATBB[a-zA-Z0-9]{32}\b",
        severity="block",
        category="VCS Token",
        redact=8,
    ),

    # ── Atlassian / Jira ────────────────────────────────────
    Pattern(
        name="Atlassian API Token",
        regex=r"\bATATT[a-zA-Z0-9\-_]{50,}\b",
        severity="block",
        category="API Key",
        redact=10,
    ),

    # ── AI / ML platform keys ──────────────────────────────────────────────
    Pattern(
        name="Anthropic API Key",
        regex=r"\bsk-ant-(?:api0[23]-)?[a-zA-Z0-9\-_]{90,}\b",
        severity="block",
        category="API Key",
        redact=10,
    ),
    Pattern(
        name="OpenAI API Key",
        regex=r"\bsk-(?:proj-)?[a-zA-Z0-9\-_]{20,}\b",
        severity="block",
        category="API Key",
        redact=8,
    ),
    Pattern(
        name="Hugging Face Token",
        regex=r"\bhf_[a-zA-Z0-9]{34}\b",
        severity="block",
        category="API Key",
        redact=6,
    ),
    Pattern(
        name="Replicate API Token",
        regex=r"\br8_[a-zA-Z0-9]{38}\b",
        severity="block",
        category="API Key",
        redact=6,
    ),

    # ── Payment / Fintech ──────────────────────────────────────────────────
    Pattern(
        name="Stripe Live Secret Key",
        regex=r"\b(?:sk|rk|pk)_live_[0-9a-zA-Z]{10,99}\b",
        severity="block",
        category="Payment Credential",
        redact=10,
    ),
    Pattern(
        name="Stripe Test Key",
        regex=r"\b(?:sk|rk|pk)_test_[0-9a-zA-Z]{10,99}\b",
        severity="warn",
        category="Payment Credential",
        redact=10,
    ),
    Pattern(
        name="Square Access Token",
        regex=r"\bEAAAE[0-9a-zA-Z\-_=]{60,}\b",
        severity="block",
        category="Payment Credential",
        redact=8,
    ),
    Pattern(
        name="PayPal / Braintree Access Token",
        regex=r"\baccess_token\$(?:production|sandbox)\$[0-9a-z]{16}\$[0-9a-f]{32}\b",
        severity="block",
        category="Payment Credential",
        redact=22,
    ),
    Pattern(
        name="Adyen API Key",
        regex=r"\bAQE[a-z]+-[a-zA-Z0-9]{10,}\b",
        severity="block",
        category="Payment Credential",
        redact=8,
    ),

    # ── Messaging / Comms ──────────────────────────────────────────────────
    Pattern(
        name="Slack Bot / App / User Token",
        regex=r"\bxox[baprs]-[0-9]{8,13}(?:-[0-9]{8,13})?-[a-zA-Z0-9]{24,}\b",
        severity="block",
        category="API Key",
        redact=12,
    ),
    Pattern(
        name="Slack Incoming Webhook URL",
        regex=r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]{8,}/B[a-zA-Z0-9_]{8,}/[a-zA-Z0-9_]{24,}",
        severity="block",
        category="Webhook URL",
        redact=46,
    ),
    Pattern(
        name="Discord Bot Token",
        regex=r"\b[MN][a-zA-Z0-9]{23,28}\.[a-zA-Z0-9\-_]{6}\.[a-zA-Z0-9\-_]{27,}\b",
        severity="block",
        category="API Key",
        redact=10,
    ),
    Pattern(
        name="Discord Webhook URL",
        regex=r"https://discord(?:app)?\.com/api/webhooks/[0-9]{17,19}/[a-zA-Z0-9\-_]{60,68}",
        severity="block",
        category="Webhook URL",
        redact=50,
    ),
    Pattern(
        name="Telegram Bot Token",
        regex=r"\b[0-9]{8,10}:[a-zA-Z0-9_\-]{35}\b",
        severity="block",
        category="API Key",
        redact=10,
    ),
    Pattern(
        name="SendGrid API Key",
        regex=r"\bSG\.[a-zA-Z0-9]{22}\.[a-zA-Z0-9\-_]{43}\b",
        severity="block",
        category="API Key",
        redact=6,
    ),
    Pattern(
        name="Twilio Auth Token (contextual)",
        regex=r"(?:twilio|TWILIO).{0,40}[\"']([a-fA-F0-9]{32})[\"']",
        severity="block",
        category="API Key",
        redact=8,
    ),
    Pattern(
        name="Twilio API Key",
        regex=r"\bSK[0-9a-fA-F]{32}\b",
        severity="block",
        category="API Key",
        redact=6,
    ),
    Pattern(
        name="Mailgun API Key",
        regex=r"\bkey-[0-9a-zA-Z]{32}\b",
        severity="block",
        category="API Key",
        redact=8,
    ),
    Pattern(
        name="Mailchimp API Key",
        regex=r"\b[0-9a-f]{32}-us[0-9]{1,2}\b",
        severity="block",
        category="API Key",
        redact=8,
    ),
    Pattern(
        name="Postmark Server Token",
        regex=r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        severity="warn",  # UUID-like, needs context
        category="API Key",
        redact=8,
    ),

    # ── Package registry ───────────────────────────────────────────────────
    Pattern(
        name="npm Access Token",
        regex=r"\bnpm_[A-Za-z0-9]{36}\b",
        severity="block",
        category="Package Registry Token",
        redact=8,
    ),
    Pattern(
        name="PyPI API Token",
        regex=r"\bpypi-[A-Za-z0-9_\-]{50,}\b",
        severity="block",
        category="Package Registry Token",
        redact=10,
    ),
    Pattern(
        name="Docker Hub Personal Access Token",
        regex=r"\bdckr_pat_[A-Za-z0-9_\-]{27}\b",
        severity="block",
        category="Package Registry Token",
        redact=10,
    ),
    Pattern(
        name="NuGet API Key",
        regex=r"\boy2[a-zA-Z0-9]{43}\b",
        severity="block",
        category="Package Registry Token",
        redact=8,
    ),
    Pattern(
        name="RubyGems API Key",
        regex=r"\brubygems_[0-9a-f]{48}\b",
        severity="block",
        category="Package Registry Token",
        redact=12,
    ),

    # ── CI/CD platforms ────────────────────────────────────────────────────
    Pattern(
        name="CircleCI Personal API Token",
        regex=r"\b[0-9a-f]{40}\b",
        severity="warn",  # 40 hex chars is broad — only warn
        category="CI/CD Token",
        redact=8,
    ),
    Pattern(
        name="Travis CI Token",
        regex=r"(?:travis|TRAVIS).{0,20}[\"']([a-zA-Z0-9]{22})[\"']",
        severity="block",
        category="CI/CD Token",
        redact=8,
    ),

    # ── Hosting / PaaS ─────────────────────────────────────────────────────
    Pattern(
        name="Heroku API Key",
        regex=r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        severity="warn",  # UUID — too broad for block
        category="PaaS Credential",
        redact=8,
    ),
    Pattern(
        name="Vercel Token",
        regex=r"\b(?:vercel_|vc_prod_|vc_test_)[a-zA-Z0-9]{24,}\b",
        severity="block",
        category="PaaS Credential",
        redact=12,
    ),
    Pattern(
        name="Netlify Personal Access Token",
        regex=r"\bnfp_[a-zA-Z0-9]{40,}\b",
        severity="block",
        category="PaaS Credential",
        redact=8,
    ),
    Pattern(
        name="Supabase Service Role Key",
        regex=r"\bsbp_[a-f0-9]{40}\b",
        severity="block",
        category="PaaS Credential",
        redact=8,
    ),
    Pattern(
        name="Render API Key",
        regex=r"\brnd_[a-zA-Z0-9]{32,}\b",
        severity="block",
        category="PaaS Credential",
        redact=8,
    ),
    Pattern(
        name="Fly.io Token",
        regex=r"\bFlyV1\s+fm[12]_[a-zA-Z0-9_\-]{43,}\b",
        severity="block",
        category="PaaS Credential",
        redact=10,
    ),

    # ── Infrastructure / Secrets Managers ──────────────────────────────────
    Pattern(
        name="Hashicorp Vault Token",
        regex=r"\b(?:hvs\.[a-zA-Z0-9_\-]{24,}|s\.[a-zA-Z0-9]{24})\b",
        severity="block",
        category="Infrastructure Secret",
        redact=8,
    ),
    Pattern(
        name="Terraform Cloud / Enterprise Token",
        regex=r"\b(?:atlasv1-)[a-zA-Z0-9\-_]{60,}\b",
        severity="block",
        category="Infrastructure Secret",
        redact=12,
    ),
    Pattern(
        name="Doppler Token",
        regex=r"\bdp\.(?:ct|st|sa|scim)\.[a-zA-Z0-9]{40,}\b",
        severity="block",
        category="Infrastructure Secret",
        redact=8,
    ),

    # ── Observability ────────────────────
    Pattern(
        name="Datadog API Key",
        regex=r"(?:datadog|DD_API_KEY|dd_api_key).{0,20}[=:\s]+[\"']?([a-f0-9]{32})[\"']?",
        severity="block",
        category="Observability Key",
        redact=10,
    ),
    Pattern(
        name="Datadog Application Key",
        regex=r"(?:DD_APP_KEY|dd_app_key).{0,10}[=:\s]+[\"']?([a-f0-9]{40})[\"']?",
        severity="block",
        category="Observability Key",
        redact=10,
    ),
    Pattern(
        name="New Relic API Key",
        regex=r"\bNR[A-Z]{2}-[a-zA-Z0-9]{27,}\b",
        severity="block",
        category="Observability Key",
        redact=8,
    ),
    Pattern(
        name="New Relic License Key (contextual)",
        regex=r"(?:NEW_RELIC|newrelic).{0,20}[=:\s]+[\"']?([a-f0-9]{40}(?:NRAL)?)[\"']?",
        severity="block",
        category="Observability Key",
        redact=10,
    ),
    Pattern(
        name="Sentry DSN",
        regex=r"https://[a-f0-9]{32}@(?:o\d+\.)?(?:sentry\.io|[a-zA-Z0-9.\-]+)/\d+",
        severity="block",
        category="Observability Key",
        redact=24,
    ),
    Pattern(
        name="PagerDuty Integration / API Key",
        regex=r"(?:pagerduty|PAGERDUTY).{0,20}[=:\s]+[\"']?([a-zA-Z0-9+/]{20,})[\"']?",
        severity="block",
        category="Observability Key",
        redact=10,
    ),
    Pattern(
        name="LaunchDarkly SDK / API Key",
        regex=r"\b(?:sdk|api|mob)-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b",
        severity="block",
        category="Feature Flag Key",
        redact=10,
    ),

    # ── CDN / Edge / DNS ───────────────────────────────────────────────────
    Pattern(
        name="Cloudflare API Token",
        regex=r"\b[a-zA-Z0-9_\-]{40}\b",
        severity="warn",  # too broad for block
        category="CDN/Edge Token",
        redact=8,
    ),
    Pattern(
        name="Cloudflare Global API Key (contextual)",
        regex=r"(?:cloudflare|CF_API_KEY).{0,20}[=:\s]+[\"']?([a-f0-9]{37})[\"']?",
        severity="block",
        category="CDN/Edge Token",
        redact=10,
    ),
    Pattern(
        name="Fastly API Token",
        regex=r"(?:fastly|FASTLY).{0,20}[=:\s]+[\"']?([a-zA-Z0-9\-_]{32})[\"']?",
        severity="block",
        category="CDN/Edge Token",
        redact=10,
    ),

    # ── Cloud infrastructure ───────────────────────────────────────────────
    Pattern(
        name="DigitalOcean Personal Access Token",
        regex=r"\b(?:dop_v1_|doo_v1_)[a-f0-9]{64}\b",
        severity="block",
        category="Cloud Credential",
        redact=12,
    ),
    Pattern(
        name="Linode Personal Access Token",
        regex=r"\b[a-f0-9]{64}\b",
        severity="warn",  # 64 hex chars is broad
        category="Cloud Credential",
        redact=8,
    ),

    # ── SaaS / Productivity ────────────────────────────────────────────────
    Pattern(
        name="Shopify Access Token",
        regex=r"\bshpat_[a-fA-F0-9]{32}\b",
        severity="block",
        category="API Key",
        redact=10,
    ),
    Pattern(
        name="Shopify Shared Secret",
        regex=r"\bshpss_[a-fA-F0-9]{32}\b",
        severity="block",
        category="API Key",
        redact=10,
    ),
    Pattern(
        name="Linear API Key",
        regex=r"\blin_api_[a-zA-Z0-9]{40}\b",
        severity="block",
        category="API Key",
        redact=12,
    ),
    Pattern(
        name="Algolia API Key",
        regex=r"(?:algolia|ALGOLIA).{0,20}[=:\s]+[\"']?([a-f0-9]{32})[\"']?",
        severity="block",
        category="API Key",
        redact=10,
    ),
    Pattern(
        name="Mapbox Access Token",
        regex=r"\bpk\.[a-zA-Z0-9]{60,}\.[a-zA-Z0-9_\-]{20,}\b",
        severity="block",
        category="API Key",
        redact=6,
    ),
    Pattern(
        name="Contentful Delivery/Preview Token",
        regex=r"(?:contentful|CONTENTFUL).{0,20}[=:\s]+[\"']?([a-zA-Z0-9\-_]{43,})[\"']?",
        severity="block",
        category="CMS Token",
        redact=10,
    ),

    # ── Auth providers ─────────────────────────────────────
    Pattern(
        name="Okta API Token",
        regex=r"\b00[a-zA-Z0-9_\-]{40}\b",
        severity="block",
        category="Auth Provider Token",
        redact=6,
    ),
    Pattern(
        name="Auth0 Management API Token (contextual)",
        regex=r"(?:auth0|AUTH0).{0,20}[=:\s]+[\"']?([a-zA-Z0-9\-_.]{30,})[\"']?",
        severity="block",
        category="Auth Provider Token",
        redact=10,
    ),

    # ── Streaming / Event platforms ────────────────────────────────────────
    Pattern(
        name="Confluent / Kafka API Key (contextual)",
        regex=r"(?:confluent|CONFLUENT|kafka|KAFKA).{0,20}(?:key|secret|password).{0,10}[=:\s]+[\"']?([a-zA-Z0-9+/]{16,})[\"']?",
        severity="block",
        category="Event Platform Key",
        redact=10,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 2: Cryptographic material
    # ═══════════════════════════════════════════════════════════════════════════

    Pattern(
        name="PEM Private Key",
        regex=r"-----BEGIN[A-Z \t]{0,30}PRIVATE KEY[A-Z \t]{0,10}-----",
        severity="block",
        category="Cryptographic Key",
        redact=20,
    ),
    Pattern(
        name="SSH Private Key (OpenSSH)",
        regex=r"-----BEGIN OPENSSH PRIVATE KEY-----",
        severity="block",
        category="Cryptographic Key",
        redact=20,
    ),
    Pattern(
        name="PGP Private Key Block",
        regex=r"-----BEGIN PGP PRIVATE KEY BLOCK-----",
        severity="block",
        category="Cryptographic Key",
        redact=20,
    ),
    Pattern(
        name="PEM Certificate",
        regex=r"-----BEGIN CERTIFICATE-----",
        severity="warn",
        category="Cryptographic Key",
        redact=20,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 3: Auth tokens & session material
    # ═══════════════════════════════════════════════════════════════════════════

    Pattern(
        name="JSON Web Token (JWT)",
        regex=r"\bey[a-zA-Z0-9\-_]{10,}\.ey[a-zA-Z0-9\-_]{10,}\.[a-zA-Z0-9\-_.+/=]{8,}\b",
        severity="block",
        category="Auth Token",
        redact=16,
    ),
    Pattern(
        name="Bearer Token in Authorization Header",
        regex=r"(?i)authorization\s*:\s*bearer\s+([a-zA-Z0-9\-_.+/=]{20,})",
        severity="block",
        category="Auth Token",
        redact=12,
    ),
    Pattern(
        name="X-API-Key Header Value",
        regex=r"(?i)x-api-key\s*:\s*([a-zA-Z0-9\-_.+/=]{16,})",
        severity="block",
        category="Auth Token",
        redact=10,
    ),
    Pattern(
        name="HTTP Basic Auth Credentials in URL",
        regex=r"https?://[a-zA-Z0-9_%.\-]+:[a-zA-Z0-9_%.\-!@#$%^&*()+={}\[\]|;:,<>?/~`]{3,}@",
        severity="block",
        category="Credential",
        redact=24,
    ),
    Pattern(
        name="OAuth Client Credentials in URL",
        regex=r"(?:client_secret|client_id)\s*=\s*[a-zA-Z0-9\-_.]{16,}",
        severity="block",
        category="Auth Token",
        redact=16,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 4: Database connection strings
    # ═══════════════════════════════════════════════════════════════════════════

    Pattern(
        name="Database Connection String (embedded password)",
        regex=(
            r"(?:jdbc:|postgres(?:ql)?://|mysql://|mongodb(?:\+srv)?://|"
            r"redis(?:s)?://|mssql://|mariadb://|cockroachdb://|"
            r"amqp(?:s)?://|nats://)"
            r"[a-zA-Z0-9_%.\-]+:"       # username
            r"[^\s]{3,}@"               # password (may contain @ and special chars)
            r"[a-zA-Z0-9.\-]"           # start of hostname (anchors the match)
        ),
        severity="block",
        category="Database Credential",
        redact=30,
    ),
    Pattern(
        name="DSN-style Connection (contextual)",
        regex=(
            r"(?:DATABASE_URL|DB_URL|REDIS_URL|MONGO_URI|MONGO_URL|"
            r"POSTGRES_URL|MYSQL_URL|AMQP_URL|NATS_URL)\s*[=:]\s*"
            r"[\"']?\S+://[^:\s]+:[^@\s]{3,}@"
        ),
        severity="block",
        category="Database Credential",
        redact=20,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 5: Shell / CLI / environment leakage
    # ═══════════════════════════════════════════════════════════════════════════

    Pattern(
        name="Shell Export of Secret Variable",
        regex=(
            r"(?:^|\n)\s*export\s+"
            r"(?:[A-Z_]*(?:SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|AUTH|"
            r"PRIVATE_KEY|ACCESS_KEY|CLIENT_SECRET|CREDENTIALS?|"
            r"DB_PASS|MASTER_KEY|SIGNING_KEY|ENCRYPTION_KEY)[A-Z_]*)"
            r"\s*=\s*[\"']?(\S{4,})[\"']?"
        ),
        severity="block",
        category="Shell Credential",
        redact=10,
    ),
    Pattern(
        name="Inline Env Var Secret Assignment",
        # Catches: AWS_SECRET_ACCESS_KEY=foo, GITHUB_TOKEN=bar, etc.
        regex=(
            r"(?:^|[\s;|&])"
            r"(?:AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN|"
            r"GITHUB_TOKEN|GH_TOKEN|GITLAB_TOKEN|"
            r"ANTHROPIC_API_KEY|OPENAI_API_KEY|"
            r"STRIPE_SECRET_KEY|STRIPE_API_KEY|"
            r"DATABASE_PASSWORD|DB_PASSWORD|DB_PASS|"
            r"SLACK_TOKEN|SLACK_BOT_TOKEN|SLACK_WEBHOOK|"
            r"SENTRY_DSN|DD_API_KEY|DD_APP_KEY|"
            r"FIREBASE_TOKEN|FIREBASE_API_KEY|"
            r"LAUNCH_DARKLY_SDK_KEY|LD_SDK_KEY|"
            r"NPM_TOKEN|DOCKER_PASSWORD|DOCKER_TOKEN|"
            r"OKTA_API_TOKEN|AUTH0_CLIENT_SECRET|"
            r"PRIVATE_KEY|SIGNING_SECRET|ENCRYPTION_KEY|"
            r"MASTER_KEY|SERVICE_KEY|WEBHOOK_SECRET)"
            r"\s*=\s*[\"']?(\S{4,})[\"']?"
        ),
        severity="block",
        category="Shell Credential",
        redact=10,
    ),
    Pattern(
        name="CLI Flag with Secret Value",
        # --api-key=X, --token X, --password X, --secret X, etc.
        regex=(
            r"--(?:api[_\-]?key|token|password|passwd|secret|"
            r"access[_\-]?key|auth[_\-]?token|private[_\-]?key|"
            r"client[_\-]?secret|api[_\-]?secret|credentials?)"
            r"[\s=]+[\"']?([^\s\"';|&]{4,})[\"']?"
        ),
        severity="block",
        category="CLI Credential",
        redact=6,
    ),
    Pattern(
        name="curl Basic Auth (-u user:pass)",
        regex=r"\bcurl\b.{0,100}-u\s+[\"']?([^\s\"':]+:[^\s\"']{3,})[\"']?",
        severity="block",
        category="CLI Credential",
        redact=10,
    ),
    Pattern(
        name="curl Auth Header",
        regex=r"\bcurl\b.{0,200}-H\s+[\"'](?:Authorization|X-API-Key)\s*:\s*(?:Bearer\s+)?([a-zA-Z0-9\-_.+/=]{16,})[\"']",
        severity="block",
        category="CLI Credential",
        redact=12,
    ),
    Pattern(
        name="Docker Environment Secret (-e / --env)",
        regex=(
            r"(?:docker|podman)\s+(?:run|exec|create).{0,200}"
            r"(?:-e|--env)\s+[\"']?"
            r"(?:[A-Z_]*(?:SECRET|PASSWORD|TOKEN|API_KEY|AUTH|PRIVATE_KEY|"
            r"CREDENTIALS?)[A-Z_]*)"
            r"=(\S{4,})[\"']?"
        ),
        severity="block",
        category="Container Credential",
        redact=10,
    ),
    Pattern(
        name="dotenv File Content (SECRET_VAR=value)",
        # Lines that look like .env file entries with secret variable names.
        regex=(
            r"(?:^|\n)\s*"
            r"(?:[A-Z_]*(?:SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|AUTH_TOKEN|"
            r"PRIVATE_KEY|ACCESS_KEY|CLIENT_SECRET|MASTER_KEY|SIGNING|"
            r"ENCRYPTION_KEY|DB_PASS|CREDENTIALS?)[A-Z_]*)"
            r"\s*=\s*[\"']?"
            r"(?!" + _PLACEHOLDER_WORDS + r")"
            r"([^\s\"'#]{6,})[\"']?"
        ),
        severity="block",
        category="Environment File Secret",
        redact=8,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 6: URL query parameter secrets
    # ═══════════════════════════════════════════════════════════════════════════

    Pattern(
        name="Secret in URL Query Parameter",
        regex=(
            r"[?&](?:api[_\-]?key|token|access[_\-]?token|secret|"
            r"auth|password|key|client[_\-]?secret|"
            r"private[_\-]?key|session[_\-]?id)"
            r"=([a-zA-Z0-9\-_.+/=%]{8,})(?:&|#|$|\s)"
        ),
        severity="block",
        category="URL Credential",
        redact=8,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 7: Natural language credential disclosure
    # ═══════════════════════════════════════════════════════════════════════════

    # Pattern: "[my] <cred_word> is/are <value>"
    Pattern(
        name="Natural Language Credential Disclosure",
        regex=(
            r"(?:^|[^a-zA-Z])"
            r"(?:my\s+)?"
            + _CRED_WORDS +
            r"\s+(?:is|are|was|were)\s+"
            + _NL_SAFE_WORDS +
            r"(\S{4,})"
        ),
        severity="block",
        category="Credential",
        redact=4,
    ),
    # Pattern: "here is my <cred>: X", "use this <cred>: X"
    Pattern(
        name="Natural Language Credential Handoff",
        regex=(
            r"(?:here(?:'s|\s+is)\s+(?:my|the|our)\s+|"
            r"(?:use|try|set|with|take|grab)\s+(?:this|the|my|our)\s+)"
            + _CRED_WORDS +
            r"[\s:=]+(\S{4,})"
        ),
        severity="block",
        category="Credential",
        redact=4,
    ),
    # Pattern: "the <cred> is <value>"
    Pattern(
        name="Natural Language Credential (definite article)",
        regex=(
            r"(?:^|[^a-zA-Z])"
            r"the\s+"
            + _CRED_WORDS +
            r"\s+(?:is|are|was|were)\s+"
            + _NL_SAFE_WORDS +
            r"(\S{4,})"
        ),
        severity="block",
        category="Credential",
        redact=4,
    ),
    # Pattern: "I set/changed/updated <cred> to <value>"
    Pattern(
        name="Natural Language Credential Mutation",
        regex=(
            r"(?:i\s+|i've\s+|we\s+|we've\s+)"
            r"(?:set|changed|updated|configured|assigned|reset|made)"
            r"\s+(?:my\s+|the\s+|our\s+)?"
            + _CRED_WORDS +
            r"\s+(?:to|as|=)\s+"
            + _NL_SAFE_WORDS +
            r"(\S{4,})"
        ),
        severity="block",
        category="Credential",
        redact=4,
    ),
    # Pattern: "<cred>: <value>" (bare label:value — e.g., pasted from a doc)
    Pattern(
        name="Labeled Credential Value",
        regex=(
            r"(?:^|\n)\s*"
            r"(?:password|api[\s_\-]?key|secret[\s_\-]?key|access[\s_\-]?key|"
            r"auth[\s_\-]?token|access[\s_\-]?token|bearer[\s_\-]?token|"
            r"client[\s_\-]?secret|private[\s_\-]?key|"
            r"master[\s_\-]?key|signing[\s_\-]?key|encryption[\s_\-]?key|"
            r"connection[\s_\-]?string|database[\s_\-]?password)"
            r"\s*:\s*[\"']?"
            r"(?!" + _PLACEHOLDER_WORDS + r")"
            r"([^\s\"']{6,})[\"']?"
        ),
        severity="block",
        category="Credential",
        redact=6,
    ),
    # Pattern: "login with <user>/<pass>" or "login <user> <pass>"
    Pattern(
        name="Natural Language Login Credentials",
        regex=(
            r"(?:login|sign\s*in|authenticate|connect)\s+"
            r"(?:with\s+|as\s+|using\s+)?"
            r"(?:user(?:name)?|login|account)\s*[=:/\s]+\s*(\S{3,})\s+"
            r"(?:and\s+)?(?:password|pass|pwd|passwd)\s*[=:/\s]+\s*(\S{3,})"
        ),
        severity="block",
        category="Credential",
        redact=4,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 8: Generic assignment patterns (lower confidence — warn)
    # ═══════════════════════════════════════════════════════════════════════════

    Pattern(
        name="Hardcoded Password Assignment (quoted)",
        regex=(
            r"(?:^|[^a-zA-Z])"
            r"(?:password|passwd|pwd)\s*[=:]\s*"
            r"[\"'](?!" + _PLACEHOLDER_WORDS + r")[^\s\"']{8,}[\"']"
        ),
        severity="warn",
        category="Credential",
        redact=6,
    ),
    Pattern(
        name="Hardcoded Password Assignment (unquoted)",
        regex=(
            r"(?:^|[^a-zA-Z])"
            r"(?:password|passwd|pwd)\s*[=:]\s*"
            r"(?!" + _PLACEHOLDER_WORDS + r")"
            r"([a-zA-Z0-9_.+/\-]{8,})"
        ),
        severity="warn",
        category="Credential",
        redact=6,
    ),
    Pattern(
        name="Hardcoded Secret / Token Assignment (quoted)",
        regex=(
            r"(?:^|[^a-zA-Z])"
            r"(?:secret|api_?key|auth_?token|access_?token|private_?key|"
            r"client_?secret|signing_?key|encryption_?key|master_?key|"
            r"service_?key|webhook_?secret)"
            r"\s*[=:]\s*"
            r"[\"'](?!" + _PLACEHOLDER_WORDS + r")[^\s\"']{10,}[\"']"
        ),
        severity="warn",
        category="Credential",
        redact=8,
    ),
    Pattern(
        name="Hardcoded Secret / Token Assignment (unquoted)",
        regex=(
            r"(?:^|[^a-zA-Z])"
            r"(?:secret|api_?key|auth_?token|access_?token|private_?key|"
            r"client_?secret|signing_?key|encryption_?key|master_?key|"
            r"service_?key|webhook_?secret)"
            r"\s*[=:]\s*"
            r"(?!" + _PLACEHOLDER_WORDS + r")"
            r"([a-zA-Z0-9_.+/\-]{10,})"
        ),
        severity="warn",
        category="Credential",
        redact=8,
    ),
    # JSON/YAML config blocks with secret keys
    Pattern(
        name="JSON/YAML Secret Field",
        regex=(
            r"[\"'](?:password|secret|api[_\-]?key|access[_\-]?token|"
            r"auth[_\-]?token|private[_\-]?key|client[_\-]?secret|"
            r"signing[_\-]?key|encryption[_\-]?key|master[_\-]?key|"
            r"service[_\-]?key|webhook[_\-]?secret|db[_\-]?password)[\"']"
            r"\s*:\s*"
            r"[\"'](?!" + _PLACEHOLDER_WORDS + r")([^\s\"']{6,})[\"']"
        ),
        severity="warn",
        category="Config Credential",
        redact=6,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 9: PII — Identity (block)
    # ═══════════════════════════════════════════════════════════════════════════

    Pattern(
        name="US Social Security Number (SSN)",
        regex=r"\b(?!000|666|9\d{2})\d{3}[-\s](?!00)\d{2}[-\s](?!0000)\d{4}\b",
        severity="block",
        category="PII — Identity",
        redact=5,
    ),
    Pattern(
        name="US Individual Taxpayer ID (ITIN)",
        regex=r"\b9\d{2}[-\s](?:5[0-9]|6[0-5]|7[0-9]|8[0-8]|9[0-24-9])[-\s]\d{4}\b",
        severity="block",
        category="PII — Identity",
        redact=5,
    ),
    Pattern(
        name="US Passport Number",
        regex=r"\b[A-Z][0-9]{8}\b",
        severity="warn",
        category="PII — Identity",
        redact=4,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 10: PII — Contact (warn)
    # ═══════════════════════════════════════════════════════════════════════════

    Pattern(
        name="Email Address",
        regex=r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        severity="warn",
        category="PII — Contact",
        redact=5,
    ),
    Pattern(
        name="US / Canadian Phone Number",
        regex=r"\b(?:\+1[\s.\-]?)?\(?[2-9][0-9]{2}\)?[\s.\-]?[2-9][0-9]{2}[\s.\-]?[0-9]{4}\b",
        severity="warn",
        category="PII — Contact",
        redact=5,
    ),
    Pattern(
        name="International Phone Number (E.164)",
        regex=r"\+(?!1[\s.\-])[1-9][0-9]{6,13}\b",
        severity="warn",
        category="PII — Contact",
        redact=6,
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 11: Network identifiers (warn)
    # ═══════════════════════════════════════════════════════════════════════════

    Pattern(
        name="IPv4 Address",
        regex=(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        ),
        severity="warn",
        category="Network — IP (use project IP library)",
        redact=8,
    ),
    Pattern(
        name="AWS Account ID (12 digits)",
        regex=r"\b[0-9]{12}\b",
        severity="warn",
        category="Cloud Metadata",
        redact=4,
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Credit card detection (separate from regex patterns — requires Luhn check)
# ─────────────────────────────────────────────────────────────────────────────

_CC_RE = re.compile(
    r"\b"
    r"(?:"
    r"4[0-9]{12}(?:[0-9]{3,6})?"          # Visa (13, 16, 19 digits)
    r"|5[1-5][0-9]{14}"                    # Mastercard (classic range)
    r"|2(?:2[2-9][1-9]|[3-6][0-9]{2}|7[01][0-9]|720)[0-9]{12}"  # MC (2xxx range)
    r"|3[47][0-9]{13}"                     # Amex
    r"|3(?:0[0-5]|[68][0-9])[0-9]{11}"   # Diners Club
    r"|6(?:011|5[0-9]{2})[0-9]{12}"      # Discover
    r"|(?:2131|1800|35\d{3})\d{11}"       # JCB
    r"|62[0-9]{14,17}"                     # UnionPay
    r")"
    r"(?:[\s\-][0-9]{4})*"               # optional space/dash-separated groups
    r"\b",
    re.ASCII,
)


def _luhn(number: str) -> bool:
    """Return True if `number` (digits only) passes the Luhn checksum."""
    digits = [int(d) for d in number]
    total = sum(digits[-1::-2])  # odd positions from right (0-indexed)
    for d in digits[-2::-2]:    # even positions from right
        doubled = d * 2
        total += doubled if doubled < 10 else doubled - 9
    return total % 10 == 0


def find_credit_cards(text: str) -> list[str]:
    """Return a list of raw matches that are Luhn-valid card numbers."""
    results = []
    for m in _CC_RE.finditer(text):
        raw = m.group()
        digits = re.sub(r"[\s\-]", "", raw)
        if 13 <= len(digits) <= 19 and _luhn(digits):
            results.append(raw.strip())
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Entropy-based detection (catch-all for unknown secret formats)
# ─────────────────────────────────────────────────────────────────────────────

_ENTROPY_CONTEXT_RE = re.compile(
    r"(?:password|passwd|secret|api[_\-]?key|token|auth|"
    r"private[_\-]?key|access[_\-]?key|client[_\-]?secret|"
    r"credentials?|signing|encryption|master[_\-]?key|"
    r"webhook[_\-]?secret|service[_\-]?key|connection[_\-]?string)"
    r"\s*[=:\s]+\s*[\"']?"
    r"([a-zA-Z0-9\-_.+/=!@#$%^&*~]{12,})"
    r"[\"']?",
    re.IGNORECASE,
)


def _shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy in bits per character."""
    if not s:
        return 0.0
    length = len(s)
    counts = Counter(s)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts.values()
    )


def find_high_entropy_secrets(text: str) -> list[str]:
    """Find high-entropy strings near credential keywords.

    Returns raw match strings where the value has Shannon entropy > 4.5
    bits/char — a strong signal that the string is a real secret rather
    than a placeholder or English word.
    """
    results = []
    for m in _ENTROPY_CONTEXT_RE.finditer(text):
        value = m.group(1)
        # Skip known placeholder patterns
        lower = value.lower()
        if any(p in lower for p in (
            "example", "placeholder", "changeme", "test", "fake",
            "dummy", "sample", "your_", "xxx", "todo", "fixme",
            "insert", "replace", "redacted",
        )):
            continue
        # Skip very short values or all-same-char
        if len(set(value)) < 5:
            continue
        if _shannon_entropy(value) > 4.5:
            results.append(m.group(0).strip())
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Scanner core
# ─────────────────────────────────────────────────────────────────────────────

def _redact(text: str, show: int) -> str:
    """Reveal at most `show` characters then mask the rest."""
    text = text.strip()
    if len(text) <= show:
        return "***"
    return text[:show] + "***"


def scan(text: str) -> tuple[list[Finding], list[Finding]]:
    """
    Scan `text` for sensitive data.

    Returns:
        (blocking_findings, warning_findings) — each is a list of Finding.
        Blocking findings should cause exit 2; warnings allow exit 0.
    """
    blocks: list[Finding] = []
    warns: list[Finding] = []

    for pat in PATTERNS:
        m = pat.search(text)
        if m is None:
            continue
        snippet = _redact(m.group(0), pat.redact)
        finding = Finding(
            name=pat.name,
            category=pat.category,
            severity=pat.severity,
            snippet=snippet,
        )
        (blocks if pat.severity == "block" else warns).append(finding)

    # Credit card detection (Luhn-validated)
    for cc in find_credit_cards(text):
        blocks.append(Finding(
            name="Credit Card Number",
            category="PII — Payment",
            severity="block",
            snippet=_redact(cc, 4) + " (Luhn-valid)",
        ))

    # Entropy-based catch-all
    for ent in find_high_entropy_secrets(text):
        blocks.append(Finding(
            name="High-Entropy Secret (near credential keyword)",
            category="Credential (entropy-detected)",
            severity="block",
            snippet=_redact(ent, 12),
        ))

    return blocks, warns


# ─────────────────────────────────────────────────────────────────────────────
# Output formatting
# ─────────────────────────────────────────────────────────────────────────────

_HR = "─" * 68


def _fmt_findings(findings: list[Finding], label: str) -> str:
    lines = []
    for f in findings:
        lines.append(f"  [{label}]  {f.category}")
        lines.append(f"           {f.name} — {f.snippet}")
    return "\n".join(lines)


def build_block_output(blocks: list[Finding], warns: list[Finding]) -> str:
    parts = [
        _HR,
        "  Prompt Scanner — BLOCKED",
        _HR,
        "",
        "Your prompt was NOT sent to the model because it appears to contain",
        "sensitive data. Review and redact before retrying.",
        "",
        _fmt_findings(blocks, "BLOCK"),
    ]
    if warns:
        parts += ["", _fmt_findings(warns, "WARN")]
    parts += [
        "",
        "Tips:",
        "  • Use environment variables or a secrets manager instead of",
        "    pasting credentials directly into prompts.",
        "  • For test data, use well-known placeholder values",
        "    (e.g., Visa test card 4111 1111 1111 1111).",
        "  • Set PROMPT_SCANNER_MODE=audit to log-only (never blocks).",
        _HR,
    ]
    return "\n".join(parts)


def build_warn_output(warns: list[Finding]) -> str:
    parts = [
        "",
        _HR,
        "  Prompt Scanner — WARNING  (prompt was sent)",
        _HR,
        "",
        _fmt_findings(warns, "WARN"),
        "",
        "Review whether the flagged data above is intentional.",
        "For IP addresses: use the project IP library, not raw strings.",
        _HR,
    ]
    return "\n".join(parts)


def build_audit_output(blocks: list[Finding], warns: list[Finding]) -> str:
    all_f = blocks + warns
    parts = [
        _HR,
        "  Prompt Scanner — AUDIT",
        _HR,
        "",
        _fmt_findings([f for f in all_f if f.severity == "block"], "BLOCK"),
        "",
        _fmt_findings([f for f in all_f if f.severity == "warn"], "WARN"),
        _HR,
    ]
    return "\n".join(p for p in parts if p is not None)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    mode = os.environ.get("PROMPT_SCANNER_MODE", "standard").lower()

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)  # Unreadable input — fail open, never block

    prompt: str = data.get("prompt", "")
    if not prompt.strip():
        sys.exit(0)

    blocks, warns = scan(prompt)

    # ── Audit mode: log everything, never block ──────────────────────────
    if mode == "audit":
        if blocks or warns:
            print(build_audit_output(blocks, warns), file=sys.stderr)
        sys.exit(0)

    # ── Strict mode: treat all warnings as blocks ────────────────────────
    if mode == "strict":
        blocks = blocks + warns
        warns = []

    # ── Block ────────────────────────────────────────────────────────────
    if blocks:
        print(build_block_output(blocks, warns), file=sys.stderr)
        sys.exit(2)

    # ── Warn only ────────────────────────────────────────────────────────
    if warns:
        print(build_warn_output(warns), flush=True)

    sys.exit(0)


if __name__ == "__main__":
    main()
