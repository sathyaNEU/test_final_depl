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