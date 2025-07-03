import pandas as pd
from datetime import datetime

def analyze_grades(grades_file, codebook_file, output_dir):
    """
    Analyzes student grades, identifies students needing remediation,
    groups them, and generates a remediation plan.

    Args:
        grades_file (str): Path to the grades CSV file.
        codebook_file (str): Path to the codebook CSV file.
        output_dir (str): Directory to save the output file.
    """
    try:
        grades_df = pd.read_csv(grades_file)
        codebook_df = pd.read_csv(codebook_file)
    except FileNotFoundError as e:
        print(f"Error: {e}. Please check the file paths.")
        return

    # --- Data Cleaning and Preparation ---
    # Replace '#DIV/0!' with 0, assuming it means a score of 0
    grades_df.replace("#DIV/0!", 0, inplace=True)

    # Drop columns named '0' if they exist
    if '0' in grades_df.columns:
        grades_df.drop(columns=['0'], inplace=True)

    # Get assessment columns by finding the intersection of columns
    # from both dataframes, excluding 'Name' and 'Gender' from grades_df
    assessment_columns = list(set(grades_df.columns) & set(codebook_df['Assessment ID']))

    # Convert assessment columns to numeric, coercing errors
    for col in assessment_columns:
        grades_df[col] = pd.to_numeric(grades_df[col], errors='coerce')

    # Fill any remaining NaN values with 0
    grades_df[assessment_columns] = grades_df[assessment_columns].fillna(0)


    passing_threshold = 60
    failing_students = {}

    for index, student in grades_df.iterrows():
        student_name = student["Name"]
        failed_assessments = []

        for assessment_id in assessment_columns:
            score = student[assessment_id]
            if score < passing_threshold:
                assessment_info = codebook_df[codebook_df["Assessment ID"] == assessment_id]
                if not assessment_info.empty:
                    failed_assessments.append({
                        "Assessment ID": assessment_id,
                        "Score": score,
                        "Content Domain": assessment_info.iloc[0]["Content Domain"],
                        "Learning Competency": assessment_info.iloc[0]["Learning Competency"]
                    })

        if failed_assessments:
            failing_students[student_name] = failed_assessments

    remediation_groups = {}
    for student, assessments in failing_students.items():
        for assessment in assessments:
            competency = assessment["Learning Competency"]
            if competency not in remediation_groups:
                remediation_groups[competency] = []
            remediation_groups[competency].append(student)

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
            competency_performance[competency] = pass_rate

    sorted_competencies = sorted(competency_performance.items(), key=lambda item: item[1])


    # --- Generate Report ---
    today_date = datetime.now().strftime("%Y-%m-%d")
    output_filename = f"remediation_plan_{today_date}.txt"
    output_path = f"{output_dir}/{output_filename}"

    with open(output_path, "w") as f:
        f.write(f"Remediation Plan - {today_date}\n")
        f.write("=" * 30 + "\n\n")

        f.write("Individual Remediation Plans\n")
        f.write("-" * 40 + "\n")
        for student, assessments in failing_students.items():
            f.write(f"\nStudent: {student}\n")
            for assessment in assessments:
                score_info = f"(Score: {assessment['Score']:.2f})"
                if assessment['Score'] == 0:
                    score_info += " - Note: Student may have missed this assessment."
                f.write(f"  - Failed Assessment: {assessment['Assessment ID']} {score_info}\n")
                f.write(f"    - Competency: {assessment['Learning Competency']}\n")
                f.write(f"    - Recommended Program: Focus on {assessment['Learning Competency']}.\n")
                f.write(f"    - Specific Task: Review concepts related to {assessment['Assessment ID']}.\n")
                f.write(f"    - Suggestion: Provide one-on-one tutoring and additional practice exercises.\n")

        f.write("\n" + "=" * 30 + "\n\n")


        f.write("Remediation Groups based on Learning Competency\n")
        f.write("-" * 40 + "\n")
        for competency, students in remediation_groups.items():
            f.write(f"\nLearning Competency: {competency}\n")
            f.write("  Students needing support:\n")
            for student in set(students):
                f.write(f"    - {student}\n")
        f.write("\n" + "=" * 30 + "\n\n")

        f.write("Class Performance Analysis and Recommendations\n")
        f.write("-" * 40 + "\n")
        f.write("This section analyzes the overall class performance for each learning competency.\n\n")
        
        if not sorted_competencies:
            f.write("No competency performance data to display.\n")
        else:
            f.write("Performance by Learning Competency (sorted by pass rate):\n")
            for competency, pass_rate in sorted_competencies:
                f.write(f"- {competency}: {pass_rate:.2f}% pass rate\n")

            f.write("\nRecommendations:\n")
            # Generate dynamic recommendations for the bottom 2-3 competencies
            for i, (competency, pass_rate) in enumerate(sorted_competencies):
                if i < 3: # Focus on the 3 most challenging competencies
                    if pass_rate < 50:
                        f.write(f"\n- URGENT FOCUS: '{competency}' has a very low pass rate of {pass_rate:.2f}%. A comprehensive re-teaching of this topic is strongly recommended for the entire class.\n")
                    elif pass_rate < 75:
                        f.write(f"\n- HIGH PRIORITY: '{competency}' shows a significant struggle with a {pass_rate:.2f}% pass rate. Consider a targeted review session and providing supplementary materials.\n")
                    else:
                        f.write(f"\n- REVIEW SUGGESTED: While the pass rate for '{competency}' is {pass_rate:.2f}%, a number of students still require support. A quick review or a peer-tutoring session could be beneficial.\n")

    print(f"Remediation plan saved to {output_path}")


if __name__ == "__main__":
    # Assuming the script is in the same directory as the data files
    grades_file = "gradesMachineReadable.csv"
    codebook_file = "codebookMachineReadable.csv"
    output_dir = "."
    analyze_grades(grades_file, codebook_file, output_dir)