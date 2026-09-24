"""
Tests for Phase 5B — Persian transcript parsing and smart draft.

Coverage:
- parse_listing_transcript (pure parser): area, rooms, floors, build year,
  prices (digits / word numbers / compound), amenities with negation,
  property type, direction, district, deal type, missing, confidence
- _resolve_neighborhood (name / contains / alias / miss)
- extract_draft service (transcript guard, fields, idempotency)
- apply_draft_to_listing (Listing creation, state updates, code generation)
- Draft views (generate, apply, agency scoping)
"""

from __future__ import annotations

import pytest

# ─── Parser (pure) ────────────────────────────────────────────────────────────


class TestParserBasics:
    def test_full_sale_transcript(self):
        from apps.ai.draft_parser import parse_listing_transcript

        result = parse_listing_transcript(
            "یک آپارتمان فروشی در محله سعادت‌آباد، هشتاد متر، دو خواب، "
            "طبقه سوم از پنج طبقه، ساخت ۱۳۹۰، شمالی، پارکینگ دارد، آسانسور دارد، "
            "انباری دارد، قیمت پنج میلیارد تومان."
        )
        data = result["data"]
        assert data["area"] == 80
        assert data["rooms"] == 2
        assert data["floor"] == 3
        assert data["total_floors"] == 5
        assert data["build_year"] == 2011  # 1390 شمسی + 621
        assert data["sale_price"] == 5_000_000_000
        assert data["property_type"] == "apartment"
        assert data["direction"] == "north"
        assert data["deal_type"] == "sale"
        assert data["district"] == "سعادتآباد"
        assert data["parking"] is True
        assert data["elevator"] is True
        assert data["storage"] is True
        assert result["missing"] == []

    def test_mortgage_and_rent(self):
        from apps.ai.draft_parser import parse_listing_transcript

        result = parse_listing_transcript(
            "اجاره مغازه در محله بازار، ۴۰ متر بدون پارکینگ، "
            "رهن ۵۰ میلیون و اجاره ماهی ۸ میلیون تومان"
        )
        data = result["data"]
        assert data["area"] == 40
        assert data["property_type"] == "commercial"
        assert data["deal_type"] == "mortgage_rent"
        assert data["mortgage_amount"] == 50_000_000
        assert data["rent_amount"] == 8_000_000
        assert data["parking"] is False  # «بدون پارکینگ»
        assert data["district"] == "بازار"
        assert "rent_amount" not in result["missing"]

    def test_compound_price(self):
        from apps.ai.draft_parser import parse_listing_transcript

        result = parse_listing_transcript(
            "ویلایی شمالی دویست و پنجاه متر، ۵ خواب، طبقه اول، "
            "قیمت یک میلیارد و دویست میلیون تومان"
        )
        data = result["data"]
        assert data["area"] == 250  # «دویست و پنجاه»
        assert data["rooms"] == 5
        assert data["floor"] == 1  # «طبقه اول»
        assert data["sale_price"] == 1_200_000_000  # 1e9 + 200e6
        assert data["direction"] == "north"

    def test_compound_words_glued(self):
        """Whisper-style glued words: دوخوابه، هشتادمتری."""
        from apps.ai.draft_parser import parse_listing_transcript

        result = parse_listing_transcript("یک آپارتمان دوخوابه هشتادمتری")
        assert result["data"]["rooms"] == 2
        assert result["data"]["area"] == 80

    def test_two_digit_build_year(self):
        from apps.ai.draft_parser import parse_listing_transcript

        result = parse_listing_transcript("زمین کلنگی ساخت ۷۵")
        assert result["data"]["build_year"] == 1996  # 1375 شمسی + 621
        assert result["data"]["property_type"] == "land"

    def test_rent_deal_type(self):
        from apps.ai.draft_parser import parse_listing_transcript

        result = parse_listing_transcript(
            "آپارتمان پنجاه متری با بالکن، اجاره دو میلیون تومان"
        )
        assert result["data"]["deal_type"] == "rent"
        assert result["data"]["rent_amount"] == 2_000_000
        assert result["data"]["balcony"] is True

    def test_no_negation_means_true(self):
        from apps.ai.draft_parser import parse_listing_transcript

        result = parse_listing_transcript("آپارتمان ۱۰۰ متر با پارکینگ")
        assert result["data"]["parking"] is True

    def test_empty_transcript(self):
        from apps.ai.draft_parser import parse_listing_transcript

        result = parse_listing_transcript("سلام خوبید")
        assert result["data"].get("deal_type") == "sale"  # default
        assert result["missing"] == ["area", "rooms", "sale_price"]
        assert result["confidence"] == 0.0

    def test_confidence_partial(self):
        from apps.ai.draft_parser import parse_listing_transcript

        result = parse_listing_transcript("هشتاد متر دو خواب")
        # 2 of 15 scored fields found
        assert result["confidence"] == round(2 / 15, 2)


