import sys
from _datetime import datetime
import requests
import logging

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def build_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


def generate_test(api_key, url, learned_today):
    headers = build_headers(api_key)

    data = {
        "model": "openrouter/auto",
        "messages": [
            {
                "role": "system",
                "content": """
                                You are a study assistant that creates tests from study material.

                                Rules:
                                - Use only the material provided by the user
                                - Do not add outside knowledge
                                - Create exactly 5 questions
                                - The test must include:
                                  * exactly 2 multiple-choice questions
                                  * exactly 2 short-answer questions
                                  * exactly 1 conceptual question
                                - Multiple-choice questions must include 4 options: a, b, c, d
                                - Do not write the type of question
                                - Questions should test understanding, not just memorization
                                - Avoid copying sentences directly from the text
                                - The order of the question types should vary each time
                                - Create the answers for the questions
                                Format:

                                Test:
                                1.
                                2.
                                3.
                                4.
                                5.

                                Answer Key:
                                1.
                                2.
                                3.
                                4.
                                5.

                                Before finishing, verify that:
                                - There are exactly 5 questions
                                - Exactly 2 questions contain answer options (a, b, c, d)
                                If the conditions are not satisfied, regenerate the test.
                                """
            },
            {
                "role": "user",
                "content": f"""Create a test based on the following material.

                                    Material:
                                    {learned_today}
                                """
            }
        ]
    }

    logging.info("Sending request to generate test.")

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        full_output = result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        raise
    except ValueError as e:
        logging.error(f"Invalid JSON response: {e}")
        raise
    except (KeyError, IndexError) as e:
        logging.error(f"Unexpected response format: {e}")
        raise
    logging.info("Received response from test generation API.")
    return full_output


def collect_answers():
    answers = []
    for i in range(1, 6):
        logging.info(f"Waiting for student input for question {i}.")
        answers.append(input(f"Answer for question {i}:\n"))
    logging.info("Collected 5 student answers.")
    student_answers = ""
    for i, ans in enumerate(answers, start=1):
        student_answers += f"{i}. {ans}\n"
    return student_answers


def grade_test(api_key, url, learned_today, questions, student_answers, answer_key):
    headers = build_headers(api_key)
    data_grade = {
        "model": "openrouter/auto",
        "messages": [
            {
                "role": "system",
                "content":
                    """
                    You are an exam grading assistant.

                    The user already received a test based on some study material and answered the questions.

                    You will receive:
                    1. The study material
                    2. The questions
                    3. The student's answers
                    4. The correct answers

                    Your task is to determine the grade of the student based on his answers.

                    Grading rules:
                    - Each question is graded from 0 to 20 points.
                    - If the answer is blank → 0 points
                    - If a question is multiple-choice:
                      - Correct answer → 20 points
                      - Incorrect answer → 0 points
                    - For open questions:
                      - Give a score between 0 and 20 depending on how close the student's answer is to the correct answer.
                      - You can give any score between 0 and 20.
                      - The score does not have to be a multiple of 5.

                    For each question you must:
                    - Compare the correct answer with the student's answer
                    - Give a score from 0–20
                    - Explain briefly why the score was given and why it was not higher or lower.

                    Important rules:
                    - Use only the provided study material and answer key to determine the score.
                    - Do not use outside knowledge.
                    - Be fair and consistent.

                    Return the result exactly in this format:

                    Question 1:
                    Student Answer:
                    Correct Answer:
                    Score: X/20
                    Explanation:

                    Question 2:
                    Student Answer:
                    Correct Answer:
                    Score: X/20
                    Explanation:

                    Question 3:
                    Student Answer:
                    Correct Answer:
                    Score: X/20
                    Explanation:

                    Question 4:
                    Student Answer:
                    Correct Answer:
                    Score: X/20
                    Explanation:

                    Question 5:
                    Student Answer:
                    Correct Answer:
                    Score: X/20
                    Explanation:

                    Final Score: X/100

                    """
            },
            {
                "role": "user",
                "content": f"""Give the score based on the following material, questions, answers:

                    Material:
                    {learned_today}
                    Questions:
                    {questions}
                    Student Answers:
                    {student_answers}
                    Answer Key:
                    {answer_key}
                    """
            }
        ]
    }
    logging.info("Sending request to grade test.")
    try:
        grading = requests.post(url, headers=headers, json=data_grade)
        grading.raise_for_status()
        score = grading.json()
        score = score["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        raise
    except ValueError as e:
        logging.error(f"Invalid JSON response: {e}")
        raise
    except (KeyError, IndexError) as e:
        logging.error(f"Unexpected response format: {e}")
        raise
    logging.info("Received response from grading API.")
    return score


def main():
    logging.info("Starting Project.")

    api_key =input("Enter API Key.\n")
    url = "https://openrouter.ai/api/v1/chat/completions"
    learned_today = """
    Enter All The Information Learned.
    """

    full_output = ""
    for i in range(3):
        if "Answer Key:" not in full_output:
            if i != 0:
                logging.warning("Generated test does not contain Answer Key.")
                logging.info(f"Generating Test. Attempt {i + 1}.")
            else:
                logging.info("Generating Test.")
            full_output = generate_test(api_key, url, learned_today)

    if "Answer Key:" in full_output:
        logging.info("Test Generated Successfully.")
    else:
        logging.error("Failed to generate test after 3 attempts. Exiting program.")
        sys.exit(1)

    questions, _, answer_key = full_output.partition("Answer Key:")
    logging.info("Displaying generated test to user.")
    print(questions)

    logging.info("Collecting User Answers.")
    student_answers = collect_answers()
    logging.info("Answers Collected Successfully.")

    logging.info("Starting Grading Process.")
    grading = grade_test(api_key, url, learned_today, questions, student_answers, answer_key)
    logging.info("Finished Grading Process.")
    logging.info("Displaying grading result to user.")
    print(grading)
    with open("history.txt", "a", encoding="utf-8") as f:
        f.write("=== New Test ===\n")
        f.write(f"Date: {datetime.now()}\n")
        f.write(f"{grading}\n")
    logging.info("Finished Project.")


if __name__ == "__main__":
    main()