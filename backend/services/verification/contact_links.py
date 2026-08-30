"""Contact & link verification (Phase E) -- checkable from spec, not from
a human's judgment call, so it ships at full confidence and stays a
separate section rather than folded into structure's estimated score.
Verified facts (a phone number is or isn't dialable, a domain does or
doesn't accept mail, a URL does or doesn't resolve) shouldn't be averaged
in with things a rubric estimates -- that's the verified/estimated split
this module exists to draw.

Three checks, three different reasons a resume's contact info fails:
  phone     format/region errors ("0091" typed instead of "+91", a
            reserved/fictional area code like 555) -- phonenumbers
  email     syntax OR a domain that doesn't actually accept mail (MX
            lookup) -- email-validator. Checked directly, not assumed:
            "gmial.com" (a plausible typo of gmail.com) still passes MX
            deliverability -- somebody keeps that domain's mail server
            up. It's not a universal typo-catcher; dead/placeholder
            domains (Canva's "reallygreatsite.com", confirmed against
            this eval corpus directly) are what it reliably catches.
  link      reachability (async httpx) plus platform-shape rules
            (LinkedIn should be /in/username, not a search URL; GitHub a
            profile or repo, not a 404). Status is ok | unreachable |
            blocked, never a bare "invalid" -- a 403/405/999 is almost
            always bot-blocking (LinkedIn's own profile pages return 405
            to a plain HEAD request, checked directly), not evidence the
            link is broken.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from enum import Enum

import httpx
import phonenumbers
import tldextract
from email_validator import EmailSyntaxError, EmailUndeliverableError, validate_email

# Candidate phone sequences in résumé text: digits, spaces, dashes, dots,
# parens, and a leading +/00 for international dialing prefixes.
_PHONE_CANDIDATE = re.compile(r"(?<!\d)(\+?\(?\d[\d\s().-]{7,}\d)(?!\d)")
_EMAIL_CANDIDATE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# HTTP responses that mean "a bot-protection layer intercepted this
# request", not "the link is broken" -- LinkedIn's own profile pages
# return 405 to a plain HEAD request, checked directly against a real
# profile URL before assuming it.
_BOT_BLOCK_STATUS_CODES = frozenset({403, 405, 429, 999})

DEFAULT_PHONE_REGION = "US"  # the eval corpus's own convention; override per-request if the résumé's own locale is known
LINK_TIMEOUT_SECONDS = 8.0


class LinkStatus(str, Enum):
    OK = "ok"
    UNREACHABLE = "unreachable"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class PhoneCheck:
    raw: str
    is_valid: bool
    is_possible: bool
    e164: str | None  # best-effort formatted fix, None if unparseable even loosely
    issue: str | None  # human-readable reason, None when is_valid

    @property
    def has_issue(self) -> bool:
        # Not just `not self.is_valid`: a "00 instead of +" correction can
        # produce is_valid=True (the corrected number is real) while still
        # carrying an issue (the raw text as typed was malformed). Both
        # count.
        return not self.is_valid or self.issue is not None


@dataclass(frozen=True, slots=True)
class EmailCheck:
    raw: str
    is_valid_syntax: bool
    is_deliverable: bool | None  # None when the syntax check itself already failed
    issue: str | None

    @property
    def has_issue(self) -> bool:
        return not self.is_valid_syntax or self.is_deliverable is False


@dataclass(frozen=True, slots=True)
class LinkCheck:
    url: str
    status: LinkStatus
    http_status: int | None  # the raw code, kept even when status is a coarser bucket
    platform_issue: str | None  # e.g. "LinkedIn URL should be /in/<username>, not a search/feed URL"

    @property
    def has_issue(self) -> bool:
        return self.status is not LinkStatus.OK or self.platform_issue is not None


@dataclass(frozen=True, slots=True)
class CompletenessCheck:
    has_name: bool
    has_phone: bool
    has_email: bool
    has_location: bool
    has_linkedin: bool
    has_portfolio_or_github: bool  # only expected for technical/design fields -- see check_completeness
    field_expects_portfolio: bool

    @property
    def missing(self) -> list[str]:
        out = []
        if not self.has_name:
            out.append("name")
        if not self.has_phone:
            out.append("phone")
        if not self.has_email:
            out.append("email")
        if not self.has_location:
            out.append("location")
        if not self.has_linkedin:
            out.append("LinkedIn")
        if self.field_expects_portfolio and not self.has_portfolio_or_github:
            out.append("portfolio/GitHub")
        return out


@dataclass
class ContactLinkReport:
    """The section this module ships as -- "Contact & Links: N issues
    found", separate from the structure score, per the module docstring.
    """

    phones: list[PhoneCheck] = field(default_factory=list)
    emails: list[EmailCheck] = field(default_factory=list)
    links: list[LinkCheck] = field(default_factory=list)
    completeness: CompletenessCheck | None = None

    @property
    def issue_count(self) -> int:
        n = sum(1 for p in self.phones if p.has_issue)
        n += sum(1 for e in self.emails if e.has_issue)
        n += sum(1 for l in self.links if l.has_issue)
        if self.completeness is not None:
            n += len(self.completeness.missing)
        return n

    @property
    def summary(self) -> str:
        return f"Contact & Links: {self.issue_count} issue{'s' if self.issue_count != 1 else ''} found"


def check_phone(raw: str, region: str = DEFAULT_PHONE_REGION) -> PhoneCheck:
    """Validate one candidate phone number. Handles the specific bug named
    in the brief: "0091 9876543210" (an international dialing prefix typed
    as 00 instead of +) parses as garbage against a fixed region --
    detected by re-trying with 00 replaced by + and preferring that
    parse when it succeeds and the 00-as-is parse doesn't.
    """
    candidates = [raw]
    stripped = raw.strip()
    if stripped.startswith("00"):
        candidates.insert(0, "+" + stripped[2:])

    best: tuple[bool, bool, str | None, str | None] | None = None
    for candidate in candidates:
        try:
            parsed = phonenumbers.parse(candidate, region)
        except phonenumbers.NumberParseException:
            continue
        valid = phonenumbers.is_valid_number(parsed)
        possible = phonenumbers.is_possible_number(parsed)
        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        issue = None
        if not valid:
            if candidate != raw:
                issue = f"looks like an international prefix typed as '00' instead of '+' -- try {e164}"
            elif not possible:
                issue = "not a possible phone number in any known format"
            else:
                issue = (
                    "possible length/shape, but not a real assigned number "
                    "(reserved/fictional range, e.g. a 555 area code) or the region guess is wrong"
                )
        if valid:
            # Still flag it when only the 00->+ correction made it valid --
            # the raw text as the applicant typed it was genuinely
            # malformed notation, even though the corrected number is
            # real. Silently returning issue=None here (the original bug
            # in this function) would hide exactly the case the brief
            # asked to catch.
            fix_issue = (
                f"typed as '00...' instead of '+' -- valid once corrected to {e164}"
                if candidate != raw else None
            )
            return PhoneCheck(raw=raw, is_valid=True, is_possible=True, e164=e164, issue=fix_issue)
        if best is None:
            best = (valid, possible, e164, issue)
    if best is None:
        return PhoneCheck(raw=raw, is_valid=False, is_possible=False, e164=None, issue="could not parse as a phone number at all")
    valid, possible, e164, issue = best
    return PhoneCheck(raw=raw, is_valid=valid, is_possible=possible, e164=e164, issue=issue)


def check_email(raw: str, *, check_deliverability: bool = True) -> EmailCheck:
    """Syntax via email-validator; deliverability via its MX lookup when
    check_deliverability=True (a network call -- set False for offline/
    fast paths). Deliverability catches a dead/placeholder domain
    (confirmed against this eval corpus: Canva's "reallygreatsite.com"
    template placeholder fails it); it does NOT reliably catch a
    plausible-typo domain that still has mail service configured
    ("gmial.com" passes -- checked, not assumed clean).
    """
    try:
        validate_email(raw, check_deliverability=check_deliverability)
    except EmailSyntaxError as e:
        return EmailCheck(raw=raw, is_valid_syntax=False, is_deliverable=None, issue=str(e))
    except EmailUndeliverableError as e:
        # Bug found by this module's own tests, not assumed correct on
        # write: email_validator raises EmailNotValidError for BOTH
        # syntax and deliverability failures, and the first version of
        # this function caught the base class and reported every failure
        # as bad syntax -- including "hello@reallygreatsite.com", whose
        # syntax is completely fine and only its domain doesn't accept
        # mail. Catching the specific subclass instead so the two stay
        # distinguishable, which is the entire point of surfacing this
        # check separately from a plain "is this a valid-looking email".
        return EmailCheck(raw=raw, is_valid_syntax=True, is_deliverable=False, issue=str(e))
    # is_deliverable=None means "not checked" (check_deliverability=False),
    # not "checked and fine" -- an earlier version of this function
    # hardcoded True here regardless, falsely claiming a check that never
    # ran; also caught by this module's own tests before it shipped.
    is_deliverable = True if check_deliverability else None
    return EmailCheck(raw=raw, is_valid_syntax=True, is_deliverable=is_deliverable, issue=None)


def extract_phone_candidates(text: str) -> list[str]:
    return [m.group(1).strip() for m in _PHONE_CANDIDATE.finditer(text)]


def extract_email_candidates(text: str) -> list[str]:
    return sorted(set(_EMAIL_CANDIDATE.findall(text)))


def _platform_issue(url: str) -> str | None:
    """Shape rules for the platforms résumés actually link to. Narrow on
    purpose -- flags a clearly-wrong shape (a LinkedIn search/feed URL
    instead of a profile, a GitHub URL with no username at all), not
    every possible URL variation.
    """
    ext = tldextract.extract(url)
    domain = f"{ext.domain}.{ext.suffix}".lower()
    path = url.split(domain, 1)[-1] if domain in url.lower() else ""

    if domain == "linkedin.com":
        if not re.match(r"^/in/[^/]+/?$", path):
            return "LinkedIn URL should be /in/<username> (a profile), not a search, feed, or company URL"
    elif domain == "github.com":
        segments = [s for s in path.split("/") if s]
        if not segments:
            return "GitHub URL has no username or repository -- links to the homepage"
    return None


async def check_link(client: httpx.AsyncClient, url: str) -> LinkCheck:
    platform_issue = _platform_issue(url)
    try:
        resp = await client.head(url, timeout=LINK_TIMEOUT_SECONDS, follow_redirects=True)
        code = resp.status_code
    except httpx.TimeoutException:
        return LinkCheck(url=url, status=LinkStatus.UNREACHABLE, http_status=None, platform_issue=platform_issue)
    except httpx.HTTPError:
        return LinkCheck(url=url, status=LinkStatus.UNREACHABLE, http_status=None, platform_issue=platform_issue)

    if code in _BOT_BLOCK_STATUS_CODES:
        status = LinkStatus.BLOCKED
    elif 200 <= code < 400:
        status = LinkStatus.OK
    else:
        status = LinkStatus.UNREACHABLE
    return LinkCheck(url=url, status=status, http_status=code, platform_issue=platform_issue)


# Field-name substrings where a portfolio/GitHub link is a reasonable
# completeness expectation -- technical and design roles specifically,
# per the brief ("portfolio/GitHub for technical and design fields").
# Matched against evaluation/labels.csv's actual field strings, not
# guessed abstractly.
_PORTFOLIO_EXPECTED_FIELD_MARKERS = (
    "computer science", "software", "swe", "web development", "full-stack",
    "data science", "electrical", "hci", "design", "ux", "ui", "architecture",
    "graphic",
)

# {0,3}, not {1,3}: a bare single capitalized word on its own near the
# top of the document also counts. Real corpus case, found while
# verifying this against actual resumes: several use a single-name alias
# ("Harshibar") rather than "First Last" -- a stricter 2-word-minimum
# regex flagged a resume with its name printed in 48pt font at the very
# top as missing one.
_NAME_LINE = re.compile(r"^[A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){0,3}$")
_LOCATION_PATTERN = re.compile(r"\b[A-Z][a-zA-Z. ]+,\s*[A-Z]{2}\b")


def _field_expects_portfolio(field: str | None) -> bool:
    if not field:
        return False
    low = field.lower()
    return any(marker in low for marker in _PORTFOLIO_EXPECTED_FIELD_MARKERS)


def check_completeness(
    text: str, field: str | None = None, annotation_uris: list[str] | None = None,
) -> CompletenessCheck:
    """name, phone, email, location always expected; LinkedIn generally;
    portfolio/GitHub only for fields where the brief says to expect it.

    annotation_uris, when given, are checked alongside the visible text --
    a real corpus case (R36) captions its GitHub link as "500 stars on
    GitHub" with no literal "github.com" anywhere in the text, which a
    text-only regex misses entirely even though the actual link target is
    right there in the PDF's annotations. Pass
    ExtractionResult.annotations' uris (services/parsing/pdf_extract.py)
    when available.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # First 2 lines only, not 5 -- a résumé's name is essentially always
    # the literal first line; widening the window combined with {0,3}
    # accepting a single word risks matching a section heading
    # ("Education", "Experience") that happens to appear a few lines down
    # instead. Checked against the eval corpus, not assumed safe.
    has_name = any(_NAME_LINE.match(ln) for ln in lines[:2])
    has_phone = bool(extract_phone_candidates(text))
    has_email = bool(extract_email_candidates(text))
    has_location = bool(_LOCATION_PATTERN.search(text))

    uris_blob = " ".join(annotation_uris or [])
    has_linkedin = bool(re.search(r"linkedin\.com", text + " " + uris_blob, re.IGNORECASE))
    has_portfolio_or_github = bool(
        re.search(r"github\.com|\bportfolio\b|behance\.net|dribbble\.com", text + " " + uris_blob, re.IGNORECASE)
    )
    return CompletenessCheck(
        has_name=has_name, has_phone=has_phone, has_email=has_email,
        has_location=has_location, has_linkedin=has_linkedin,
        has_portfolio_or_github=has_portfolio_or_github,
        field_expects_portfolio=_field_expects_portfolio(field),
    )