# ─── Neighborhood resolution ─────────────────────────────────────────────────


@pytest.fixture
def neighborhood(db):
    from apps.listings.models import City, Neighborhood

    city = City.objects.create(name="تهران", province="تهران", slug="tehran")
    return Neighborhood.objects.create(
        city=city,
        name="سعادت‌آباد",
        aliases=["سعادت اباد", "saadat abad"],
    )


@pytest.mark.django_db
class TestResolveNeighborhood:
    def test_exact_name(self, neighborhood):
        from apps.ai.services import _resolve_neighborhood

        assert _resolve_neighborhood("سعادت‌آباد") == neighborhood

    def test_contains_name(self, neighborhood):
        from apps.ai.services import _resolve_neighborhood

        assert _resolve_neighborhood("سعادتآباد عالی") == neighborhood

    def test_alias(self, neighborhood):
        from apps.ai.services import _resolve_neighborhood

        assert _resolve_neighborhood("saadat abad") == neighborhood

    def test_no_match(self, neighborhood):
        from apps.ai.services import _resolve_neighborhood

        assert _resolve_neighborhood("ونک") is None
        assert _resolve_neighborhood("") is None


# ─── extract_draft ────────────────────────────────────────────────────────────


def _make_voice_note(agency, user, transcript, status="transcribed"):
    from apps.ai.models import VoiceNote
    from tests.test_5a_voice_transcription import _ogg_upload

    return VoiceNote.objects.create(
        agency=agency,
        audio=_ogg_upload(),
        original_filename="voice.ogg",
        mime_type="audio/ogg",
        status=status,
        transcript=transcript,
        uploaded_by=user,
    )


@pytest.mark.django_db
class TestExtractDraft:
    def test_creates_draft_with_fields(self, agency, user, neighborhood):
        from apps.ai.services import extract_draft

        note = _make_voice_note(
            agency, user, "آپارتمان در محله سعادت‌آباد، هشتاد متر، دو خواب، قیمت دو میلیارد تومان"
        )
        draft = extract_draft(note)
        assert draft.voice_note == note
        assert draft.parser == "regex_fa"
        assert draft.data["area"] == 80
        assert draft.data["neighborhood"] == neighborhood.pk
        assert draft.data["sale_price"] == 2_000_000_000
        assert draft.status == "draft"

    def test_requires_transcribed_state(self, agency, user):
        from django.core.exceptions import ValidationError

        from apps.ai.services import extract_draft

        note = _make_voice_note(agency, user, "متنی", status="queued")
        with pytest.raises(ValidationError, match="رونویسی"):
            extract_draft(note)

    def test_reextract_replaces_old_draft(self, agency, user):
        from apps.ai.models import VoiceDraft
        from apps.ai.services import extract_draft

        note = _make_voice_note(agency, user, "هشتاد متر دو خواب قیمت سه میلیارد تومان")
        first = extract_draft(note)
        second = extract_draft(note)
        assert first.pk != second.pk
        assert not VoiceDraft.objects.filter(pk=first.pk).exists()


