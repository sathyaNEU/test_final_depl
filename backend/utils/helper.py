import requests
import os 
from datetime import datetime

def trigger_dag_qa_datagen_pipeline(pipeline, params):
    AIRFLOW_BASE_URL, AIRFLOW_USERNAME, AIRFLOW_PASSWORD = os.getenv('AIRFLOW_BASE_URL'), os.getenv('AIRFLOW_USERNAME'), os.getenv('AIRFLOW_PASSWORD')
    # AIRFLOW_BASE_URL, AIRFLOW_USERNAME, AIRFLOW_PASSWORD = "http://34.59.146.190:8081/api/v1", os.getenv('AIRFLOW_USERNAME'), os.getenv('AIRFLOW_PASSWORD')
    url = f"{AIRFLOW_BASE_URL}/dags/{pipeline}/dagRuns"  
    response = requests.post(
        url,
        auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        headers={"Content-Type": "application/json"},
        json={ "conf": params }  
    )
    if response.status_code in [200, 201]:  # 201 = Created, 200 = Success
        return {"message": f"System is currently processing your request", "response": response}
    else:
        return {"message": f"Request failed", "response": response}
    


def report_ready_data(state_before_llm, state_after_llm):
    if isinstance(state_after_llm, int):
        return [
        {
            'question':pair['question'],
            'user_answer':pair['user_answer'],
            'actual_answer': pair['actual_answer'],
            'llm_feedback': 'No Feedback Provided'
        }
        for pair in state_before_llm  
        ]
       
    else:
        feedback_lookup = {item['id']: item['review'] for item in state_after_llm}
        return [
        {
            'question':pair['question'],
            'user_answer':pair['user_answer'],
            'actual_answer': pair['actual_answer'],
            'llm_feedback': feedback_lookup.get(pair['id'], 'No Feedback Provided')
        }
        for pair in state_before_llm  
        ]



def generate_quiz_report_md(user_name: str, quiz_title: str, feedback_data: list) -> str:
    quiz_date = datetime.now().strftime("%B %d, %Y")
    
    md_lines = [
        f"# 📝 Quiz Feedback Report",
        f"**Name:** {user_name}",
        f"**Quiz Title:** {quiz_title}",
        f"**Date:** {quiz_date}",
        "\n---\n"
    ]
 
    for i, item in enumerate(feedback_data, 1):
        md_lines.extend([
            f"## Question {i}: {item['question']}",
            f"**Your Answer:**\n{item['user_answer']}",
            f"\n**Correct Answer:**\n{item['actual_answer']}",
            f"\n**Feedback:**\n> {item['llm_feedback']}",
            "\n---\n"
        ])
    return "\n".join(md_lines)


def prompt_for_json(data):
    return f"""

            Convert the following text into structured JSON. Do **not** add any triple quotes ('''), `json\\n`, or newline characters (`\\n`) at the start of the JSON output. Refer to the example format below 
            also map all links available with repective values:

            {{
            "name": "name",
            "phone": "number",
            "email": "email",
            "location": "Boston, MA, 02120",
            "LinkedIn": "url",
            "GitHub": "url",
            "education": [],
            "skills": [ {{if category is present make it as key and items as value}} ],
            "work_experience": [],
            "projects": []
            }}

            Text: {data['text']}
            Links: {data['links']}

        """



sys_qa_validation_prompt = """
You are a precise and fair assistant helping evaluate user answers to interview questions. You will be given a list of question-answer entries. Each entry includes:
 
- `id`: a unique identifier
- `question`: the interview question
- `actual_answer`: the correct answer
- `user_answer`: the answer provided by the user
 
Your job is to return a JSON list of evaluations. For each entry:
- Give encouraging and constructive feedback.
- If the user's answer is mostly or fully correct, acknowledge it and reinforce their understanding.
- If the answer is partially correct, point out what was right and what was missing.
- If incorrect, kindly explain why and provide a correct step-by-step explanation.
- Avoid demotivating tone. Use phrasing like “You’re almost there…” or “Good attempt, but…” when needed.
- Focus on clarity and helpfulness. Don't restate the question unless needed in the explanation.
 
### Output Schema:
Return a list of objects with:
- `"id"`: the same ID from input
- `"review"`: the evaluation and feedback string
 
Respond only with valid JSON.
"""
 
 
user_qa_validation_prompt = """
Here is a list of user answers with questions and correct answers.
Please validate each item and return feedback in the required format.
 
Input:
 
{}
 
"""