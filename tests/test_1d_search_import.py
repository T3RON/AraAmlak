"""
Phase 1D tests — normalize_fa, search/filter, ImportJob, import service, dedupe.

Run with:
  pytest --ds=ara_amlak.settings.testing_nogis tests/test_1d_search_import.py -v
"""


import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

# ─── normalize_fa ─────────────────────────────────────────────────────────────

class TestNormalizeFa:
    def test_arabic_kaf(self):
        from apps.core.text import normalize_fa
        assert normalize_fa("كتاب") == "کتاب"

    def test_arabic_yeh(self):
        from apps.core.text import normalize_fa
        assert normalize_fa("مشاوري") == "مشاوری"

    def test_eastern_arabic_digits(self):
        from apps.core.text import normalize_fa
        assert normalize_fa("١٢٣") == "123"

    def test_indic_digits(self):
        from apps.core.text import normalize_fa
        assert normalize_fa("۴۵۶") == "456"

    def test_zero_width_removed(self):
        from apps.core.text import normalize_fa
        text = "سلام\u200cدنیا"
        assert normalize_fa(text) == "سلامدنیا"

    def test_multiple_spaces_collapsed(self):
        from apps.core.text import normalize_fa
        assert normalize_fa("تهران   پارس") == "تهران پارس"

    def test_none_returns_empty(self):
        from apps.core.text import normalize_fa
        assert normalize_fa(None) == ""

    def test_idempotent(self):
        from apps.core.text import normalize_fa
        s = "خیابان ولیعصر ۱۲"
        assert normalize_fa(normalize_fa(s)) == normalize_fa(s)

    def test_mixed_digits_and_text(self):
        from apps.core.text import normalize_fa
        assert normalize_fa("متراژ ۸۰ متر") == "متراژ 80 متر"


class TestNormalizePhoneIr:
    def test_plus98(self):
        from apps.core.text import normalize_phone_ir
        assert normalize_phone_ir("+989123456789") == "09123456789"

    def test_0098(self):
        from apps.core.text import normalize_phone_ir
        assert normalize_phone_ir("00989123456789") == "09123456789"

    def test_98(self):
        from apps.core.text import normalize_phone_ir
        assert normalize_phone_ir("989123456789") == "09123456789"

    def test_missing_leading_zero(self):
        from apps.core.text import normalize_phone_ir
        assert normalize_phone_ir("9123456789") == "09123456789"

    def test_already_correct(self):
        from apps.core.text import normalize_phone_ir
        assert normalize_phone_ir("09123456789") == "09123456789"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def listing_set(db, agency):
    """Create 4 listings with varying attributes for filter tests."""
    from apps.listings.models import DealType, Listing, ListingStatus, PropertyType
    listings = []
    data = [
        {"deal_type": DealType.SALE, "property_type": PropertyType.APARTMENT,
         "city": "تهران", "district": "ولنجک", "area": 80, "rooms": 2,
         "sale_price": 5_000_000_000, "status": ListingStatus.ACTIVE},
        {"deal_type": DealType.RENT, "property_type": PropertyType.APARTMENT,
         "city": "تهران", "district": "پونک", "area": 60, "rooms": 1,
         "rent_amount": 5_000_000, "status": ListingStatus.ACTIVE},
        {"deal_type": DealType.SALE, "property_type": PropertyType.VILLA,
         "city": "اصفهان", "district": "جلفا", "area": 200, "rooms": 4,
         "sale_price": 12_000_000_000, "status": ListingStatus.RESERVED},
        {"deal_type": DealType.MORTGAGE_RENT, "property_type": PropertyType.COMMERCIAL,
         "city": "تهران", "district": "شریعتی", "area": 40, "rooms": 0,
         "mortgage_amount": 800_000_000, "status": ListingStatus.ACTIVE},
    ]
    for d in data:
        listings.append(Listing.objects.create(agency=agency, **d))
    return listings


# ─── Search / filter ──────────────────────────────────────────────────────────

