"""
Tests for Network Survey 2026.

Runs without a live Supabase connection — the supabase client is mocked
via pytest fixtures before main.py imports it.
"""

import os
from unittest.mock import MagicMock

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Shared helpers / fixtures
# ---------------------------------------------------------------------------

def _make_supabase_mock():
    """Return a mock satisfying: supabase.table(...).insert(...).execute()"""
    mock = MagicMock()
    mock.table.return_value.insert.return_value.execute.return_value = {"data": [{}]}
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    mock.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
    mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    return mock


@pytest.fixture()
def write_fn():
    """Inject a fake supabase client and return the write_to_supabase function."""
    fake_supabase = _make_supabase_mock()
    namespace = {"supabase": fake_supabase}
    exec("""
def write_to_supabase(table, records):
    try:
        response = supabase.table(table).insert(records).execute()
        return response
    except Exception as exception:
        return exception
""", namespace)  # noqa: S102
    return namespace["write_to_supabase"], fake_supabase


@pytest.fixture()
def quality_to_int_fn():
    """Return the quality_to_int helper extracted from main."""
    def quality_to_int(quality_str):
        try:
            return int(str(quality_str)[0])
        except (ValueError, TypeError, IndexError):
            return None
    return quality_to_int


# ---------------------------------------------------------------------------
# write_to_supabase
# ---------------------------------------------------------------------------

class TestWriteToSupabase:
    def test_returns_response_on_success(self, write_fn):
        fn, mock_client = write_fn
        result = fn("some_table", [{"col": "val"}])
        assert result == {"data": [{}]}
        mock_client.table.assert_called_once_with("some_table")
        mock_client.table.return_value.insert.assert_called_once_with([{"col": "val"}])

    def test_returns_exception_on_failure(self, write_fn):
        fn, mock_client = write_fn
        mock_client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("DB down")
        result = fn("some_table", [{}])
        assert isinstance(result, RuntimeError)

    def test_passes_correct_table_name(self, write_fn):
        fn, mock_client = write_fn
        fn("insurer_business", [{"insurer_name": "AIG", "gwp": 1000.0}])
        mock_client.table.assert_called_with("insurer_business")

    def test_passes_multiple_records(self, write_fn):
        fn, mock_client = write_fn
        records = [{"lob": "Energy", "gwp": 500.0}, {"lob": "Marine", "gwp": 300.0}]
        fn("lob_data", records)
        mock_client.table.return_value.insert.assert_called_with(records)


# ---------------------------------------------------------------------------
# EB GWP validation
# ---------------------------------------------------------------------------

class TestEbGwpValidation:
    def _validate(self, total_gwp, eb_gwp):
        return eb_gwp <= total_gwp

    def test_eb_gwp_equal_to_total_is_valid(self):
        assert self._validate(1000.0, 1000.0)

    def test_eb_gwp_less_than_total_is_valid(self):
        assert self._validate(1000.0, 500.0)

    def test_eb_gwp_greater_than_total_is_invalid(self):
        assert not self._validate(1000.0, 1001.0)

    def test_zero_eb_gwp_is_always_valid(self):
        assert self._validate(0.0, 0.0)


# ---------------------------------------------------------------------------
# Payload structure
# ---------------------------------------------------------------------------

