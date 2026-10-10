"""
viz_utils.py — Idea 5: Schema-Linking Visualizer & Idea 6: Auto-Visualization Agent
======================================================================================
Idea 5: Parse the generated SQL with sqlglot to extract tables, columns, and join
         conditions used, then render an interactive ER-style graph via streamlit-agraph
         where used nodes/edges are highlighted in accent color.

Idea 6: Inspect the result DataFrame (column types, cardinality, row count) and
         automatically choose the best Plotly chart. Gracefully handles:
         - Pure text results       → skip chart (show table only)
         - Single numeric value    → Big Metric card
         - 1 categorical + 1 numeric  → Horizontal bar chart
         - 1 date + 1 numeric     → Line chart
         - Multi-column mix       → show the most informative bar (first categorical × first numeric)
         Always includes a manual chart-type override dropdown.
"""

from __future__ import annotations
import re
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# IDEA 5: Schema-Linking Visualizer
# ─────────────────────────────────────────────────────────────────────────────

# Hard-coded FK edges discovered from the cre_Drama_Workshop_Groups schema
# Format: (from_table, from_col, to_table, to_col)
SCHEMA_FK_EDGES = [
    ("Bookings",           "Customer_ID",       "Customers",            "Customer_ID"),
    ("Bookings",           "Customer_ID",       "Clients",              "Client_ID"),
    ("Bookings",           "Workshop_Group_ID", "Drama_Workshop_Groups","Workshop_Group_ID"),
    ("Bookings",           "Store_ID",          "Stores",               "Store_ID"),
    ("Bookings_Services",  "Order_ID",          "Bookings",             "Booking_ID"),
    ("Bookings_Services",  "Product_ID",        "Services",             "Service_ID"),
    ("Performers_in_Bookings","Order_ID",        "Bookings",             "Booking_ID"),
    ("Performers_in_Bookings","Performer_ID",    "Performers",           "Performer_ID"),
    ("Order_Items",        "Order_ID",          "Bookings",             "Booking_ID"),
    ("Order_Items",        "Product_ID",        "Products",             "Product_ID"),
    ("Clients",            "Address_ID",        "Addresses",            "Address_ID"),
    ("Customers",          "Address_ID",        "Addresses",            "Address_ID"),
    ("Drama_Workshop_Groups","Address_ID",       "Addresses",            "Address_ID"),
    ("Stores",             "Address_ID",        "Addresses",            "Address_ID"),
    ("Performers",         "Address_ID",        "Addresses",            "Address_ID"),
    ("Stores",             "Marketing_Region_Code","Marketing_Regions", "Marketing_Region_Code"),
    ("Drama_Workshop_Groups","Marketing_Region_Code","Marketing_Regions","Marketing_Region_Code"),
    ("Services",           "Workshop_Group_ID", "Drama_Workshop_Groups","Workshop_Group_ID"),
    ("Services",           "Service_Type_Code", "Ref_Service_Types",   "Service_Type_Code"),
]