class TestBuildListingQueryset:
    def _q(self, params, agency):
        from apps.core.models import clear_current_agency, set_current_agency
        from apps.listings.search_service import build_listing_queryset
        set_current_agency(agency)
        try:
            return list(build_listing_queryset(params))
        finally:
            clear_current_agency()

    def test_no_filters_returns_all(self, db, agency, listing_set):
        results = self._q({}, agency)
        assert len(results) == 4

    def test_filter_by_deal_type(self, db, agency, listing_set):
        results = self._q({"deal_type": "sale"}, agency)
        assert len(results) == 2
        assert all(item.deal_type == "sale" for item in results)

    def test_filter_by_status(self, db, agency, listing_set):
        results = self._q({"status": "reserved"}, agency)
        assert len(results) == 1
        assert results[0].city == "اصفهان"

    def test_filter_by_city(self, db, agency, listing_set):
        results = self._q({"city": "تهران"}, agency)
        assert len(results) == 3

    def test_filter_by_district(self, db, agency, listing_set):
        results = self._q({"district": "ولنجک"}, agency)
        assert len(results) == 1

    def test_filter_by_min_area(self, db, agency, listing_set):
        results = self._q({"min_area": "80"}, agency)
        assert all(item.area >= 80 for item in results)

    def test_filter_by_max_area(self, db, agency, listing_set):
        results = self._q({"max_area": "70"}, agency)
        assert all(item.area <= 70 for item in results)

    def test_search_q_matches_city(self, db, agency, listing_set):
        results = self._q({"q": "اصفهان"}, agency)
        assert len(results) == 1
        assert results[0].city == "اصفهان"

    def test_search_normalizes_arabic_kaf(self, db, agency, listing_set):
        """Searching with Arabic كاف should still find Persian ک."""
        from apps.listings.models import DealType, Listing, ListingStatus, PropertyType
        Listing.objects.create(
            agency=agency,
            deal_type=DealType.SALE,
            property_type=PropertyType.APARTMENT,
            city="کرج",
            status=ListingStatus.ACTIVE,
        )
        # Arabic kaf in query
        results = self._q({"q": "كرج"}, agency)
        assert any(item.city == "کرج" for item in results)

    def test_sort_by_area_desc(self, db, agency, listing_set):
        results = self._q({"sort": "-area"}, agency)
        areas = [item.area for item in results if item.area]
        assert areas == sorted(areas, reverse=True)

    def test_invalid_min_area_ignored(self, db, agency, listing_set):
        """Non-numeric min_area should not raise, just be ignored."""
        results = self._q({"min_area": "abc"}, agency)
        assert len(results) == 4


# ─── Import service: CSV parsing ─────────────────────────────────────────────

class TestImportServiceCsv:
    def _make_csv(self, rows: list[list[str]]) -> bytes:
        lines = [",".join(r) for r in rows]
        return "\n".join(lines).encode("utf-8")

    def test_parse_valid_csv(self):
        from apps.listings.import_service import parse_import_file
        csv_bytes = self._make_csv([
            ["نوع معامله", "نوع ملک", "شهر", "متراژ"],
            ["فروش", "آپارتمان", "تهران", "80"],
        ])
        headers, rows = parse_import_file(csv_bytes, "test.csv")
        assert "نوع معامله" in headers
        assert len(rows) == 1
        assert rows[0][2] == "تهران"

    def test_parse_empty_csv(self):
        from apps.listings.import_service import parse_import_file
        headers, rows = parse_import_file(b"", "empty.csv")
        assert headers == []
        assert rows == []

    def test_map_headers_arabic_kaf(self):
        """Header with Arabic kاf should map to canonical field."""
        from apps.listings.import_service import _map_headers
        headers = ["نوع معامله", "شهر", "متراژ"]
        col_map = _map_headers(headers)
        # At least deal_type, city, area should be mapped
        assert 0 in col_map  # نوع معامله → deal_type
        assert 1 in col_map  # شهر → city

    def test_coerce_row_valid(self):
        from apps.listings.import_service import _coerce_row
        raw = {
            "deal_type": "فروش",
            "property_type": "آپارتمان",
            "city": "تهران",
            "area": "۸۰",
            "rooms": "2",
            "sale_price": "5000000000",
            "parking": "بله",
        }
        data, errors = _coerce_row(raw)
        assert errors == []
        assert data["deal_type"] == "sale"
        assert data["property_type"] == "apartment"
        assert data["area"] == 80
        assert data["parking"] is True

    def test_coerce_row_invalid_deal_type(self):
        from apps.listings.import_service import _coerce_row
        raw = {"deal_type": "ندانستم", "property_type": "آپارتمان", "city": "تهران"}
        data, errors = _coerce_row(raw)
        assert any("نوع معامله" in e for e in errors)

    def test_coerce_row_invalid_price(self):
        from apps.listings.import_service import _coerce_row
        raw = {"deal_type": "فروش", "property_type": "آپارتمان",
               "city": "تهران", "sale_price": "abc"}
        data, errors = _coerce_row(raw)
        assert any("قیمت" in e for e in errors)


# ─── run_import_job ───────────────────────────────────────────────────────────