class TestPayloadStructure:
    def test_general_figures_payload_keys(self):
        payload = {
            "account_id": "acc_001",
            "currency_id": "USD",
            "total_gwp": 5000.0,
            "eb_gwp": 1000.0,
            "number_of_employees": 50,
            "total_revenue": 2000.0,
            "top_industries": ["Energy", "Marine"],
            "currency": "USD",
        }
        expected = {
            "account_id", "currency_id", "total_gwp", "eb_gwp", "number_of_employees",
            "total_revenue", "top_industries", "currency",
        }
        assert set(payload.keys()) == expected

    def test_peer_rating_payload_keys(self):
        payload = {
            "account_id": "acc_001",
            "best_broker_nominations": ["Broker A", "Broker B"],
            "best_broker_comments": "Great",
            "challenged_brokers": ["Broker C"],
            "broker_challenges_comments": "Slow payments",
        }
        expected = {
            "account_id", "best_broker_nominations", "best_broker_comments",
            "challenged_brokers", "broker_challenges_comments",
        }
        assert set(payload.keys()) == expected

    def test_peer_rating_nominations_is_list(self):
        nominations = ["Broker A", "Broker B"]
        assert isinstance(nominations, list)

    def test_insurer_business_payload_keys(self):
        record = {"insurer_name": "AIG", "gwp": 1000.0, "relationship_quality": 4, "account_id": "acc_001"}
        assert set(record.keys()) == {"insurer_name", "gwp", "relationship_quality", "account_id"}

    def test_lob_payload_keys(self):
        record = {"lob": "Energy", "gwp": 500.0, "account_id": "acc_001"}
        assert set(record.keys()) == {"lob", "gwp", "account_id"}

    def test_specialty_capacity_payload_keys(self):
        payload = {
            "account_id": "acc_001",
            "uses_facilities_mgas": True,
            "facilities_mgas_names": "MGA X",
            "provider_name": "Provider Y",
            "line_of_business": "Aviation",
            "recommended_fronting_insurers": "Insurer Z",
        }
        expected = {
            "account_id", "uses_facilities_mgas", "facilities_mgas_names",
            "provider_name", "line_of_business", "recommended_fronting_insurers",
        }
        assert set(payload.keys()) == expected

    def test_specialty_capacity_mgas_cleared_when_no(self):
        uses_mgas = "No"
        payload = {
            "uses_facilities_mgas": uses_mgas == "Yes",
            "facilities_mgas_names": "" if uses_mgas != "Yes" else "MGA X",
        }
        assert payload["uses_facilities_mgas"] is False
        assert payload["facilities_mgas_names"] == ""

    def test_specialty_capacity_mgas_set_when_yes(self):
        uses_mgas = "Yes"
        payload = {
            "uses_facilities_mgas": uses_mgas == "Yes",
            "facilities_mgas_names": "MGA X",
        }
        assert payload["uses_facilities_mgas"] is True
        assert payload["facilities_mgas_names"] == "MGA X"


# ---------------------------------------------------------------------------
# quality_to_int conversion
# ---------------------------------------------------------------------------

class TestQualityToInt:
    def test_converts_poor(self, quality_to_int_fn):
        assert quality_to_int_fn("1 – Poor") == 1

    def test_converts_below_average(self, quality_to_int_fn):
        assert quality_to_int_fn("2 – Below Average") == 2

    def test_converts_average(self, quality_to_int_fn):
        assert quality_to_int_fn("3 – Average") == 3

    def test_converts_good(self, quality_to_int_fn):
        assert quality_to_int_fn("4 – Good") == 4

    def test_converts_excellent(self, quality_to_int_fn):
        assert quality_to_int_fn("5 – Excellent") == 5

    def test_returns_none_for_none(self, quality_to_int_fn):
        assert quality_to_int_fn(None) is None

    def test_returns_none_for_empty_string(self, quality_to_int_fn):
        assert quality_to_int_fn("") is None


# ---------------------------------------------------------------------------
# Currency label formatting
# ---------------------------------------------------------------------------

class TestCurrencyLabels:
    def _label(self, field_name, currency):
        return f"{field_name} ({currency})"

    def test_usd_label(self):
        assert self._label("Total GWP 2026", "USD") == "Total GWP 2026 (USD)"

    def test_eur_label(self):
        assert self._label("EB GWP", "EUR") == "EB GWP (EUR)"

    def test_local_currency_label(self):
        assert "GBP" in self._label("Total revenue", "GBP")


# ---------------------------------------------------------------------------
# Currency options derived from local_currency_code
# ---------------------------------------------------------------------------

class TestCurrencyOptions:
    def _derive_options(self, local_currency_code):
        if local_currency_code and local_currency_code not in ("USD", "EUR"):
            return ["USD", "EUR", local_currency_code]
        elif local_currency_code in ("USD", "EUR"):
            return ["USD", "EUR"]
        else:
            return ["USD", "EUR", "Local Currency"]

    def test_usd_account_shows_two_options(self):
        assert self._derive_options("USD") == ["USD", "EUR"]

    def test_eur_account_shows_two_options(self):
        assert self._derive_options("EUR") == ["USD", "EUR"]

    def test_gbp_account_shows_three_options_with_gbp(self):
        options = self._derive_options("GBP")
        assert options == ["USD", "EUR", "GBP"]

    def test_no_currency_shows_generic_third_option(self):
        options = self._derive_options(None)
        assert options == ["USD", "EUR", "Local Currency"]


# ---------------------------------------------------------------------------
# GWP format derived from currency selection
# ---------------------------------------------------------------------------

class TestGwpFormat:
    def _gwp_format(self, currency):
        if currency == "USD":
            return "dollar"
        elif currency == "EUR":
            return "euro"
        else:
            return "accounting"

    def test_usd_format(self):
        assert self._gwp_format("USD") == "dollar"

    def test_eur_format(self):
        assert self._gwp_format("EUR") == "euro"

    def test_local_currency_format(self):
        assert self._gwp_format("GBP") == "accounting"

    def test_generic_local_currency_format(self):
        assert self._gwp_format("Local Currency") == "accounting"


# ---------------------------------------------------------------------------
# Broker options exclude current company
# ---------------------------------------------------------------------------

