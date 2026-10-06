"""Build primary financial statements from SEC Financial Statement Data Sets."""

from __future__ import annotations

import re
from collections.abc import Mapping

import pandas as pd


STATEMENT_NAMES = ("balance_sheet", "income_statement", "cash_flow")


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with SEC column names in lowercase.

    >>> _normalize_columns(pd.DataFrame({"CIK": [1]})).columns.tolist()
    ['cik']
    """
    result = frame.copy()
    result.columns = [str(column).lower() for column in result.columns]
    return result


def _normalize_cik(value: object) -> str:
    """Normalize a CIK value to its unpadded digit representation.

    >>> _normalize_cik("0000000123")
    '123'
    """
    return re.sub(r"\D", "", str(value)).lstrip("0") or "0"


def select_latest_filing(submissions: pd.DataFrame, cik: int | str) -> pd.Series:
    """Select the latest 10-K or 10-Q row for a CIK, ordered by filing date.

    >>> filings = pd.DataFrame({"cik": [1, 1], "form": ["10-K", "10-Q"], "filed": ["2024-02-01", "2024-05-01"], "adsh": ["a", "b"]})
    >>> select_latest_filing(filings, "0000000001")["form"]
    '10-Q'
    """
    submissions = _normalize_columns(submissions)
    required = {"cik", "form", "filed", "adsh"}
    missing = required.difference(submissions.columns)
    if missing:
        raise ValueError(f"SUB table is missing required columns: {sorted(missing)}")

    matches = submissions.loc[
        submissions["cik"].map(_normalize_cik).eq(_normalize_cik(cik))
        & submissions["form"].isin(["10-K", "10-Q"])
    ].copy()
    if matches.empty:
        raise ValueError(f"No 10-K or 10-Q filing found for CIK {cik}")
    matches["filed"] = pd.to_datetime(matches["filed"], errors="coerce")
    matches = matches.dropna(subset=["filed"]).sort_values(["filed", "adsh"])
    if matches.empty:
        raise ValueError(f"No valid filing date found for CIK {cik}")
    return matches.iloc[-1]


def _statement_for_fact(tag: str, label: str, quarters: int) -> str | None:
    """Classify a primary statement fact using duration and concept wording.

    >>> _statement_for_fact("Assets", "Total assets", 0)
    'balance_sheet'
    >>> _statement_for_fact("NetCashProvidedByUsedInOperatingActivities", "Operating cash", 1)
    'cash_flow'
    """
    text = f"{tag} {label}".lower()
    cash_flow_terms = (
        "cashflow", "cash flow", "cashprovidedbyusedin", "cashprovidedfrom",
        "cashusedin", "paymentsfor", "paymentsto", "paymentsof", "proceedsfrom",
        "increase_decrease_in_cash", "increase (decrease) in cash", "effectofexchange",
        "effect of exchange", "depreciationdepletionandamortization",
        "sharebasedcompensation", "stockbasedcompensation", "increaseordecreasein",
        "increase (decrease) in accounts", "increase (decrease) in inventories",
        "increase (decrease) in operating", "repaymentsof", "repayments of",
        "issuanceof", "issuance of", "acquirepropertyplantandequipment",
        "acquire businesses", "acquisitions of businesses",
    )
    if quarters == 0:
        return "balance_sheet"
    if any(term in text for term in cash_flow_terms):
        return "cash_flow"
    return "income_statement"


def create_financial_statements(
    submissions: pd.DataFrame,
    numeric: pd.DataFrame,
    tags: pd.DataFrame,
    cik: int | str,
    presentation: pd.DataFrame | None = None,
) -> tuple[pd.Series, dict[str, pd.DataFrame]]:
    """Build primary statements from the latest filing for a CIK.

    Facts are restricted to the selected accession and consolidated (non-segment)
    rows. When PRE is provided, statement assignment, preferred labels, line order,
    and negating flags come from the SEC presentation table. Duration facts retain
    SEC's quarter count so quarterly and year-to-date values remain distinguishable.
    Returns the filing metadata and three tables.

    >>> subs = pd.DataFrame({"cik": [7], "form": ["10-Q"], "filed": ["2024-05-01"], "adsh": ["a"], "period": ["2024-03-31"]})
    >>> nums = pd.DataFrame({"adsh": ["a", "a"], "tag": ["Assets", "Revenues"], "version": ["us-gaap/2024", "us-gaap/2024"], "ddate": ["2024-03-31", "2024-03-31"], "qtrs": [0, 1], "uom": ["USD", "USD"], "value": [100, 50], "segments": ["", ""]})
    >>> tag_data = pd.DataFrame({"tag": ["Assets", "Revenues"], "version": ["us-gaap/2024", "us-gaap/2024"], "tlabel": ["Assets", "Revenue"]})
    >>> filing, tables = create_financial_statements(subs, nums, tag_data, 7)
    >>> (filing["adsh"], len(tables["balance_sheet"]), len(tables["income_statement"]))
    ('a', 1, 1)
    """
    filing = select_latest_filing(submissions, cik)
    numeric = _normalize_columns(numeric)
    tags = _normalize_columns(tags)
    required = {"adsh", "tag", "ddate", "qtrs", "uom", "value"}
    missing = required.difference(numeric.columns)
    if missing:
        raise ValueError(f"NUM table is missing required columns: {sorted(missing)}")
    tag_required = {"tag", "tlabel"}
    missing_tags = tag_required.difference(tags.columns)
    if missing_tags:
        raise ValueError(f"TAG table is missing required columns: {sorted(missing_tags)}")

    facts = numeric.loc[numeric["adsh"].eq(filing["adsh"])].copy()
    if "segments" in facts.columns:
        facts = facts.loc[facts["segments"].fillna("").astype(str).str.strip().eq("")]
    facts["value"] = pd.to_numeric(facts["value"], errors="coerce")
    facts["qtrs"] = pd.to_numeric(facts["qtrs"], errors="coerce")
    facts = facts.dropna(subset=["value", "qtrs"])
    join_columns = ["tag"]
    if "version" in facts.columns and "version" in tags.columns:
        join_columns.append("version")
    label_columns = list(dict.fromkeys(join_columns + ["tlabel"]))
    labels = tags[label_columns].drop_duplicates(join_columns, keep="last")
    facts = facts.merge(labels, on=join_columns, how="left", validate="many_to_one")
    facts["label"] = facts["tlabel"].fillna(facts["tag"])
    facts["period"] = facts["ddate"].astype(str)
    facts["quarters"] = facts["qtrs"].astype(int)
    facts["statement"] = [
        _statement_for_fact(tag, label, quarters)
        for tag, label, quarters in zip(facts["tag"], facts["label"], facts["quarters"])
    ]

    display_columns = ["label", "tag", "period", "quarters", "uom", "value"]
    if presentation is not None:
        presentation = _normalize_columns(presentation)
        required_presentation = {"adsh", "tag", "version", "stmt", "report", "line", "plabel"}
        missing_presentation = required_presentation.difference(presentation.columns)
        if missing_presentation:
            raise ValueError(
                f"PRE table is missing required columns: {sorted(missing_presentation)}"
            )
        join_columns = ["adsh", "tag"]
        if "version" in facts.columns:
            join_columns.append("version")
        if "version" not in join_columns:
            raise ValueError("NUM table must include version to match PRE presentation rows")
        presentation_columns = join_columns + ["stmt", "report", "line", "plabel"]
        if "negating" in presentation.columns:
            presentation_columns.append("negating")
        presented = presentation.loc[
            presentation["adsh"].eq(filing["adsh"]), presentation_columns
        ].copy()
        facts = facts.merge(
            presented.drop_duplicates(join_columns + ["report", "line"]),
            on=join_columns,
            how="inner",
            validate="many_to_many",
        )
        facts["label"] = facts["plabel"].fillna(facts["label"])
        facts["statement"] = facts["stmt"].map(
            {"BS": "balance_sheet", "IS": "income_statement", "CF": "cash_flow"}
        )
        if "negating" in facts.columns:
            negating = facts["negating"].astype(str).str.strip().isin(["1", "True", "true"])
            facts.loc[negating, "value"] *= -1
        display_columns += ["stmt", "report", "line"]
    else:
        facts["statement"] = [
            _statement_for_fact(tag, label, quarters)
            for tag, label, quarters in zip(facts["tag"], facts["label"], facts["quarters"])
        ]

    tables: dict[str, pd.DataFrame] = {}
    for name in STATEMENT_NAMES:
        table = facts.loc[facts["statement"].eq(name), display_columns].copy()
        if presentation is not None:
            table = table.drop_duplicates(
                ["report", "line", "tag", "period", "quarters", "uom"], keep="last"
            )
            table["_report_order"] = pd.to_numeric(table["report"], errors="coerce")
            table["_line_order"] = pd.to_numeric(table["line"], errors="coerce")
            sort_columns = ["_report_order", "_line_order", "period", "quarters"]
            ascending = [True, True, False, False]
        else:
            table = table.drop_duplicates(["tag", "period", "quarters", "uom"], keep="last")
            sort_columns = ["period", "quarters", "label"]
            ascending = [False, False, True]
        table = table.sort_values(sort_columns, ascending=ascending)
        if presentation is not None:
            table = table.drop(columns=["_report_order", "_line_order"])
        tables[name] = table.reset_index(drop=True)
    return filing, tables


def common_size_statements(
    statements: Mapping[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Return common-size statement copies with amounts expressed as percentages.

    Balance sheet items are scaled by total assets. Income statement and cash-flow
    items are scaled by revenue for matching period and duration. Rows with no
    denominator are omitted rather than presented as misleading percentages.

    >>> statements = {
    ...     "balance_sheet": pd.DataFrame({"label": ["Assets", "Cash"], "tag": ["Assets", "CashAndCashEquivalentsAtCarryingValue"], "period": ["2024-03-31"] * 2, "quarters": [0] * 2, "uom": ["USD"] * 2, "value": [100, 25]}),
    ...     "income_statement": pd.DataFrame({"label": ["Revenue"], "tag": ["Revenues"], "period": ["2024-03-31"], "quarters": [1], "uom": ["USD"], "value": [50]}),
    ...     "cash_flow": pd.DataFrame({"label": ["Operating cash flow"], "tag": ["NetCashProvidedByUsedInOperatingActivities"], "period": ["2024-03-31"], "quarters": [1], "uom": ["USD"], "value": [10]}),
    ... }
    >>> common_size_statements(statements)["balance_sheet"]["value"].tolist()
    [100.0, 25.0]
    >>> float(common_size_statements(statements)["cash_flow"]["value"].iloc[0])
    20.0
    """
    result: dict[str, pd.DataFrame] = {}
    balance = statements["balance_sheet"].copy()
    revenue = statements["income_statement"].copy()

    def find_revenue(period: object, quarters: object) -> float | None:
        candidates = revenue.loc[
            revenue["period"].eq(period)
            & revenue["quarters"].eq(quarters)
            & revenue["tag"].astype(str).str.contains(r"Revenue|Sales", case=False, regex=True)
        ]
        if candidates.empty:
            return None
        values = candidates["value"].abs()
        return float(values.iloc[0]) if values.iloc[0] else None

    asset_rows = balance.loc[
        balance["tag"].astype(str).str.fullmatch(r"Assets", case=False)
    ]
    if asset_rows.empty:
        asset_rows = balance.loc[
            balance["label"].astype(str).str.fullmatch(r"Total assets", case=False)
        ]
    asset_denominators = {
        period: float(value)
        for period, value in zip(asset_rows["period"], asset_rows["value"])
        if value != 0
    }

    for name, frame in statements.items():
        common = frame.copy()
        if name == "balance_sheet":
            common["denominator"] = common["period"].map(asset_denominators)
        else:
            common["denominator"] = [
                find_revenue(period, quarters)
                for period, quarters in zip(common["period"], common["quarters"])
            ]
        common = common.loc[common["denominator"].notna() & common["denominator"].ne(0)].copy()
        common["value"] = (common["value"] / common["denominator"] * 100).round(2)
        common = common.drop(columns="denominator")
        result[name] = common.reset_index(drop=True)
    return result