class TestRunImportJob:
    def _make_csv_file(self, rows: list[list[str]]) -> bytes:
        lines = [",".join(r) for r in rows]
        return "\n".join(lines).encode("utf-8")

    def test_import_valid_rows(self, db, agency, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.listings.import_service import run_import_job
        from apps.listings.models import ImportJob, ImportJobStatus, Listing

        csv_bytes = self._make_csv_file([
            ["نوع معامله", "نوع ملک", "شهر", "متراژ", "اتاق"],
            ["فروش", "آپارتمان", "تهران", "80", "2"],
            ["اجاره", "آپارتمان", "اصفهان", "60", "1"],
        ])
        f = SimpleUploadedFile("test.csv", csv_bytes, content_type="text/csv")
        job = ImportJob.objects.create(
            agency=agency,
            uploaded_file=f,
            original_filename="test.csv",
        )

        result = run_import_job(job.pk)

        job.refresh_from_db()
        assert job.status == ImportJobStatus.DONE
        assert job.imported_rows == 2
        assert job.error_rows == 0
        assert result["imported"] == 2

        # Verify listings were actually created
        count = Listing.all_objects.filter(agency=agency).count()
        assert count >= 2

    def test_import_missing_required_fields(self, db, agency, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.listings.import_service import run_import_job
        from apps.listings.models import ImportJob, ImportJobStatus

        # Row missing نوع ملک and city
        csv_bytes = self._make_csv_file([
            ["نوع معامله"],
            ["فروش"],
        ])
        f = SimpleUploadedFile("bad.csv", csv_bytes, content_type="text/csv")
        job = ImportJob.objects.create(
            agency=agency, uploaded_file=f, original_filename="bad.csv",
        )
        run_import_job(job.pk)
        job.refresh_from_db()
        assert job.status == ImportJobStatus.DONE
        assert job.error_rows == 1
        assert len(job.error_report) >= 1

    def test_import_invalid_deal_type(self, db, agency, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.listings.import_service import run_import_job
        from apps.listings.models import ImportJob

        csv_bytes = self._make_csv_file([
            ["نوع معامله", "نوع ملک", "شهر"],
            ["نامعتبر", "آپارتمان", "تهران"],
        ])
        f = SimpleUploadedFile("inv.csv", csv_bytes, content_type="text/csv")
        job = ImportJob.objects.create(
            agency=agency, uploaded_file=f, original_filename="inv.csv",
        )
        run_import_job(job.pk)
        job.refresh_from_db()
        assert job.error_rows >= 1


# ─── Dedupe ───────────────────────────────────────────────────────────────────

class TestDedupeCheck:
    def test_detects_duplicate(self, db, agency):
        from apps.listings.import_service import check_duplicate
        from apps.listings.models import DealType, Listing, ListingStatus, PropertyType

        Listing.objects.create(
            agency=agency,
            deal_type=DealType.SALE,
            property_type=PropertyType.APARTMENT,
            city="تهران",
            district="ولنجک",
            area=80,
            status=ListingStatus.ACTIVE,
        )
        # Same city + district + area within 10% tolerance → duplicate
        assert check_duplicate(agency, "تهران", "ولنجک", 82) is True

    def test_no_duplicate_different_city(self, db, agency):
        from apps.listings.import_service import check_duplicate
        from apps.listings.models import DealType, Listing, ListingStatus, PropertyType

        Listing.objects.create(
            agency=agency,
            deal_type=DealType.SALE,
            property_type=PropertyType.APARTMENT,
            city="تهران",
            area=80,
            status=ListingStatus.ACTIVE,
        )
        assert check_duplicate(agency, "اصفهان", "", 80) is False

    def test_no_duplicate_area_outside_tolerance(self, db, agency):
        from apps.listings.import_service import check_duplicate
        from apps.listings.models import DealType, Listing, ListingStatus, PropertyType

        Listing.objects.create(
            agency=agency,
            deal_type=DealType.SALE,
            property_type=PropertyType.APARTMENT,
            city="تهران",
            area=80,
            status=ListingStatus.ACTIVE,
        )
        # 150 is > 10% above 80 → not a duplicate
        assert check_duplicate(agency, "تهران", "", 150) is False


# ─── Tenant isolation ─────────────────────────────────────────────────────────

class TestImportJobTenantIsolation:
    def test_import_job_scoped_to_agency(self, db, agency, agency_b):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.listings.models import ImportJob

        f = SimpleUploadedFile("a.csv", b"", content_type="text/csv")
        ImportJob.objects.create(
            agency=agency, uploaded_file=f, original_filename="a.csv",
        )
        # agency_b should see zero ImportJobs
        from apps.core.models import clear_current_agency, set_current_agency
        set_current_agency(agency_b)
        try:
            assert ImportJob.objects.count() == 0
        finally:
            clear_current_agency()