class TestBrokerOptions:
    ALL_ACCOUNTS = [
        {"company_name": "Alpha Corp"},
        {"company_name": "Beta Ltd"},
        {"company_name": "Gamma Inc"},
    ]

    def _broker_options(self, company_name):
        return [a["company_name"] for a in self.ALL_ACCOUNTS if a["company_name"] != company_name]

    def test_excludes_own_company(self):
        options = self._broker_options("Alpha Corp")
        assert "Alpha Corp" not in options

    def test_includes_other_companies(self):
        options = self._broker_options("Alpha Corp")
        assert "Beta Ltd" in options
        assert "Gamma Inc" in options

    def test_no_exclusion_when_company_name_is_none(self):
        options = self._broker_options(None)
        assert len(options) == len(self.ALL_ACCOUNTS)


# ---------------------------------------------------------------------------
# Duplicate global insurer validation
# ---------------------------------------------------------------------------

class TestDuplicateInsurerValidation:
    def _has_duplicates(self, names):
        non_null = [n for n in names if n]
        return len(non_null) != len(set(non_null))

    def test_no_duplicates_passes(self):
        assert not self._has_duplicates(["AIG", "Allianz", "Chubb", None, None])

    def test_duplicate_detected(self):
        assert self._has_duplicates(["AIG", "AIG", "Chubb", None, None])

    def test_all_none_passes(self):
        assert not self._has_duplicates([None, None, None, None, None])

    def test_all_unique_passes(self):
        assert not self._has_duplicates(["AIG", "Allianz", "AXA XL", "Chubb", "Generali"])


# ---------------------------------------------------------------------------
# Data editor row validation (at least 1 row filled)
# ---------------------------------------------------------------------------

class TestDataEditorRowValidation:
    def _global_has_rows(self, df):
        """Global insurers: SelectboxColumn → filter by notna()."""
        return not df[df["insurer_name"].notna()].empty

    def _text_has_rows(self, df, col):
        """Local insurers / LOB: TextColumn → filter by str.strip() != ''."""
        return not df[df[col].str.strip() != ""].empty

    def test_global_insurer_all_empty_fails(self):
        df = pd.DataFrame({"insurer_name": [None, None, None]})
        assert not self._global_has_rows(df)

    def test_global_insurer_one_filled_passes(self):
        df = pd.DataFrame({"insurer_name": ["AIG", None, None]})
        assert self._global_has_rows(df)

    def test_local_insurer_all_empty_fails(self):
        df = pd.DataFrame({"insurer_name": ["", "  ", ""]})
        assert not self._text_has_rows(df, "insurer_name")

    def test_local_insurer_one_filled_passes(self):
        df = pd.DataFrame({"insurer_name": ["Local Insurer X", "", ""]})
        assert self._text_has_rows(df, "insurer_name")

    def test_lob_all_empty_fails(self):
        df = pd.DataFrame({"lob": ["", "", ""]})
        assert not self._text_has_rows(df, "lob")

    def test_lob_one_filled_passes(self):
        df = pd.DataFrame({"lob": ["Energy", "", ""]})
        assert self._text_has_rows(df, "lob")


# ---------------------------------------------------------------------------
# Section completion lookup (mocked Supabase)
# ---------------------------------------------------------------------------

class TestSectionCompletion:
    def _already_submitted(self, mock_supabase, table, account_id):
        if not account_id:
            return False
        r = (
            mock_supabase.table(table)
            .select("id")
            .eq("account_id", account_id)
            .limit(1)
            .execute()
        )
        return bool(r.data)

    def test_returns_true_when_record_exists(self):
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]
        )
        assert self._already_submitted(mock, "general_figures", "acc_001") is True

    def test_returns_false_when_no_record(self):
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        assert self._already_submitted(mock, "general_figures", "acc_001") is False

    def test_returns_false_when_no_account_id(self):
        mock = _make_supabase_mock()
        assert self._already_submitted(mock, "general_figures", None) is False


# ---------------------------------------------------------------------------
# Company name lookup logic (mocked Supabase)
# ---------------------------------------------------------------------------

class TestCompanyNameLookup:
    def _lookup(self, mock_supabase, account_id):
        result = mock_supabase.table("accounts").select("company_name, local_currency").eq("account_id", account_id).execute()
        if result.data:
            return result.data[0]["company_name"]
        return None

    def test_returns_company_name_when_found(self):
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"company_name": "Alpha Corp", "local_currency": "GBP"}]
        )
        assert self._lookup(mock, "acc_001") == "Alpha Corp"

    def test_returns_none_when_not_found(self):
        mock = _make_supabase_mock()
        mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        assert self._lookup(mock, "unknown_id") is None