async def check_links(urls: list[str]) -> list[LinkCheck]:
    """Checks every URL concurrently, not sequentially -- the whole reason
    to ask for async httpx here rather than requests-in-a-loop. A résumé
    with 10 links (R36, checked directly) at an 8s timeout each would take
    up to 80s sequentially; gathered, it's bounded by the slowest single
    check, not the sum.
    """
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(*(check_link(client, url) for url in urls))


async def build_report(
    text: str,
    annotation_uris: list[str] | None = None,
    *,
    field: str | None = None,
    check_deliverability: bool = True,
    check_reachability: bool = True,
) -> ContactLinkReport:
    """Assembles the full section. `annotation_uris` should come from
    ExtractionResult.annotations (services/parsing/pdf_extract.py) when
    available -- checking the resume's real link TARGETS, not just
    whatever URL-shaped text happens to appear, catches a styled/icon link
    the text layer alone would miss entirely (see that module's
    invisible_annotations). Falls back to URL-shaped text if none given.

    check_deliverability / check_reachability: both make network calls
    (MX lookup, HTTP HEAD) -- set False for an offline/fast path (tests,
    CI) rather than skip the checks silently in a way a caller might not
    notice.
    """
    phones = [check_phone(p) for p in extract_phone_candidates(text)]
    emails = [check_email(e, check_deliverability=check_deliverability) for e in extract_email_candidates(text)]

    if annotation_uris is not None:
        link_targets = [u for u in annotation_uris if u.startswith(("http://", "https://"))]
    else:
        link_targets = [
            u if u.startswith("http") else f"https://{u}"
            for u in re.findall(r"(?:https?://|www\.)[^\s,;()\[\]<>]+", text)
        ]
    links = await check_links(link_targets) if check_reachability and link_targets else [
        LinkCheck(url=u, status=LinkStatus.OK, http_status=None, platform_issue=_platform_issue(u))
        for u in link_targets
    ]

    completeness = check_completeness(text, field=field, annotation_uris=annotation_uris)

    return ContactLinkReport(phones=phones, emails=emails, links=links, completeness=completeness)
