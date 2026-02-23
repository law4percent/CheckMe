def compare_answers(
    student_answers: dict,
    answer_key_data: dict
) -> tuple:
    """
    Compare student answers against the answer key.

    Returns:
        (score, total_questions, breakdown_dict)
    """
    answer_key = answer_key_data.get("answer_key", {})
    total = len(answer_key)
    score = 0
    breakdown = {}

    for q_num, correct_answer in answer_key.items():
        student_answer = student_answers.get(q_num, "missing_answer")
        is_correct = student_answer == correct_answer

        breakdown[q_num] = {
            "student": student_answer,
            "correct": correct_answer,
            "is_correct": is_correct,
        }

        if is_correct:
            score += 1

    return score, total, breakdown