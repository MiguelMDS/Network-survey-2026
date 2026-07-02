import streamlit as st
import pandas as pd
import base64
import logging
from urllib.parse import quote
from pathlib import Path
from supabase import create_client, Client

st.set_page_config(page_title="Network Survey 2026", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

BUSINESS_INDICATORS_TABLE = "business_indicators"
INSURER_BUSINESS_TABLE = "insurer_business"
INSURER_BUSINESS_LOCAL_TABLE = "insurer_business_local"
LOB_TABLE = "lob_data"
SPECIALTY_TABLE = "specialty_capacity_items"
NETWORK_VALUE_TABLE = "network_value_collaboration"
SUPPORTING_DOCS_TABLE = "supporting_documents"
ACCOUNTS_TABLE = "accounts"

INDUSTRY_OPTIONS = [
    "Energy, Utilities & Natural Resources",
    "Industrials & Manufacturing",
    "Aviation & Space",
    "Construction & Real Estate",
    "Consumer, Retail & Hospitality",
    "Healthcare & Life Sciences",
    "Financial Services",
    "Technology",
    "Telecoms, Media & Entertainment",
    "Professional & Business Services",
    "Public Sector, Education & NGO",
    "Transportation",
    "Other",
]

LOB_OPTIONS = [
    "Property",
    "Liability",
    "Motor",
    "Marine",
    "Engineering / Construction",
    "Energy",
    "Financial Lines",
    "Cyber",
    "Life",
    "Health",
    "Disability",
    "Employee Benefits",
    "Other",
]

QUALITY_OPTIONS = [
    "1 – Poor",
    "2 – Below Average",
    "3 – Average",
    "4 – Good",
    "5 – Excellent",
]

BARRIER_OPTIONS = {
    "Internal": [
        "Technology / digital capabilities",
        "Human resources / talent",
        "Internal processes & efficiency",
    ],
    "External / Market": [
        "Limited underwriting appetite",
        "Insufficient capacity",
        "Pricing pressure",
        "Service limitations from insurers",
        "Gaps in available products / solutions",
        "Regulatory / compliance constraints",
    ],
}


logger = logging.getLogger("network_survey_2026")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _normalize_query_param(value):
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


DEBUG_MODE = str(st.query_params.get("debug", "")).strip().lower() in {"1", "true", "yes", "y", "on"}


def _debug_log(message):
    logger.info(message)
    if DEBUG_MODE:
        st.sidebar.caption(message)


def write_to_supabase(table, records):
    try:
        return supabase.table(table).insert(records).execute()
    except Exception as exception:
        return exception


def quality_to_int(quality_str):
    try:
        return int(str(quality_str)[0])
    except (ValueError, TypeError, IndexError):
        return None


def _already_submitted(table, account_id):
    if not account_id:
        return False
    try:
        r = (
            supabase.table(table)
            .select("id")
            .eq("account_id", account_id)
            .limit(1)
            .execute()
        )
        return bool(r.data)
    except Exception:
        return False


def _get_saved_currency(account_id):
    if not account_id:
        return None
    try:
        r = (
            supabase.table(BUSINESS_INDICATORS_TABLE)
            .select("currency_id, currency")
            .eq("account_id", account_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not r.data:
            return None
        row = r.data[0]
        return row.get("currency_id") or row.get("currency")
    except Exception:
        return None


def _load_global_insurers():
    try:
        insurers_result = (
            supabase.table("insurers")
            .select("insurer_name")
            .order("insurer_name")
            .execute()
        )
        insurers = [r["insurer_name"] for r in insurers_result.data if r["insurer_name"]]
        _debug_log(f"Insurers loaded: {len(insurers)}")
        return insurers
    except Exception as e:
        _debug_log(f"Error loading insurers: {e}")
        return []


def _normalize_other(choice, other_text):
    if choice == "Other":
        return (other_text or "").strip()
    return (choice or "").strip()


def _industry_picker(prefix, label, options):
    c1, c2 = st.columns([2, 3])
    with c1:
        choice = st.selectbox(
            label,
            options=options,
            index=None,
            placeholder="Select an option",
            key=f"{prefix}_choice",
        )
    with c2:
        other_text = ""
        if choice == "Other":
            other_text = st.text_input("If Other, please specify", key=f"{prefix}_other")
    return choice, other_text


def _parse_non_negative_float(raw_value):
    txt = str(raw_value or "").strip()
    if not txt:
        return 0.0
    txt = txt.replace(",", ".")
    value = float(txt)
    if value < 0:
        raise ValueError("Value must be non-negative")
    return value


def _logo_data_uri(logo_filename="logo.svg"):
    try:
        logo_path = Path(__file__).resolve().parent / logo_filename
        if not logo_path.exists():
            return None
        encoded = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
        return f"data:image/svg+xml;base64,{encoded}"
    except Exception:
        return None

st.divider()
st.title("Network Survey 2026")
st.caption("Thank you for participating in the Brokerslink Network Survey.")
st.markdown(
    """
This survey covers your company's activity during 2025. It should take approximately 12–15 minutes to complete.

Your responses will help us update our network data, understand member capabilities and priorities, and improve the value Brokerslink delivers globally. They will also support internal reporting and aggregated market intelligence.

All individual company data is treated as strictly confidential. Any external use will be based solely on aggregated and anonymised insights, unless expressly agreed otherwise with you.
"""
)

# Disable column-header interactions on all grid tables (prevents sorting by click).
toolbar_logo = _logo_data_uri() or "https://www.brokerslink.com/themes/custom/ga_client/logo.svg"
st.markdown(
    """
<style>
div[data-testid="stDataFrame"] thead th,
div[data-testid="stDataEditor"] thead th,
div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataEditor"] [role="columnheader"] {
    pointer-events: none !important;
}
div[data-testid="stCaptionContainer"],
div[data-testid="stCaptionContainer"] p {
    color: #000000 !important;
}
div[data-testid="stDataFrame"] [role="toolbar"],
div[data-testid="stDataEditor"] [role="toolbar"] {
    display: none !important;
}
div[data-testid="stDataFrameToolbar"],
div[data-testid="stDataEditorToolbar"],
div[data-testid="stElementToolbar"] {
    display: none !important;
}
div[data-testid="stDataFrame"] button[aria-label*="Show/hide"],
div[data-testid="stDataEditor"] button[aria-label*="Show/hide"],
div[data-testid="stDataFrame"] button[title*="Show/hide"],
div[data-testid="stDataEditor"] button[title*="Show/hide"] {
    display: none !important;
}
div[data-testid="stDataFrame"] {
    overflow-x: auto !important;
}
div[data-testid="stDataEditor"] {
    overflow-x: auto !important;
}
div[data-testid="stDataFrame"] ::-webkit-scrollbar,
div[data-testid="stDataEditor"] ::-webkit-scrollbar {
    height: 12px;
}
div[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb,
div[data-testid="stDataEditor"] ::-webkit-scrollbar-thumb {
    background: #b0b0b0;
    border-radius: 8px;
}
/* Brokerslink logo in Streamlit toolbar */
div[data-testid="stToolbar"],
.st-emotion-cache-14vh5up.e1yxiy6j2 {
    position: relative;
    min-height: 44px;
}

div[data-testid="stToolbar"]::before,
.st-emotion-cache-14vh5up.e1yxiy6j2::before {
    content: "";
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    width: 145px;
    height: 28px;
    background-image: url("__TOOLBAR_LOGO__");
    background-repeat: no-repeat;
    background-size: contain;
    background-position: left center;
    pointer-events: none;
}

div[data-testid="stToolbar"] > * {
    margin-left: 155px;
}
</style>
""".replace("__TOOLBAR_LOGO__", toolbar_logo),
    unsafe_allow_html=True,
)

query_params_snapshot = dict(st.query_params)
_debug_log(f"Query params keys: {list(query_params_snapshot.keys())}")

account_id_raw = st.query_params.get(
    "accountid",
    st.query_params.get("account_id", st.query_params.get("accountId", None)),
)
account_id = _normalize_query_param(account_id_raw)
_debug_log(f"Resolved account_id from URL: {account_id!r}")
company_name = None
local_currency_code = None
account_type = None

if account_id:
    _debug_log(f"Searching account_id={account_id!r} (len={len(account_id)})")
    try:
        result = (
            supabase.table(ACCOUNTS_TABLE)
            .select("company_name, local_currency, type")
            .eq("account_id", account_id)
            .execute()
        )
        _debug_log(f"Accounts exact-match rows: {len(result.data or [])}")

        if (not result.data) and account_id.lower() != account_id:
            lower_account_id = account_id.lower()
            _debug_log(f"Retrying account lookup with lowercase account_id={lower_account_id!r}")
            result = (
                supabase.table(ACCOUNTS_TABLE)
                .select("company_name, local_currency, type")
                .eq("account_id", lower_account_id)
                .execute()
            )
            _debug_log(f"Accounts lowercase rows: {len(result.data or [])}")
            if result.data:
                account_id = lower_account_id

        if result.data:
            company_name = result.data[0]["company_name"]
            local_currency_code = result.data[0].get("local_currency") or None
            account_type = result.data[0].get("type") or None
            _debug_log(
                f"Account resolved: company={company_name!r}, local_currency={local_currency_code!r}, type={account_type!r}"
            )
        else:
            st.warning(f"Account ID '{account_id}' not found in the system.")
    except Exception as e:
        st.error(f"Error loading account '{account_id}': {e}")
        _debug_log(f"Error loading account details: {e}")
else:
    st.warning("No account ID in URL. Add `?accountid=...` to the address bar.")

is_specialist_broker = account_type == "Specialist Broker"

if company_name:
    st.subheader(company_name)

business_done = _already_submitted(BUSINESS_INDICATORS_TABLE, account_id)
insurer_done = _already_submitted(INSURER_BUSINESS_TABLE, account_id)
specialty_done = _already_submitted(SPECIALTY_TABLE, account_id)
network_done = _already_submitted(NETWORK_VALUE_TABLE, account_id)
supporting_done = _already_submitted(SUPPORTING_DOCS_TABLE, account_id)
all_sections_done = business_done and insurer_done and specialty_done and network_done and supporting_done
currency_locked = business_done



st.caption("⚑ Before you begin — select your reporting currency")
st.caption("All financial figures in this survey should be reported in the same currency. Please tick one:")
# Temporary restriction requested: only USD and EUR.
currency_options = ["USD", "EUR"]

saved_currency = _get_saved_currency(account_id)
default_currency = saved_currency if saved_currency in currency_options else "USD"

currency = st.pills(
    "Currency",
    options=currency_options,
    selection_mode="single",
    default=default_currency,
    key="currency",
    disabled=currency_locked,
)
if not currency:
    currency = default_currency

if currency == "USD":
    amount_format = "dollar"
elif currency == "EUR":
    amount_format = "euro"
else:
    amount_format = "accounting"



if currency_locked:
    st.caption("🔒 Currency is locked after submitting section 1.")

global_insurers = _load_global_insurers()
try:
    all_accounts = supabase.table(ACCOUNTS_TABLE).select("company_name").execute().data or []
    _debug_log(f"Accounts for broker options loaded: {len(all_accounts)}")
except Exception as e:
    all_accounts = []
    _debug_log(f"Error loading accounts for broker options: {e}")
broker_options = [
    a["company_name"] for a in all_accounts if a["company_name"] and a["company_name"] != company_name
]
broker_options.sort()
_debug_log(f"Broker options prepared: {len(broker_options)}")
st.divider()
if business_done:
    st.success("1. COMPANY PROFILE & BUSINESS INDICATORS — 2025 — ALREADY SUBMITTED ✓")
else:
    st.header("1. COMPANY PROFILE & BUSINESS INDICATORS — 2025")
    st.caption("Please report figures for the full calendar year 2025. Use the selected currency throughout the survey.")

    st.subheader("1.1 Total GWP & Revenue")
    total_gwp_2025_input = st.text_input("Total Gross Written Premium (GWP) — 2025", placeholder="0.00")
    total_revenue_2025_input = st.text_input("Total Revenue (commissions + fees) — 2025", placeholder="0.00")

    if is_specialist_broker:
        st.info("For Specialist Broker accounts, market ranking and section 1.2 are not required.")
        pct_eb = 0.0
        pct_pc = 0.0
        pct_trade_credit = 0.0
        pct_financial_lines = 0.0
        pct_other = 0.0
    else:
        st.subheader("1.2 GWP Breakdown by Line of Business")
        st.caption("Enter the percentage of your total GWP for each line of business. The total must add up to 100%.")
        pct_eb = st.number_input("Employee Benefits", min_value=0.0, max_value=100.0, step=5.0)
        pct_pc = st.number_input("Property & Casualty (P&C)", min_value=0.0, max_value=100.0, step=5.0)
        pct_trade_credit = st.number_input("Trade Credit", min_value=0.0, max_value=100.0, step=5.0)
        pct_financial_lines = st.number_input("Financial Lines (D&O, PI, Cyber, etc.)", min_value=0.0, max_value=100.0, step=5.0)
        pct_other = st.number_input("Other", min_value=0.0, max_value=100.0, step=1.0)

    st.subheader("1.3 Company Size & Market Position")
    number_of_employees = st.number_input("Number of employees", min_value=0, step=1, format="%d")
    market_position_choice = None
    market_position_other = ""
    if not is_specialist_broker:
        ranking_options = [
            "1st",
            "2nd",
            "3rd",
            "Top 5",
            "Top 10",
            "Top 20",
            "Not ranked / Unknown",
            "Other",
        ]
        market_position_choice = st.selectbox(
            "Your position in the brokerage market ranking in your country",
            options=ranking_options,
            index=None,
            placeholder="Select a category",
        )
        if market_position_choice == "Other":
            market_position_other = st.text_input("If Other, please specify")

    st.subheader("1.4 Top 3 Client Industries by Premium Volume")
    st.caption("List the three industries that generate the most premium volume for your company (e.g. Manufacturing, Real Estate, Healthcare).")
    ind_1, ind_1_other = _industry_picker("top_industry_1", "1st", INDUSTRY_OPTIONS)
    ind_2, ind_2_other = _industry_picker("top_industry_2", "2nd", INDUSTRY_OPTIONS)
    ind_3, ind_3_other = _industry_picker("top_industry_3", "3rd", INDUSTRY_OPTIONS)

    st.subheader("1.5 Top 3 Areas of Expertise")
    st.caption("What are the three areas where your company has the deepest knowledge and strongest capabilities? (e.g. Risk Engineering, Marine, Cyber, Employee Benefits)")
    expertise_1 = st.text_input("1st area of expertise")
    expertise_2 = st.text_input("2nd area of expertise")
    expertise_3 = st.text_input("3rd area of expertise")

    if st.button("Submit business indicators"):
        pct_total = round(pct_eb + pct_pc + pct_trade_credit + pct_financial_lines + pct_other, 4)
        try:
            total_gwp_2025 = _parse_non_negative_float(total_gwp_2025_input)
            total_revenue_2025 = _parse_non_negative_float(total_revenue_2025_input)
        except ValueError:
            st.error("In section 1.1, Total GWP and Total Revenue must be valid non-negative numbers.")
            st.stop()
        industries = [
            _normalize_other(ind_1, ind_1_other),
            _normalize_other(ind_2, ind_2_other),
            _normalize_other(ind_3, ind_3_other),
        ]
        if is_specialist_broker:
            market_position_ranking = None
        elif market_position_choice == "Other":
            market_position_ranking = market_position_other.strip()
        else:
            market_position_ranking = market_position_choice
        if (not is_specialist_broker) and abs(pct_total - 100.0) > 0.01:
            st.error(f"The percentage breakdown must total 100%. Current total: {pct_total}%")
        elif (not is_specialist_broker) and (not market_position_ranking):
            st.error("Please select your brokerage market ranking position in section 1.3.")
        elif (
            (ind_1 == "Other" and not industries[0])
            or (ind_2 == "Other" and not industries[1])
            or (ind_3 == "Other" and not industries[2])
        ):
            st.error("When choosing 'Other' in 1.4, please provide free text.")
        else:
            payload = {
                "account_id": account_id,
                "currency_id": currency,
                "currency": currency,
                "total_gwp": total_gwp_2025,
                "total_revenue": total_revenue_2025,
                "number_of_employees": int(number_of_employees),
                "market_ranking_position": market_position_ranking,
                "pct_employee_benefits": pct_eb,
                "pct_property_casualty": pct_pc,
                "pct_trade_credit": pct_trade_credit,
                "pct_financial_lines": pct_financial_lines,
                "pct_other": pct_other,
                "top_industries": [x for x in industries if x],
                "top_expertise_areas": [x.strip() for x in [expertise_1, expertise_2, expertise_3] if x.strip()],
            }
            result_insert = write_to_supabase(BUSINESS_INDICATORS_TABLE, [payload])
            if isinstance(result_insert, Exception):
                st.error(f"Failed to save business indicators: {result_insert}")
            else:
                st.success("Business indicators saved.")
                st.rerun()
st.divider()
if insurer_done:
    st.success("2. INSURER RELATIONSHIPS — ALREADY SUBMITTED ✓")
else:
    st.header("2. INSURER RELATIONSHIPS")
    st.caption("Rate each insurer on a scale of 1 to 5: 1 = Poor | 2 = Below Average | 3 = Average | 4 = Good | 5 = Excellent")

    df_global_insurers_data = {
        "insurer_name": [None] * 5,
        "gwp_total": [0.0] * 5,
        "quality_claims_service": [None] * 5,
        "quality_underwriting_responsiveness": [None] * 5,
        "quality_financial_strength": [None] * 5,
    }
    df_local_insurers_data = {
        "insurer_name": [""] * 3,
        "gwp_total": [0.0] * 3,
        "quality_claims_service": [None] * 3,
        "quality_underwriting_responsiveness": [None] * 3,
        "quality_financial_strength": [None] * 3,
    }
    if not is_specialist_broker:
        df_global_insurers_data["gwp_pc"] = [0.0] * 5
        df_local_insurers_data["gwp_pc"] = [0.0] * 3
        df_global_insurers_data["gwp_eb"] = [0.0] * 5
        df_local_insurers_data["gwp_eb"] = [0.0] * 3

    df_global_insurers = pd.DataFrame(df_global_insurers_data)
    df_local_insurers = pd.DataFrame(df_local_insurers_data)
    if not is_specialist_broker:
        global_column_order = [
            "insurer_name",
            "gwp_total",
            "gwp_eb",
            "gwp_pc",
            "quality_claims_service",
            "quality_underwriting_responsiveness",
            "quality_financial_strength",
        ]
        local_column_order = [
            "insurer_name",
            "gwp_total",
            "gwp_eb",
            "gwp_pc",
            "quality_claims_service",
            "quality_underwriting_responsiveness",
            "quality_financial_strength",
        ]
        df_global_insurers = df_global_insurers[global_column_order]
        df_local_insurers = df_local_insurers[local_column_order]

    st.subheader("2.1 Top 5 Global Insurers (by GWP placed with them)")
    global_column_config = {
        "insurer_name": st.column_config.SelectboxColumn("Insurer", options=global_insurers, required=False),
        "gwp_total": st.column_config.NumberColumn(f"TOTAL ({currency})", format=amount_format, min_value=0),
        "quality_claims_service": st.column_config.SelectboxColumn("Claims Service", options=QUALITY_OPTIONS, required=False),
        "quality_underwriting_responsiveness": st.column_config.SelectboxColumn("Underwriting & Responsiveness", options=QUALITY_OPTIONS, required=False),
        "quality_financial_strength": st.column_config.SelectboxColumn("Financial Strength", options=QUALITY_OPTIONS, required=False),
    }
    if not is_specialist_broker:
        global_column_config["gwp_eb"] = st.column_config.NumberColumn(f"EB ({currency})", format=amount_format, min_value=0)
        global_column_config["gwp_pc"] = st.column_config.NumberColumn(f"P&C ({currency})", format=amount_format, min_value=0)

    edited_global = st.data_editor(
        df_global_insurers,
        column_config=global_column_config,
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        key="edited_global_insurers",
    )

    st.subheader("2.2 Top 3 Local / Domestic Insurers (by GWP placed with them)")
    local_column_config = {
        "insurer_name": st.column_config.TextColumn("Insurer", required=False),
        "gwp_total": st.column_config.NumberColumn(f"TOTAL ({currency})", format=amount_format, min_value=0),
        "quality_claims_service": st.column_config.SelectboxColumn("Claims Service", options=QUALITY_OPTIONS, required=False),
        "quality_underwriting_responsiveness": st.column_config.SelectboxColumn("Underwriting & Responsiveness", options=QUALITY_OPTIONS, required=False),
        "quality_financial_strength": st.column_config.SelectboxColumn("Financial Strength", options=QUALITY_OPTIONS, required=False),
    }
    if not is_specialist_broker:
        local_column_config["gwp_eb"] = st.column_config.NumberColumn(f"EB ({currency})", format=amount_format, min_value=0)
        local_column_config["gwp_pc"] = st.column_config.NumberColumn(f"P&C ({currency})", format=amount_format, min_value=0)

    edited_local = st.data_editor(
        df_local_insurers,
        column_config=local_column_config,
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        key="edited_local_insurers",
    )

    edited_lob_23 = None
    if is_specialist_broker:
        st.info("Section 2.3 (Top 3 Lines of Business) is not required for Specialist Broker accounts.")
    else:
        st.subheader("2.3 Top 3 Lines of Business by GWP Amount")
        st.caption("Use 'If Other, please specify' only when Line of Business = Other.")
        edited_lob_23 = st.data_editor(
            pd.DataFrame(
                {
                    "line_of_business": [None] * 3,
                    "if_other_please_specify": [""] * 3,
                    "gwp_amount": [None] * 3,
                }
            ),
            column_config={
                "line_of_business": st.column_config.SelectboxColumn("Line of Business", options=LOB_OPTIONS, required=False),
                "if_other_please_specify": st.column_config.TextColumn("If Other, please specify", required=False),
                "gwp_amount": st.column_config.NumberColumn(f"GWP Amount ({currency})", min_value=0.01, step=1000.0, format="%0.2f", required=False),
            },
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            key="edited_lob_23",
        )

    disable_insurer_submit = False
    if (not is_specialist_broker) and edited_lob_23 is not None:
        invalid_if_other_live = edited_lob_23.apply(
            lambda row: (row.get("line_of_business") != "Other") and bool((row.get("if_other_please_specify") or "").strip()),
            axis=1,
        )
        if invalid_if_other_live.any():
            st.warning("In 2.3, 'If Other, please specify' can only be filled when Line of Business is 'Other'.")
            disable_insurer_submit = True

    if st.button("Submit insurer & LOB overview", disabled=disable_insurer_submit):
        global_records = edited_global[edited_global["insurer_name"].notna()].copy()
        local_records = edited_local[edited_local["insurer_name"].str.strip() != ""].copy()

        if global_records.empty:
            st.error("Please fill in at least one row in 2.1 Top 5 insurers by GWP.")
        elif local_records.empty:
            st.error("Please fill in at least one row in 2.2 Local insurers.")
        elif global_records["insurer_name"].duplicated().any():
            st.error("Each global insurer can only appear once. Please remove duplicates.")
        else:
            lob_records = []
            lob_validation_error = None
            if not is_specialist_broker:
                for _, row in edited_lob_23.iterrows():
                    lob_choice = row.get("line_of_business")
                    lob_other = (row.get("if_other_please_specify") or "").strip()
                    lob_gwp = row.get("gwp_amount")

                    has_any = bool(lob_choice) or bool(lob_other) or pd.notna(lob_gwp)
                    if not has_any:
                        continue

                    if not lob_choice:
                        lob_validation_error = "For 2.3, each filled row must include a Line of Business."
                        break
                    if lob_choice != "Other" and lob_other:
                        lob_validation_error = "For 2.3, 'If Other, please specify' can only be filled when Line of Business is 'Other'."
                        break
                    if pd.isna(lob_gwp) or float(lob_gwp) <= 0:
                        lob_validation_error = "For 2.3, GWP Amount must be greater than zero."
                        break

                    final_lob = _normalize_other(lob_choice, lob_other)
                    if lob_choice == "Other" and not final_lob:
                        lob_validation_error = "For 2.3, when selecting 'Other', please provide free text."
                        break

                    lob_records.append({"account_id": account_id, "lob": final_lob, "gwp": float(lob_gwp)})

            if lob_validation_error:
                st.error(lob_validation_error)
            elif (not is_specialist_broker) and (not lob_records):
                st.error("Please fill in at least one line of business in 2.3.")
            else:
                global_records["quality_claims_service"] = global_records["quality_claims_service"].apply(quality_to_int)
                global_records["quality_underwriting_responsiveness"] = global_records["quality_underwriting_responsiveness"].apply(quality_to_int)
                global_records["quality_financial_strength"] = global_records["quality_financial_strength"].apply(quality_to_int)
                global_records["account_id"] = account_id

                local_records["quality_claims_service"] = local_records["quality_claims_service"].apply(quality_to_int)
                local_records["quality_underwriting_responsiveness"] = local_records["quality_underwriting_responsiveness"].apply(quality_to_int)
                local_records["quality_financial_strength"] = local_records["quality_financial_strength"].apply(quality_to_int)
                local_records["account_id"] = account_id

                result_global = write_to_supabase(INSURER_BUSINESS_TABLE, global_records.to_dict("records"))
                result_local = write_to_supabase(INSURER_BUSINESS_LOCAL_TABLE, local_records.to_dict("records"))
                if is_specialist_broker:
                    result_lob = True
                else:
                    result_lob = write_to_supabase(LOB_TABLE, lob_records)

                has_error = False
                if isinstance(result_global, Exception):
                    has_error = True
                    st.error(f"Failed saving 2.1 Top insurers: {result_global}")
                if isinstance(result_local, Exception):
                    has_error = True
                    st.error(f"Failed saving 2.2 Local insurers: {result_local}")
                if isinstance(result_lob, Exception):
                    has_error = True
                    st.error(f"Failed saving 2.3 Lines of business: {result_lob}")

                if not has_error:
                    st.success("Insurer & line of business overview saved.")
                    st.rerun()
st.divider()
if specialty_done:
    st.success("3. SPECIALTY CAPACITY — ALREADY SUBMITTED ✓")
else:
    st.header("3. SPECIALTY CAPACITY — FACILITIES & MGAS")

    uses_mgas = st.radio(
        "Does your company currently use any facilities and/or Managing General Agents (MGAs)?",
        options=["Yes", "No"],
        index=None,
        key="specialty_uses_mgas",
    )

    edited_specialty = None
    if uses_mgas == "Yes":
        st.caption("If YES, please list the facilities and/or MGAs you use and the approximate annual GWP placed through each.")
        edited_specialty = st.data_editor(
            pd.DataFrame({"facility_mga_name": [""] * 3, "approx_annual_gwp": [None] * 3}),
            column_config={
                "facility_mga_name": st.column_config.TextColumn("Facility / MGA Name", required=False),
                "approx_annual_gwp": st.column_config.NumberColumn(f"Approx. Annual GWP ({currency})", min_value=0.01, step=1000.0, format="%0.2f", required=False),
            },
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            key="specialty_editor",
        )

    if st.button("Submit specialty capacity"):
        if uses_mgas is None:
            st.error("Please choose Yes or No.")
        else:
            specialty_items_records = []
            if uses_mgas == "Yes":
                for _, row in edited_specialty.iterrows():
                    name = (row.get("facility_mga_name") or "").strip()
                    gwp_val = row.get("approx_annual_gwp")
                    has_any = bool(name) or pd.notna(gwp_val)
                    if not has_any:
                        continue
                    if not name:
                        st.error("Section 3: every filled row needs a Facility / MGA Name.")
                        st.stop()
                    if pd.isna(gwp_val) or float(gwp_val) <= 0:
                        st.error("Section 3: Approx. Annual GWP must be greater than zero.")
                        st.stop()
                    specialty_items_records.append(
                        {
                            "account_id": account_id,
                            "uses_facilities_mgas": True,
                            "facility_mga_name": name,
                            "approx_annual_gwp": float(gwp_val),
                        }
                    )

                if not specialty_items_records:
                    st.error("Please add at least one Facility / MGA row in section 3.")
                    st.stop()

            else:
                # Register explicit "No" answer in items table so section appears as submitted.
                specialty_items_records.append(
                    {
                        "account_id": account_id,
                        "uses_facilities_mgas": False,
                        "facility_mga_name": None,
                        "approx_annual_gwp": None,
                    }
                )

            result_specialty_items = write_to_supabase(SPECIALTY_TABLE, specialty_items_records)
            if isinstance(result_specialty_items, Exception):
                st.error(f"Failed to save specialty capacity: {result_specialty_items}")
            else:
                st.success("Specialty capacity saved.")
                st.rerun()
st.divider()
if network_done:
    st.success("4. BROKERSLINK NETWORK — COLLABORATION & GROWTH — ALREADY SUBMITTED ✓")
else:
    st.header("4. BROKERSLINK NETWORK — COLLABORATION & GROWTH")

    st.subheader("4.1 Top 3 Network brokers/companies — Most Business Collaboration in 2025")
    st.caption("Which Brokerslink member companies did you collaborate with most during 2025? List them in order.")
    top1 = st.selectbox("1st", options=broker_options, index=None, placeholder="Select broker/company")
    top2 = st.selectbox("2nd", options=broker_options, index=None, placeholder="Select broker/company")
    top3 = st.selectbox("3rd", options=broker_options, index=None, placeholder="Select broker/company")
    additional_info = st.text_area("Additional details (optional): e.g. type of business, countries involved, outcome", height=100)

    st.subheader("4.2 How Can Collaboration Be Improved?")
    st.caption("Please share your thoughts on what could make collaboration between Brokerslink members more effective — consider communication tools, joint business development, events, and knowledge sharing.")
    collaboration_improvements = st.text_area("Collaboration improvements", height=120)

    st.subheader("4.3 Top 3 Client Industries with the Highest Growth in Demand by 2026")
    st.caption("Which industries do you expect to see the strongest increase in insurance demand from your clients in 2026?")
    growth_1, growth_1_other = _industry_picker("growth_1", "1st", INDUSTRY_OPTIONS)
    growth_2, growth_2_other = _industry_picker("growth_2", "2nd", INDUSTRY_OPTIONS)
    growth_3, growth_3_other = _industry_picker("growth_3", "3rd", INDUSTRY_OPTIONS)

    st.subheader("4.4 Top 3 Client Industries with the Largest Capacity Gaps")
    st.caption("Where is it hardest to find sufficient insurance capacity for your clients? List the industries where risk capacity is most limited.")
    gap_1, gap_1_other = _industry_picker("gap_1", "1st", INDUSTRY_OPTIONS)
    gap_2, gap_2_other = _industry_picker("gap_2", "2nd", INDUSTRY_OPTIONS)
    gap_3, gap_3_other = _industry_picker("gap_3", "3rd", INDUSTRY_OPTIONS)

    st.subheader("4.5 Main Barriers to Growth")
    st.caption("Please tick all factors that currently limit your company's growth. You may select multiple options.")
    selected_barriers = []
    st.markdown("**Internal Barriers**")
    for opt in BARRIER_OPTIONS["Internal"]:
        if st.checkbox(opt, key=f"barrier_internal_{opt}"):
            selected_barriers.append(opt)
    other_internal_selected = st.checkbox("Other internal barrier", key="barrier_internal_other_selected")
    if other_internal_selected:
        other_internal_barrier = st.text_input("Specify other internal barrier")
        if other_internal_barrier.strip():
            selected_barriers.append(f"Other internal barrier: {other_internal_barrier.strip()}")

    st.markdown("**External / Market Barriers**")
    for opt in BARRIER_OPTIONS["External / Market"]:
        if st.checkbox(opt, key=f"barrier_external_{opt}"):
            selected_barriers.append(opt)
    other_external_selected = st.checkbox("Other external barrier", key="barrier_external_other_selected")
    if other_external_selected:
        other_external_barrier = st.text_input("Specify other external barrier")
        if other_external_barrier.strip():
            selected_barriers.append(f"Other external barrier: {other_external_barrier.strip()}")

    if st.button("Submit collaboration section"):
        top_brokers = [x for x in [top1, top2, top3] if x]
        growth_values = [
            _normalize_other(growth_1, growth_1_other),
            _normalize_other(growth_2, growth_2_other),
            _normalize_other(growth_3, growth_3_other),
        ]
        gap_values = [
            _normalize_other(gap_1, gap_1_other),
            _normalize_other(gap_2, gap_2_other),
            _normalize_other(gap_3, gap_3_other),
        ]

        if len(top_brokers) == 0:
            st.error("Please select at least one broker/company in section 4.1.")
        elif len(set(top_brokers)) != len(top_brokers):
            st.error("Please avoid duplicate brokers/companies in section 4.1.")
        elif (
            (growth_1 == "Other" and not growth_values[0])
            or (growth_2 == "Other" and not growth_values[1])
            or (growth_3 == "Other" and not growth_values[2])
            or (gap_1 == "Other" and not gap_values[0])
            or (gap_2 == "Other" and not gap_values[1])
            or (gap_3 == "Other" and not gap_values[2])
        ):
            st.error("Whenever 'Other' is selected in 4.3/4.4, please provide free text.")
        elif other_internal_selected and not any(x.startswith("Other internal barrier:") for x in selected_barriers):
            st.error("Please specify the other internal barrier.")
        elif other_external_selected and not any(x.startswith("Other external barrier:") for x in selected_barriers):
            st.error("Please specify the other external barrier.")
        else:
            payload = {
                "account_id": account_id,
                "top_collaboration_brokers": top_brokers,
                "additional_information": additional_info,
                "collaboration_improvements": collaboration_improvements,
                "top_growth_industries_2026": growth_values,
                "top_risk_capacity_gap_industries": gap_values,
                "main_growth_barriers": selected_barriers,
            }
            result_network = write_to_supabase(NETWORK_VALUE_TABLE, [payload])
            if isinstance(result_network, Exception):
                st.error(f"Failed to save section 4: {result_network}")
            else:
                st.success("Section 4 saved.")
                st.rerun()
st.divider()
if supporting_done:
    st.success("5. SUPPORTING DOCUMENTS (OPTIONAL) — ALREADY SUBMITTED ✓")
else:
    st.header("5. SUPPORTING DOCUMENTS (OPTIONAL)")
    st.caption("If you have any additional material that would help us better understand your business — such as annual reports, market presentations, or data files — please attach them or share a link below. This is entirely optional.")

    st.caption("Accepted formats: XLSX, CSV, PDF · Maximum 4 MB per file")
    file_link = st.text_input("File name or link")
    uploaded_file = st.file_uploader("Upload file", type=["xlsx", "csv", "pdf"])
    additional_comments = st.text_area("Additional Comments")

    if st.button("Submit supporting documents"):
        uploaded_file_name = None
        uploaded_file_path = None

        if uploaded_file is not None:
            file_size = len(uploaded_file.getvalue())
            max_size = 4 * 1024 * 1024
            if file_size > max_size:
                st.error("File exceeds 4 MB. Please upload a smaller file.")
                st.stop()
            try:
                uploaded_file_path = f"{account_id}/{uploaded_file.name}"
                supabase.storage.from_("survey-files").upload(
                    path=uploaded_file_path,
                    file=uploaded_file.getvalue(),
                    file_options={"content-type": uploaded_file.type},
                )
                uploaded_file_name = uploaded_file.name
            except Exception as e:
                st.error(f"File upload failed: {e}")
                st.stop()

        if not uploaded_file and not file_link.strip() and not additional_comments.strip():
            st.info("No file/link/comments submitted.")
        else:
            payload = {
                "account_id": account_id,
                "file_name": uploaded_file_name,
                "file_path": uploaded_file_path,
                "file_link": file_link.strip(),
                "additional_comments": additional_comments.strip(),
            }
            result_doc = write_to_supabase(SUPPORTING_DOCS_TABLE, [payload])
            if isinstance(result_doc, Exception):
                st.error(f"Failed to save supporting document metadata: {result_doc}")
            else:
                st.success("Supporting documents information saved.")
                st.rerun()

all_sections_done = business_done and insurer_done and specialty_done and network_done and supporting_done
st.divider()
if all_sections_done:
    st.markdown("### Thank you for your contribution.")
    st.caption(
        "Thank you for contributing to the Brokerslink Global Survey."
        "Your responses are vital for the ongoing development of the Brokerslink ecosystem."
        "We are grateful for the time and effort you have devoted to completing this survey."
        "Once we have analysed the data you have submitted, we will contact you if we require any further clarification."
        "In the meantime, if you have any questions or would like to share additional insights, please don't hesitate to get in touch."
    )



questions_subject = quote(f"Survey 2026 Questions - {company_name or 'Unknown Company'}")
st.markdown(
        """
        <div style="padding: 0.25rem 0 1rem 0;">
            <div style="display:flex; gap:1rem; align-items:center; flex-wrap:wrap; margin-bottom:0.5rem;">
                <a href="mailto:miguel.gomes@mdsgroup.com?cc=allan.rocha@mdsgroup.com&subject=__QUESTIONS_SUBJECT__" style="text-decoration:none;">Questions</a>
            </div>
            <div style="font-size:0.9rem; opacity:0.85; margin-bottom:0.25rem;">
                Brokerslink AG, c/o MJP Partners AG, Bahnhofstrasse 20, 6300 Zug-Switzerland
            </div>
            <div style="font-size:0.85rem; opacity:0.8;">
                © COPYRIGHT 2026 BROKERSLINK. ALL RIGHTS RESERVED
            </div>
        </div>
        """.replace("__QUESTIONS_SUBJECT__", questions_subject),
        unsafe_allow_html=True,
)

