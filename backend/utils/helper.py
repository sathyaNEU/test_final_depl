
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