# Complete column list per table (for hover labels)
SCHEMA_COLS = {
    "Customers":            ["Customer_ID","Address_ID","Customer_Name","Customer_Phone","Customer_Email_Address","Other_Details"],
    "Clients":              ["Client_ID","Address_ID","Customer_Email_Address","Customer_Name","Customer_Phone","Other_Details"],
    "Bookings":             ["Booking_ID","Customer_ID","Workshop_Group_ID","Status_Code","Store_ID","Order_Date","Planned_Delivery_Date","Actual_Delivery_Date","Other_Order_Details"],
    "Stores":               ["Store_ID","Address_ID","Marketing_Region_Code","Store_Name","Store_Phone","Store_Email_Address","Other_Details"],
    "Drama_Workshop_Groups":["Workshop_Group_ID","Address_ID","Currency_Code","Marketing_Region_Code","Store_Name","Store_Phone","Store_Email_Address","Other_Details"],
    "Performers":           ["Performer_ID","Address_ID","Customer_Name","Customer_Phone","Customer_Email_Address","Other_Details"],
    "Services":             ["Service_ID","Service_Type_Code","Workshop_Group_ID","Product_Description","Product_Name","Product_Price","Other_Product_Service_Details"],
    "Products":             ["Product_ID","Product_Name","Product_Price","Product_Description","Other_Product_Service_Details"],
    "Addresses":            ["Address_ID","Line_1","Line_2","City_Town","State_County","Other_Details"],
    "Bookings_Services":    ["Order_ID","Product_ID"],
    "Performers_in_Bookings":["Order_ID","Performer_ID"],
    "Order_Items":          ["Order_Item_ID","Order_ID","Product_ID","Order_Quantity","Other_Item_Details"],
    "Marketing_Regions":    ["Marketing_Region_Code","Marketing_Region_Name","Marketing_Region_Descriptrion","Other_Details"],
    "Ref_Service_Types":    ["Service_Type_Code","Parent_Service_Type_Code","Service_Type_Description"],
}


def _parse_sql_links(sql: str) -> tuple[set[str], set[str]]:
    """
    Parse SQL with sqlglot to extract tables and columns used.
    Returns (used_tables: set[str], used_cols: set[str]).
    Falls back to regex if sqlglot fails.
    """
    used_tables: set[str] = set()
    used_cols: set[str] = set()
    try:
        import sqlglot
        import sqlglot.expressions as exp
        ast = sqlglot.parse_one(sql, dialect="sqlite", error_level=sqlglot.ErrorLevel.IGNORE)
        for t in ast.find_all(exp.Table):
            used_tables.add(t.name)
        for c in ast.find_all(exp.Column):
            used_cols.add(c.name)
    except Exception:
        # Regex fallback
        for t in SCHEMA_COLS:
            if re.search(rf'\b{re.escape(t)}\b', sql, re.IGNORECASE):
                used_tables.add(t)
        for t in used_tables:
            for c in SCHEMA_COLS.get(t, []):
                if re.search(rf'\b{re.escape(c)}\b', sql, re.IGNORECASE):
                    used_cols.add(c)
    return used_tables, used_cols


def render_schema_linker(sql: str):
    """
    Idea 5 — Schema-Linking Visualizer.
    Renders an interactive agraph ER diagram. Tables used in the SQL are highlighted
    in accent green, FK join edges used in the SQL are bolded, other edges are dimmed.
    Falls back to a compact text view if agraph isn't importable.
    """
    if not sql or not sql.strip():
        return

    used_tables, used_cols = _parse_sql_links(sql)
    if not used_tables:
        return

    # Determine which FK edges are activated (both sides in used_tables)
    active_edges = [
        (f, fc, t, tc)
        for (f, fc, t, tc) in SCHEMA_FK_EDGES
        if f in used_tables and t in used_tables
    ]

    with st.expander("🗺️ Schema-Linking Visualizer (Idea 5) — Tables & Joins used in this query", expanded=True):
        # Summary line
        table_badges = " · ".join([f"`{t}`" for t in sorted(used_tables)])
        st.markdown(f"**Tables accessed:** {table_badges}")

        if active_edges:
            join_text = " · ".join([f"`{f}.{fc}` ⟶ `{t}.{tc}`" for f, fc, t, tc in active_edges])
            st.markdown(f"**Join paths activated:** {join_text}")

        used_col_badges = " · ".join([f"`{c}`" for c in sorted(used_cols) if c])
        if used_col_badges:
            st.markdown(f"**Columns selected/filtered:** {used_col_badges}")

        try:
            from streamlit_agraph import agraph, Node, Edge, Config

            nodes = []
            edges_out = []

            all_relevant_tables = set(used_tables)
            for f, _, t, _ in active_edges:
                all_relevant_tables.add(f)
                all_relevant_tables.add(t)

            for tbl in all_relevant_tables:
                cols = SCHEMA_COLS.get(tbl, [])
                highlighted_cols = [f"→ {c}" if c in used_cols else c for c in cols]
                label = tbl
                col_tooltip = "\n".join(highlighted_cols[:8])  # max 8 cols in tooltip
                is_used = tbl in used_tables
                nodes.append(Node(
                    id=tbl,
                    label=label,
                    title=f"Table: {tbl}\nColumns:\n{col_tooltip}",
                    size=28 if is_used else 18,
                    color="#22c55e" if is_used else "#94a3b8",
                    font={"size": 14 if is_used else 11, "color": "#fff" if is_used else "#334155"},
                    shape="box",
                ))

            for (f, fc, t, tc) in SCHEMA_FK_EDGES:
                if f not in all_relevant_tables or t not in all_relevant_tables:
                    continue
                is_active = (f, fc, t, tc) in active_edges
                edges_out.append(Edge(
                    source=f,
                    target=t,
                    label=f"{fc} → {tc}",
                    title=f"{f}.{fc} → {t}.{tc}",
                    color="#22c55e" if is_active else "#cbd5e1",
                    width=3 if is_active else 1,
                    dashes=not is_active,
                ))

            config = Config(
                width="100%",
                height=380,
                directed=True,
                physics=True,
                hierarchical=False,
                nodeHighlightBehavior=True,
                highlightColor="#f97316",
                collapsible=False,
            )
            agraph(nodes=nodes, edges=edges_out, config=config)

        except Exception as graph_err:
            # Clean fallback if agraph has rendering issues or is not installed
            st.caption(f"💡 Interactive graph preview: {graph_err}")


