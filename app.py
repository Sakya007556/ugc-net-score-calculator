import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(
    page_title="UGC NET HRM Dec 2025 Score Calculator",
    page_icon="✅",
    layout="centered"
)

MARKS_CORRECT = 2
MARKS_WRONG = 0
MARKS_UNATTEMPTED = 0

ANSWER_KEY_FILE = "answer_key.xlsx"

# Regex patterns for NTA response sheet format
QID_PATTERN = re.compile(r"Question ID\s*:\s*(\d+)")
CHOSEN_PATTERN = re.compile(r"Chosen Option\s*:\s*(\d+)")


# ---------------------------
# FUNCTIONS
# ---------------------------
def extract_answers_from_pdf(uploaded_pdf_file) -> pd.DataFrame:
    """
    Extract QuestionID and ChosenOption from response sheet PDF.
    Returns DataFrame with columns: QuestionID, ChosenOption
    """
    question_ids = []
    chosen_options = []

    with pdfplumber.open(uploaded_pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""

            qids = QID_PATTERN.findall(text)
            chosens = CHOSEN_PATTERN.findall(text)

            # Pair them in order
            for qid, chosen in zip(qids, chosens):
                question_ids.append(int(qid))
                chosen_options.append(int(chosen))

    return pd.DataFrame({
        "QuestionID": question_ids,
        "ChosenOption": chosen_options
    })


def calculate_score(answer_key_df: pd.DataFrame, my_answers_df: pd.DataFrame):
    """
    Merge answer key + chosen answers.
    Returns detailed report df + summary dict
    """
    report = pd.merge(answer_key_df, my_answers_df, on="QuestionID", how="left")

    def result_row(row):
        if pd.isna(row["ChosenOption"]):
            return "Not Attempted"
        elif int(row["ChosenOption"]) == int(row["CorrectOption"]):
            return "Correct"
        return "Wrong"

    report["Result"] = report.apply(result_row, axis=1)

    def marks_row(row):
        if row["Result"] == "Correct":
            return MARKS_CORRECT
        elif row["Result"] == "Wrong":
            return MARKS_WRONG
        return MARKS_UNATTEMPTED

    report["Marks"] = report.apply(marks_row, axis=1)

    summary = {
        "Correct": int((report["Result"] == "Correct").sum()),
        "Wrong": int((report["Result"] == "Wrong").sum()),
        "Not Attempted": int((report["Result"] == "Not Attempted").sum()),
        "Total Score": int(report["Marks"].sum())
    }

    return report, summary


def generate_excel_report(report_df: pd.DataFrame, summary: dict) -> bytes:
    """
    Create downloadable Excel in memory and return bytes
    """
    summary_df = pd.DataFrame({
        "Metric": list(summary.keys()),
        "Value": list(summary.values())
    })

    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        report_df.to_excel(writer, index=False, sheet_name="Detailed Report")
        summary_df.to_excel(writer, index=False, sheet_name="Summary")

    return excel_buffer.getvalue()


# ---------------------------
# UI (SEO + App Layout)
# ---------------------------
st.title("UGC NET HRM December 2025 Answer Key Score Calculator")
st.markdown("""
✅ **Upload your UGC NET Response Sheet PDF** and calculate your marks instantly.  
🎯 **Subject:** Labour Welfare / HRM (UGC NET Dec 2025)  
🔍 This tool automatically extracts **Question ID + Chosen Option** and matches with official answer key.

**How to use:**
1. Upload your response sheet PDF  
2. Click **Calculate Score**  
3. Download Excel report (optional)
""")

st.divider()

# Load answer key
try:
    answer_key = pd.read_excel(ANSWER_KEY_FILE)
except Exception:
    st.error("❌ answer_key.xlsx not found or invalid format. Please upload correct file in GitHub repo.")
    st.stop()

# Validate answer key columns
required_cols = {"QuestionID", "CorrectOption"}
if not required_cols.issubset(set(answer_key.columns)):
    st.error("❌ answer_key.xlsx must contain columns: QuestionID, CorrectOption")
    st.stop()

# Upload PDF
uploaded_pdf = st.file_uploader("📄 Upload Response Sheet PDF", type=["pdf"])

col1, col2 = st.columns(2)
with col1:
    st.caption("✅ Works best with official NTA response sheet PDF (text-based).")
with col2:
    st.caption("⚠️ If PDF is scanned images, extraction may fail (needs OCR).")

# Button
if uploaded_pdf is not None:
    st.success("✅ PDF Uploaded Successfully")

    if st.button("📌 Calculate Score", use_container_width=True):
        with st.spinner("Extracting your chosen answers from PDF..."):
            my_answers = extract_answers_from_pdf(uploaded_pdf)

        # If no answers extracted
        if my_answers.empty:
            st.error("""
❌ Could not extract QuestionID / ChosenOption from this PDF.

✅ Possible reasons:
- PDF is scanned image (not text)
- Response sheet format is different

Try downloading response sheet again from official NTA site.
""")
            st.stop()

        with st.spinner("Matching with answer key and calculating score..."):
            report, summary = calculate_score(answer_key, my_answers)

        st.subheader("✅ Score Summary")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Correct", summary["Correct"])
        c2.metric("Wrong", summary["Wrong"])
        c3.metric("Not Attempted", summary["Not Attempted"])
        c4.metric("Total Score", summary["Total Score"])

        st.divider()

        st.subheader("📊 Detailed Report")
        st.dataframe(report, use_container_width=True)

        st.divider()

        st.subheader("📥 Download")
        excel_bytes = generate_excel_report(report, summary)

        st.download_button(
            label="Download Score Report (Excel)",
            data=excel_bytes,
            file_name="ugc_net_score_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        st.info("✅ Report generated successfully!")

else:
    st.warning("📌 Please upload your response sheet PDF to calculate score.")