# ─── apply_draft_to_listing ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestApplyDraft:
    def _make_draft(self, agency, user, data=None):
        from apps.ai.models import VoiceDraft

        note = _make_voice_note(agency, user, "هشتاد متر")
        return VoiceDraft.objects.create(
            agency=agency,
            voice_note=note,
            data=data
            or {
                "area": 80,
                "rooms": 2,
                "sale_price": 3_000_000_000,
                "property_type": "apartment",
                "deal_type": "sale",
                "parking": True,
            },
            missing=[],
            confidence=0.5,
            parser="regex_fa",
        )

    def test_creates_listing(self, agency, user):
        from apps.ai.services import apply_draft_to_listing
        from apps.listings.models import ListingStatus

        draft = self._make_draft(agency, user)
        listing = apply_draft_to_listing(draft, user)

        assert listing.pk is not None
        assert listing.code  # auto-generated
        assert listing.status == ListingStatus.DRAFT
        assert listing.area == 80
        assert listing.rooms == 2
        assert listing.sale_price == 3_000_000_000
        assert listing.parking is True
        assert listing.elevator is False  # default
        assert listing.assigned_to == user

        draft.refresh_from_db()
        assert draft.status == "applied"
        assert draft.listing == listing
        draft.voice_note.refresh_from_db()
        assert draft.voice_note.listing == listing

    def test_neighborhood_resolution(self, agency, user, neighborhood):
        from apps.ai.services import apply_draft_to_listing

        draft = self._make_draft(agency, user, {"area": 60, "neighborhood": neighborhood.pk})
        listing = apply_draft_to_listing(draft, user)
        assert listing.neighborhood == neighborhood

    def test_apply_is_idempotent_guarded_by_view(self, agency, user):
        """Service re-apply creates a second listing — views guard this."""
        from apps.ai.services import apply_draft_to_listing

        draft = self._make_draft(agency, user)
        apply_draft_to_listing(draft, user)
        draft.status = "draft"  # simulate stale state
        draft.save()
        apply_draft_to_listing(draft, user)
        # Two listings — the view layer prevents this in normal flow
        from apps.listings.models import Listing

        assert Listing.all_objects.count() == 2


# ─── Views ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDraftViews:
    def _transcribed_note(self, agency, user):
        return _make_voice_note(
            agency,
            user,
            "آپارتمان هشتاد متر دو خواب قیمت دو میلیارد تومان",
        )

    def test_detail_page_shows_generate_button(self, client, user, agency):
        note = self._transcribed_note(agency, user)
        client.force_login(user)
        resp = client.get(f"/ai/voice/{note.pk}/")
        assert resp.status_code == 200
        assert "استخراج پیش‌نویس" in resp.content.decode()

    def test_generate_draft(self, client, user, agency):
        note = self._transcribed_note(agency, user)
        client.force_login(user)
        resp = client.post(f"/ai/voice/{note.pk}/draft/")
        assert resp.status_code == 200
        assert "پیش‌نویس فایل" in resp.content.decode()

        from apps.ai.models import VoiceDraft

        assert VoiceDraft.objects.filter(voice_note=note).exists()

    def test_generate_requires_transcribed(self, client, user, agency):
        note = _make_voice_note(agency, user, "متنی", status="queued")
        client.force_login(user)
        resp = client.post(f"/ai/voice/{note.pk}/draft/")
        assert resp.status_code == 422

    def test_generate_other_agency_404(self, client, user_b, agency):
        note = self._transcribed_note(agency, user_b.agency.members.first())
        client.force_login(user_b)
        # note belongs to `agency`, user_b belongs to agency_b → 404
        resp = client.post(f"/ai/voice/{note.pk}/draft/")
        assert resp.status_code == 404

    def test_apply_redirects_to_listing_edit(self, client, user, agency):
        from apps.ai.models import VoiceDraft
        from apps.listings.models import Listing

        note = self._transcribed_note(agency, user)
        draft = VoiceDraft.objects.create(
            agency=agency,
            voice_note=note,
            data={"area": 80, "rooms": 2, "sale_price": 3_000_000_000},
            missing=[],
            confidence=0.5,
            parser="regex_fa",
        )
        client.force_login(user)
        resp = client.post(f"/ai/draft/{draft.pk}/apply/")
        assert resp.status_code == 302

        draft.refresh_from_db()
        assert draft.status == "applied"
        listing = Listing.objects.get(agency=agency, area=80)
        assert resp.url == f"/listings/{listing.pk}/edit/"

    def test_apply_other_agency_404(self, client, user_b, agency):
        from apps.ai.models import VoiceDraft

        note = _make_voice_note(agency, user_b.agency.members.first(), "متنی")
        draft = VoiceDraft.objects.create(
            agency=agency, voice_note=note, data={}, parser="regex_fa"
        )
        client.force_login(user_b)
        resp = client.post(f"/ai/draft/{draft.pk}/apply/")
        assert resp.status_code == 404

    def test_apply_already_applied_redirects_to_listing(self, client, user, agency):
        from apps.ai.models import VoiceDraft
        from apps.listings.models import Listing

        note = _make_voice_note(agency, user, "متنی")
        listing = Listing.objects.create(agency=agency, city="تهران")
        draft = VoiceDraft.objects.create(
            agency=agency,
            voice_note=note,
            data={},
            parser="regex_fa",
            listing=listing,
            status="applied",
        )
        client.force_login(user)
        resp = client.post(f"/ai/draft/{draft.pk}/apply/")
        assert resp.status_code == 302
        assert resp.url == f"/listings/{listing.pk}/"
