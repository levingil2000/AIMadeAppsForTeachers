import pandas as pd
import json
from datetime import datetime

def export_grade_data(grades_file, codebook_file, output_dir):
    """
    Processes student grades and codebook data, then exports relevant analysis
    to a JSON file for dashboard visualization.

    Args:
        grades_file (str): Path to the grades CSV file.
        codebook_file (str): Path to the codebook CSV file.
        output_dir (str): Directory to save the output JSON file.
    """
    try:
        grades_df = pd.read_csv(grades_file)
        codebook_df = pd.read_csv(codebook_file)
    except FileNotFoundError as e:
        print(f"Error: {e}. Please check the file paths.")
        return

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

    # --- Export Data to JSON ---
    output_data = {
        "failing_students": failing_students_data,
        "competency_performance": competency_performance,
        "class_recommendations": class_recommendations
    }

    output_filename = "grade_analysis_data.json"
    output_path = f"{output_dir}/{output_filename}"

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=4)

    print(f"Grade analysis data exported to {output_path}")

if __name__ == "__main__":
    grades_file = "gradesMachineReadable.csv"
    codebook_file = "codebookMachineReadable.csv"
    output_dir = "."
    export_grade_data(grades_file, codebook_file, output_dir)
