from .logger import get_logger

log = get_logger("scorer.py")

def compare_answers(
    student_answers: dict,
    answer_key_data: dict
) -> tuple:
    """
    Compare student answers against the answer key.

    Returns:
        (score, total_questions, breakdown_dict)
    """
    answer_key      = answer_key_data.get("answer_key", {})
    total           = int(answer_key_data.get("total_questions", 0))
    score           = 0
    breakdown       = {}
    is_final_score  = True

    total_answer_keys = len(answer_key)
    found_warning = False
    if total != total_answer_keys:
        log(
            "\nTotal questions is not same to quantity to total answer_key", 
            f"\ntotal_questions: {total}",
            f"\total_answer_keys: {total_answer_keys}",
            log_type="warning"
        )
        found_warning = True

    for q_num, correct_answer in answer_key.items():
        student_answer  = student_answers.get(q_num, "missing_answer")
        
        checking_result = student_answer == correct_answer
        
        if student_answer == "essay_answer":
            is_final_score = False
            breakdown[q_num] = {
                "student_answer"    : student_answer,
                "correct_answer"    : "will_check_by_teacher",
                "checking_result"   : "pending",
            }
        else:
            breakdown[q_num] = {
                "student_answer"    : student_answer,
                "correct_answer"    : correct_answer,
                "checking_result"   : checking_result,
            }

            if checking_result:
                score += 1

    return score, total, breakdown, is_final_score, found_warning