# ─────────────────────────────────────────────────────────────────────────────
# IDEA 6: Auto-Visualization Agent
# ─────────────────────────────────────────────────────────────────────────────

def _classify_dataframe(df: pd.DataFrame) -> str:
    """
    Classify the dataframe shape and column types to choose chart strategy.
    Returns one of: 'metric', 'bar', 'line', 'table'
    """
    if df is None or df.empty:
        return "table"

    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Attempt numeric coercion for string-wrapped numeric columns from SQLite
    for c in df.columns:
        conv = pd.to_numeric(df[c], errors='coerce')
        if not conv.isna().all() and conv.isna().sum() == df[c].isna().sum():
            df[c] = conv

    n_rows, n_cols = df.shape

    # Single cell — show as big metric
    if n_rows == 1 and n_cols == 1:
        val = df.iloc[0, 0]
        try:
            float(val)
            return "metric"
        except (TypeError, ValueError):
            return "table"

    # Detect numeric and categorical columns
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    date_cols = [c for c in cat_cols if any(kw in c.lower() for kw in ('date', 'time', 'month', 'year', 'day'))]

    # At least 1 cat + 1 numeric → bar chart
    if cat_cols and num_cols:
        return "bar"

    # Date-like column + numeric → line chart
    if date_cols and num_cols:
        return "line"

    # Only numerics with multiple rows → bar
    if num_cols and n_rows > 1:
        return "bar"

    return "table"


