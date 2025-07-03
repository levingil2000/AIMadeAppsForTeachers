import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def analyze_grades_streamlit(grades_file, codebook_file):
    try:
        grades_df = pd.read_csv(grades_file)
        codebook_df = pd.read_csv(codebook_file)
    except FileNotFoundError as e:
        st.error(f"Error: {e}. Please check the file paths.")
        return None, None, None

    # --- Data Cleaning and Preparation ---
    grades_df.replace("#DIV/0!", 0, inplace=True)

    if '0' in grades_df.columns:
        grades_df.drop(columns=['0'], inplace=True)

    assessment_columns = list(set(grades_df.columns) & set(codebook_df['Assessment ID']))

    for col in assessment_columns:
        grades_df[col] = pd.to_numeric(grades_df[col], errors='coerce')

    grades_df[assessment_columns] = grades_df[assessment_columns].fillna(0)

    passing_threshold = 60
    failing_students_data = []

    for index, student in grades_df.iterrows():
        student_name = student["Name"]
        failed_assessments = []

        for assessment_id in assessment_columns:
            score = student[assessment_id]
            if score < passing_threshold:
                assessment_info = codebook_df[codebook_df["Assessment ID"] == assessment_id]
                if not assessment_info.empty:
                    failed_assessments.append({
                        "assessment_id": assessment_id,
                        "score": round(score, 2),
                        "content_domain": assessment_info.iloc[0]["Content Domain"],
                        "learning_competency": assessment_info.iloc[0]["Learning Competency"]
                    })

        if failed_assessments:
            failing_students_data.append({
                "student_name": student_name,
                "failed_assessments": failed_assessments
            })

    # --- Dynamic Recommendations Analysis ---
    competency_performance = {}
    codebook_df['Learning Competency'] = codebook_df['Learning Competency'].fillna('Unknown')
    unique_competencies = codebook_df["Learning Competency"].unique()

    for competency in unique_competencies:
        if competency in [0, 'Unknown'] or pd.isna(competency):
            continue
        
        assessment_ids = codebook_df[codebook_df["Learning Competency"] == competency]["Assessment ID"].tolist()
        assessment_ids = [aid for aid in assessment_ids if aid in grades_df.columns]

        if not assessment_ids:
            continue

        total_students = len(grades_df)
        total_passed = grades_df[assessment_ids].apply(lambda x: (x >= passing_threshold)).sum().sum()
        total_possible = total_students * len(assessment_ids)

        if total_possible > 0:
            pass_rate = (total_passed / total_possible) * 100
            competency_performance[competency] = round(pass_rate, 2)

    sorted_competencies = sorted(competency_performance.items(), key=lambda item: item[1])

    class_recommendations = []
    for i, (competency, pass_rate) in enumerate(sorted_competencies):
        if i < 3: # Focus on the 3 most challenging competencies
            if pass_rate < 50:
                class_recommendations.append(f"URGENT FOCUS: '{competency}' has a very low pass rate of {pass_rate:.2f}%. A comprehensive re-teaching of this topic is strongly recommended for the entire class.")
            elif pass_rate < 75:
                class_recommendations.append(f"HIGH PRIORITY: '{competency}' shows a significant struggle with a {pass_rate:.2f}% pass rate. Consider a targeted review session and providing supplementary materials.")
            else:
                class_recommendations.append(f"REVIEW SUGGESTED: While the pass rate for '{competency}' is {pass_rate:.2f}%, a number of students still require support. A quick review or a peer-tutoring session could be beneficial.")

    return failing_students_data, competency_performance, class_recommendations


st.set_page_config(layout="wide")
st.title("Grade Analysis Dashboard")

# File paths (assuming they are in the same directory as the script)
grades_file = "gradesMachineReadable.csv"
codebook_file = "codebookMachineReadable.csv"

failing_students_data, competency_performance, class_recommendations = analyze_grades_streamlit(grades_file, codebook_file)

if failing_students_data is not None:
    # --- Overall Competency Performance ---
    st.header("Overall Competency Performance")
    if competency_performance:
        competency_names = list(competency_performance.keys())
        pass_rates = list(competency_performance.values())

        colors = ['red' if rate < 60 else ('orange' if rate < 75 else 'green') for rate in pass_rates]

        fig = go.Figure(data=[go.Bar(x=competency_names, y=pass_rates, marker_color=colors)])
        fig.update_layout(title='Pass Rate by Learning Competency',
                          xaxis_title='Learning Competency',
                          yaxis_title='Pass Rate (%)',
                          yaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No competency performance data to display.")

    # --- Students Needing Remediation ---
    st.header("Students Needing Remediation")
    if failing_students_data:
        # Flatten the data for display in a DataFrame
        flat_data = []
        for student in failing_students_data:
            for assessment in student['failed_assessments']:
                flat_data.append({
                    "Student Name": student['student_name'],
                    "Failed Assessment": assessment['assessment_id'],
                    "Score": assessment['score'],
                    "Learning Competency": assessment['learning_competency']
                })
        
        failing_df = pd.DataFrame(flat_data)

        # Add filters
        st.subheader("Filter Students")
        col1, col2 = st.columns(2)
        
        all_competencies = ["All"] + sorted(failing_df["Learning Competency"].unique().tolist())
        selected_competency = col1.selectbox("Filter by Learning Competency", all_competencies)

        all_students = ["All"] + sorted(failing_df["Student Name"].unique().tolist())
        selected_student = col2.selectbox("Filter by Student Name", all_students)

        filtered_df = failing_df.copy()

        if selected_competency != "All":
            filtered_df = filtered_df[filtered_df["Learning Competency"] == selected_competency]
        
        if selected_student != "All":
            filtered_df = filtered_df[filtered_df["Student Name"] == selected_student]

        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.info("No students match the selected filters.")
    else:
        st.info("No students currently require remediation.")

    # --- Class Recommendations ---
    st.header("Class Recommendations")
    if class_recommendations:
        for rec in class_recommendations:
            st.write(f"- {rec}")
    else:
        st.info("No specific class recommendations at this time.")
