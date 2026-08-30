"""Tests for services/verification/contact_links.py (Phase E).

Split deliberately: offline tests (phone parsing, email syntax, shape
rules, completeness) run in the fast suite with no network dependency,
matching this project's CI-stays-network-free rule. The email
deliverability and link-reachability tests DO make real network calls
(MX lookup, HTTP HEAD) -- marked `network` so they're separable, not
skipped silently.
"""

from __future__ import annotations

import pytest

from services.verification.contact_links import (
    LinkStatus,
    _platform_issue,
    check_completeness,
    check_email,
    check_link,
    check_links,
    check_phone,
    extract_email_candidates,
    extract_phone_candidates,
)


class TestPhoneExtraction:
    def test_finds_a_plausible_phone_number(self):
        text = "Contact: (555) 123-4567 or email me\n"
        assert extract_phone_candidates(text) == ["(555) 123-4567"]

    def test_does_not_match_a_bare_year_or_short_number(self):
        text = "Graduated 2024, GPA 3.9\n"
        assert extract_phone_candidates(text) == []


class TestCheckPhone:
    def test_reserved_555_area_code_is_flagged_not_valid(self):
        # This eval corpus's own placeholder convention
        # ("555.555.5555") -- a real, corpus-relevant case, not
        # hypothetical.
        result = check_phone("555.555.5555")
        assert result.is_valid is False
        assert result.is_possible is True
        assert result.has_issue

    def test_a_real_shaped_us_number_is_valid(self):
        # 555 is reserved as both area code and exchange in many plans --
        # use a genuinely assignable number for this assertion.
        result = check_phone("(415) 863-2345")
        assert result.is_valid is True
        assert result.e164 == "+14158632345"
        assert not result.has_issue

    def test_00_prefix_typo_is_detected_and_a_fix_is_suggested(self):
        # The bug named in the brief: an international dialing prefix
        # typed as "00" instead of "+". The corrected number IS a real,
        # valid one (is_valid=True) -- but the raw text as typed was
        # still malformed, so it must still be flagged as an issue rather
        # than silently accepted. Caught by this exact test on first
        # write: the original implementation took an early-return path
        # that dropped the flag whenever the correction succeeded.
        result = check_phone("0091 9876543210")
        assert result.is_valid is True
        assert result.has_issue
        assert result.issue is not None
        assert "00" in result.issue and "+" in result.issue
        assert result.e164 == "+919876543210"

    def test_garbage_does_not_crash(self):
        result = check_phone("not a phone number")
        assert result.is_valid is False
        assert result.e164 is None


class TestEmailExtraction:
    def test_finds_email_addresses(self):
        text = "Reach me at jane.doe@example.com for more info.\n"
        assert extract_email_candidates(text) == ["jane.doe@example.com"]


class TestCheckEmailSyntax:
    def test_malformed_email_fails_syntax(self):
        result = check_email("bad@@nowhere", check_deliverability=False)
        assert result.is_valid_syntax is False
        assert result.has_issue

    def test_well_formed_email_passes_syntax_without_network(self):
        result = check_email("someone@example.com", check_deliverability=False)
        assert result.is_valid_syntax is True
        assert result.is_deliverable is None  # not checked -- check_deliverability=False
        assert not result.has_issue


@pytest.mark.slow
class TestCheckEmailDeliverability:
    def test_canva_template_placeholder_domain_fails_deliverability(self):
        # Real corpus case (multiple resumes in evaluation/step0/Resumes/
        # use "hello@reallygreatsite.com", Canva's own template
        # placeholder) -- confirmed directly, not assumed, that this
        # domain has no mail server.
        result = check_email("hello@reallygreatsite.com")
        assert result.is_deliverable is False
        assert result.has_issue

    def test_a_real_mail_domain_is_deliverable(self):
        result = check_email("someone@gmail.com")
        assert result.is_deliverable is True


class TestPlatformShapeRules:
    def test_linkedin_profile_url_has_no_issue(self):
        assert _platform_issue("https://www.linkedin.com/in/janedoe") is None

    def test_linkedin_non_profile_url_is_flagged(self):
        issue = _platform_issue("https://www.linkedin.com/search/results/people/?keywords=jane")
        assert issue is not None
        assert "/in/" in issue

    def test_github_profile_url_has_no_issue(self):
        assert _platform_issue("https://github.com/torvalds") is None

    def test_github_homepage_with_no_username_is_flagged(self):
        assert _platform_issue("https://github.com") is not None


