import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

MARKS_CORRECT = 2
MARKS_WRONG = 0
MARKS_UNATTEMPTED = 0

qid_pattern = re.compile(r"Question ID\s*:\s*(\d+)")
chosen_pattern = re.compile(r"Chosen Option\s*:\s*(\d+)")

def extract_answers_from_pdf(uploaded_pdf):
    question_ids, chosen_options = [], []

    with pdfplumber.open(uploaded_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            qids = qid_pattern.findall(text)
            chosens = chosen_pattern.findall(text)

            for qid, chosen in zip(qids, chosens):
                question_ids.append(int(qid))
                chosen_options.append(int(chosen))

    return pd.DataFrame({"QuestionID": question_ids, "ChosenOption": chosen_options})

st.title("UGC NET Score Calculator")

uploaded_pdf = st.file_uploader("Upload Response Sheet PDF", type=["pdf"])

# Answer key fixed file on server
answer_key = pd.read_excel("answer_key.xlsx")

if uploaded_pdf:
    st.success("PDF Uploaded Successfully ✅")

    if st.button("Calculate Score"):
        my_answers = extract_answers_from_pdf(uploaded_pdf)

        report = pd.merge(answer_key, my_answers, on="QuestionID", how="left")

        def result_row(row):
            if pd.isna(row["ChosenOption"]):
                return "Not Attempted"
            elif int(row["ChosenOption"]) == int(row["CorrectOption"]):
                return "Correct"
            else:
                return "Wrong"

        report["Result"] = report.apply(result_row, axis=1)

        def marks_row(row):
            if row["Result"] == "Correct":
                return MARKS_CORRECT
            elif row["Result"] == "Wrong":
                return MARKS_WRONG
            return MARKS_UNATTEMPTED

        report["Marks"] = report.apply(marks_row, axis=1)

        total_correct = (report["Result"] == "Correct").sum()
        total_wrong = (report["Result"] == "Wrong").sum()
        total_unattempted = (report["Result"] == "Not Attempted").sum()
        total_score = report["Marks"].sum()

        st.subheader("✅ Score Summary")
        st.write("Correct:", total_correct)
        st.write("Wrong:", total_wrong)
        st.write("Not Attempted:", total_unattempted)
        st.success(f"🎯 TOTAL SCORE: {total_score}")

        st.subheader("Detailed Report")
        st.dataframe(report)

        # Download Excel report
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            report.to_excel(writer, index=False, sheet_name="Detailed Report")

        st.download_button(
            label="📥 Download Excel Report",
            data=excel_buffer.getvalue(),
            file_name="score_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