def render_auto_visualization(df: pd.DataFrame, question: str = "", unique_key: str = ""):
    """
    Idea 6 — Auto-Visualization Agent.
    Inspects the result DataFrame and automatically renders the most appropriate
    Plotly chart. Includes a chart-type override dropdown.
    - Pure text results / single-column names → no chart (table only, no error)
    - Single numeric cell → Big Metric card (delta-style)
    - 1 categorical + 1 numeric → Horizontal bar chart (most common for this DB)
    - Date + numeric -> Line chart
    - Multi-col -> most informative bar pairing
    unique_key: a caller-provided string that must be unique per Streamlit script run
                (e.g. 'single_0', 'tab_a_0', 'history_3'). Prevents duplicate-key errors
                when the function is called multiple times per rerun.
    """
    if df is None or df.empty:
        return

    import plotly.express as px

    df_clean = df.loc[:, ~df.columns.duplicated()].copy()

    for c in df_clean.columns:
        conv = pd.to_numeric(df_clean[c], errors='coerce')
        if not conv.isna().all() and conv.isna().sum() == df_clean[c].isna().sum():
            df_clean[c] = conv

    n_rows, n_cols = df_clean.shape

    num_cols = [c for c in df_clean.columns if pd.api.types.is_numeric_dtype(df_clean[c])]
    cat_cols = [c for c in df_clean.columns if not pd.api.types.is_numeric_dtype(df_clean[c])]

    # If there's nothing plottable, don't show the section at all
    can_plot = bool(num_cols) or (n_rows == 1 and n_cols == 1)
    if not can_plot:
        return  # pure text table — just skip silently

    auto_type = _classify_dataframe(df_clean)

    with st.expander("📊 Auto-Visualization (Idea 6) — Smart Chart from Query Results", expanded=True):

        # Chart type override
        override_options = ["Auto (Recommended)", "Bar Chart", "Line Chart", "Metric Card", "Skip Chart"]
        col_ctrl, _ = st.columns([2, 3])
        with col_ctrl:
            chosen = st.selectbox(
                "Chart type:",
                options=override_options,
                index=0,
                key=f"chart_type_override_{unique_key or id(df)}",
            )

        if chosen == "Skip Chart":
            st.caption("Chart display skipped.")
            return

        if chosen != "Auto (Recommended)":
            chart_map = {
                "Bar Chart": "bar",
                "Line Chart": "line",
                "Metric Card": "metric",
            }
            resolved_type = chart_map.get(chosen, auto_type)
        else:
            resolved_type = auto_type

        st.caption(f"🤖 **Chart type selected:** `{resolved_type.upper()}` {'(auto-detected)' if chosen == 'Auto (Recommended)' else '(manual override)'}")

        try:
            if resolved_type == "metric":
                val = df_clean.iloc[0, 0]
                col_name = df_clean.columns[0]
                st.metric(label=col_name, value=val)

            elif resolved_type == "bar":
                cat_col = cat_cols[0] if cat_cols else df_clean.columns[0]
                num_col = num_cols[0] if num_cols else df_clean.columns[-1]
                df_plot = df_clean[[cat_col, num_col]].dropna()
                df_plot = df_plot.sort_values(num_col, ascending=True)  # sorted for clarity
                fig = px.bar(
                    df_plot,
                    x=num_col,
                    y=cat_col,
                    orientation="h",
                    text=num_col,
                    color=num_col,
                    color_continuous_scale="teal",
                    title=f"{num_col} by {cat_col}",
                    labels={cat_col: cat_col.replace("_", " "), num_col: num_col.replace("_", " ")},
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(
                    height=max(300, min(60 * len(df_plot), 600)),
                    showlegend=False,
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=40, t=40, b=30),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(automargin=True),
                )
                st.plotly_chart(fig, use_container_width=True)

            elif resolved_type == "line":
                date_col = next(
                    (c for c in cat_cols if any(kw in c.lower() for kw in ('date', 'time', 'month', 'year'))),
                    cat_cols[0] if cat_cols else df_clean.columns[0]
                )
                num_col = num_cols[0] if num_cols else df_clean.columns[-1]
                df_plot = df_clean[[date_col, num_col]].dropna()
                fig = px.line(
                    df_plot,
                    x=date_col,
                    y=num_col,
                    markers=True,
                    title=f"{num_col} over {date_col}",
                    labels={date_col: date_col.replace("_", " "), num_col: num_col.replace("_", " ")},
                )
                fig.update_layout(
                    height=350,
                    margin=dict(l=10, r=20, t=40, b=30),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("📋 Results are text-only — displayed as table above (no chart applicable).")

        except Exception as e:
            st.warning(f"⚠️ Chart could not be rendered: {e}")
