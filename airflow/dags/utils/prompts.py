sys_qa_datagen_prompt = """
You are an intelligent assistant designed to extract structured information from unstructured markdown text. The input contains interview questions and answers about a specific skill, written in markdown format from a website.

Your task is to parse the content and return a clean JSON object with a list of questions and their corresponding answers.

### Instructions:
- Only extract **question-answer** pairs that are explicitly present in the markdown content.
- Do **NOT** generate or create new questions or answers on your own.
- Limit the output to a **maximum of 10** question-answer pairs.
- It is acceptable to return **fewer than 10** if the markdown does not contain enough valid QA pairs.
- Ignore any headers, footers, metadata, or formatting like `#`, `*`, `**`, or code blocks unless they are part of the actual answer.
- Each item must contain:
  - `"question"`: the text of the question (string)
  - `"answer"`: the full text of the answer (string)
- Preserve the **full detail** in answers, including examples and explanations.
- Clean the text: remove markdown characters but keep formatting where it helps readability.
- Skip unrelated content that isn't a question or answer.
- Ensure the result is in **valid JSON** format with the key `qa_pairs` that maps to an array of question-answer objects.

### Example Output:
```json
{
  "qa_pairs": [
    {
      "question": "What is Python?",
      "answer": "Python is a high-level, interpreted programming language known for its readability and versatility."
    },
    {
      "question": "What are Python's key features?",
      "answer": "Key features include dynamic typing, garbage collection, extensive standard libraries, and support for multiple programming paradigms."
    }
  ]
}
"""

user_qa_datagen_prompt = """
Here is the markdown content from a website that contains interview questions and answers for {}.

Markdown content:
---
{}
---
"""


sys_skill_extract_prompt = """
Extract ONLY the explicit technical skills from this job description: {}

Focus exclusively on hard technical skills that are directly mentioned as requirements or desired qualifications, such as:
- Programming languages (Python, Java, C++, etc.)
- Software tools and platforms (AWS, Docker, Kubernetes, etc.)
- Technical frameworks and libraries (React, TensorFlow, etc.)
- Database technologies (SQL, MongoDB, etc.)
- Operating systems (Linux, Windows Server, etc.)
- Technical methodologies (CI/CD, Agile, etc.)

IMPORTANT RULES:
1. Do NOT extract parts of words. For example, do not extract "Scala" from "scalable" or "C" from "C++".
2. Do NOT infer skills that aren't explicitly mentioned.
3. Only include skills that are clearly technical tools, languages, platforms, or methodologies.
4. DO NOT include soft skills like communication, leadership, problem-solving, etc.
5. Extract the exact skill as mentioned (preserve capitalization).
6. Distinguish between similar technologies (e.g., React vs React Native, Java vs JavaScript).

Return the result as a valid JSON object with a single 'technical_skills' key containing an array of skill strings. The array should be empty if no technical skills are found.
"""