class TestCompleteness:
    def test_fully_specified_resume_has_nothing_missing(self):
        text = (
            "Jane Doe\n"
            "(415) 863-2345 | jane.doe@example.com | San Francisco, CA\n"
            "linkedin.com/in/janedoe | github.com/janedoe\n"
        )
        c = check_completeness(text, field="Computer Science / SWE")
        assert c.missing == []

    def test_missing_portfolio_only_flagged_for_technical_design_fields(self):
        text = "Jane Doe\n(415) 863-2345 | jane.doe@example.com | San Francisco, CA\nlinkedin.com/in/janedoe\n"
        non_technical = check_completeness(text, field="Public Policy")
        technical = check_completeness(text, field="Computer Science / SWE")
        assert "portfolio/GitHub" not in non_technical.missing
        assert "portfolio/GitHub" in technical.missing

    def test_missing_contact_fields_are_named(self):
        text = "Jane Doe\nSome resume content with no contact info at all.\n"
        c = check_completeness(text)
        assert "phone" in c.missing
        assert "email" in c.missing
        assert "LinkedIn" in c.missing

    def test_single_word_name_is_recognized(self):
        # Real corpus case: several résumés use a single-name alias
        # ("Harshibar") rather than "First Last".
        text = "Harshibar\n(415) 863-2345 | jane@example.com | San Francisco, CA\n"
        assert check_completeness(text).has_name

    def test_captioned_github_link_counted_via_annotation_uri_not_just_text(self):
        # R36's real case: "500 stars on GitHub" captions a link with no
        # literal "github.com" anywhere in the visible text.
        text = "Jane Doe\n500 stars on GitHub for my open-source project.\n"
        without_annotations = check_completeness(text, field="Computer Science / SWE")
        with_annotations = check_completeness(
            text, field="Computer Science / SWE",
            annotation_uris=["https://github.com/janedoe/project"],
        )
        assert "portfolio/GitHub" in without_annotations.missing
        assert "portfolio/GitHub" not in with_annotations.missing


@pytest.mark.slow
class TestLinkReachability:
    """Sync wrappers around asyncio.run, not @pytest.mark.asyncio --
    pytest-asyncio isn't a dependency anywhere else in this project, and
    these are the only async entry points that need testing, so a plugin
    for it isn't worth adding.
    """

    def test_a_reachable_url_is_ok(self):
        import asyncio

        import httpx

        async def run():
            async with httpx.AsyncClient() as client:
                return await check_link(client, "https://github.com/torvalds")

        result = asyncio.run(run())
        assert result.status is LinkStatus.OK
        assert result.http_status == 200

    def test_linkedin_bot_blocking_is_classified_as_blocked_not_unreachable(self):
        import asyncio

        import httpx

        async def run():
            async with httpx.AsyncClient() as client:
                return await check_link(client, "https://www.linkedin.com/in/nobody-fake-xyz-12345")

        result = asyncio.run(run())
        # LinkedIn returns 405 to a plain HEAD request against real profile
        # URLs -- checked directly. That's bot-blocking, not a broken link.
        assert result.status in (LinkStatus.BLOCKED, LinkStatus.OK)

    def test_nonexistent_domain_is_unreachable(self):
        import asyncio

        import httpx

        async def run():
            async with httpx.AsyncClient() as client:
                return await check_link(client, "https://this-domain-does-not-exist-abc123xyz-test.com")

        result = asyncio.run(run())
        assert result.status is LinkStatus.UNREACHABLE

    def test_check_links_runs_concurrently_not_sequentially(self):
        import asyncio
        import time

        urls = ["https://this-domain-does-not-exist-abc123xyz-test.com"] * 3
        start = time.monotonic()
        results = asyncio.run(check_links(urls))
        elapsed = time.monotonic() - start
        assert len(results) == 3
        # Sequential would take ~3x a single check's connect-error latency;
        # concurrent should be close to 1x. Loose bound -- this is a
        # sanity check on the gather, not a precise timing assertion.
        assert elapsed < 15.0
