import math
import uuid
from datetime import date
import pandas as pd
import streamlit as st

# -----------------------------
# Configuration
# -----------------------------
st.set_page_config(
    page_title="CleanFoam",
    layout="wide",
)
st.title("CleanFoam")

# -----------------------------
# Session State Management
# -----------------------------
def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if "workers" not in st.session_state:
        st.session_state.workers: list[dict] = []
    if "report_date" not in st.session_state:
        st.session_state.report_date = date.today()

# -----------------------------
# Helper Functions
# -----------------------------
def clean_number(n):
    """Render integers without .0 and handle non-numeric types gracefully."""
    if isinstance(n, (int, float)):
        return int(n) if float(n).is_integer() else f"{n:.2f}"
    return n

def compute_fee(total_value: float, custom_due: float | None) -> float:
    """Calculate the fee based on business rules."""
    if custom_due is not None and custom_due > 0:
        return custom_due
    rules = {80.0: 20.0, 90.0: 20.0, 95.0: 22.5, 100.0: 25.0, 105.0: 27.5, 110.0: 25.0}
    fee = rules.get(total_value)
    if fee is not None:
        return fee
    if int(total_value) % 10 == 5:
        return 32.5
    return 30.0

# -----------------------------
# Main App Logic and Layout
# -----------------------------
def main():
    initialize_session_state()

    # --- 1. Date Input ---
    st.session_state.report_date = st.date_input("Date", value=st.session_state.report_date)

    # --- 2. Main Input Fields (within the elegant form) ---
    with st.form(key="add_worker_form", clear_on_submit=True):
        name = st.text_input("Worker Name")
        total_value = st.number_input("Total Value", min_value=0.0, step=0.5, format="%.2f")
        withdrawn_val = st.number_input("Withdrawn Value", min_value=0.0, step=0.5, format="%.2f")
        entry_type = st.radio("Entry Type", ("Standard", "CF"), horizontal=True)
        
        st.divider()
        with st.expander("Advanced Options"):
            col1, col2 = st.columns(2)
            with col1: due_custom_val = st.number_input("Custom Due (Optional)", min_value=0.0, step=0.5, format="%.2f")
            with col2: note_text = st.text_input("Note (Optional)")
        
        st.divider()
        add_clicked = st.form_submit_button("Add Worker", type="primary", use_container_width=True)
        
        if add_clicked:
            if not name: st.error("Worker name is required.")
            elif total_value <= 0 and entry_type == "Standard": st.error("Total value must be greater than 0.")
            else:
                wid = uuid.uuid4().hex
                if entry_type == "CF":
                    new_worker = {"ID": wid, "Worker": name, "Total": total_value, "Due": "", "Withdrawn": "", "Remaining": "", "Note": note_text, "EntryType": "CF"}
                else:
                    fee = compute_fee(total_value, due_custom_val if due_custom_val > 0 else None)
                    remaining = (total_value / 2) - withdrawn_val - fee
                    new_worker = {"ID": wid, "Worker": name, "Total": total_value, "Due": fee, "Withdrawn": withdrawn_val, "Remaining": remaining, "Note": note_text, "EntryType": "Standard"}
                st.session_state.workers.append(new_worker)
                st.success(f"Added {name} successfully!")
                st.rerun()

    st.divider()

    # --- 3. Workers Overview ---
    st.subheader("Workers Overview")
    st.caption(f"Date: {st.session_state.report_date.strftime('%Y-%m-%d')}")
    
    if not st.session_state.workers:
        st.info("No workers added yet. Use the form above to add a new entry.")
    else:
        df = pd.DataFrame(st.session_state.workers)
        df_display = df.copy()
        for col in ["Total", "Due", "Withdrawn", "Remaining"]:
            df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0).apply(clean_number)
        st.dataframe(df_display[["Worker", "Total", "Due", "Withdrawn", "Remaining", "Note"]], use_container_width=True, hide_index=True)

        # --- 4. Financial Summary ---
        st.subheader("Financial Summary")
        numeric_cols = ["Total", "Withdrawn", "Remaining"]
        for col in numeric_cols: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        total_sum, withdrawn_sum, remaining_sum = df["Total"].sum(), df["Withdrawn"].sum(), df["Remaining"].sum()
        for_workers = withdrawn_sum + remaining_sum
        for_cleanfoam = total_sum - for_workers
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Revenue", f"{total_sum:,.2f}")
        m_col2.metric("For Workers", f"{for_workers:,.2f}")
        m_col3.metric("For CleanFoam", f"{for_cleanfoam:,.2f}")

    st.divider()

    # --- 5. Settings and Actions (Combined and Stable) ---
    with st.expander("⚙️ Settings"):
        st.subheader("Delete a Worker")
        
        # This mapping is internal and robust. The user only sees the descriptive label.
        worker_options_map = {f"{w['Worker']} (Total: {w['Total']})": w['ID'] for w in st.session_state.workers}
        selected_label = st.selectbox("Select a worker to delete", options=worker_options_map.keys(), index=None, placeholder="Choose a worker...")
        
        if st.button("Delete Selected Worker", type="secondary", use_container_width=True, disabled=(not selected_label)):
            if selected_label:
                worker_id_to_delete = worker_options_map[selected_label]
                st.session_state.workers = [w for w in st.session_state.workers if w['ID'] != worker_id_to_delete]
                st.success(f"Deleted worker: {selected_label.split(' (')[0]}")
                st.rerun()

        st.divider()
        st.subheader("General Settings")

        col_settings_1, col_settings_2 = st.columns(2)
        with col_settings_1:
            if st.button("Reset All Workers", use_container_width=True):
                if st.session_state.workers:
                    st.session_state.workers = []
                    st.success("All workers have been cleared.")
                    st.rerun()
        
        with col_settings_2:
            if st.session_state.workers:
                df_csv = pd.DataFrame(st.session_state.workers)[["Worker", "Total", "Due", "Withdrawn", "Remaining", "Note"]]
                st.download_button("Download Report as CSV", df_csv.to_csv(index=False).encode("utf-8"), f"cleanfoam_report_{st.session_state.report_date.strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

if __name__ == "__main__":
    main()
