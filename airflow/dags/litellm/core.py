from litellm import completion
from datetime import datetime
from airflow.models import Variable

def llm(model, system_prompt, user_prompt=None):
    api_key = Variable.get("GEMINI_API_KEY")
    if user_prompt:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    else:
        messages = [{"role": "user", "content": system_prompt}]

    response = completion(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=10000,
            response_format={"type": "json_object"},
            api_key=api_key
        )
    
    return {
        'id': response.id,
        'prompt': user_prompt or system_prompt,
        'answer': response.choices[0].message.content,
        'model': response.model,
        'prompt_tokens': response.usage.prompt_tokens,
        'completion_tokens': response.usage.completion_tokens,
        'created': datetime.fromtimestamp(response.created).strftime('%Y-%m-%d %H:%M:%S')
    }

    
def llm_deepseek(model, system_prompt, user_prompt=None):
    api_key = Variable.get("DEEPSEEK_API_KEY")

    if user_prompt:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    else:
        messages = [{"role": "user", "content": system_prompt}]

        response = completion(
            model=model,
            messages=messages,
            temperature=0.5,
            max_tokens=8000,
            api_key=api_key
        )

    return {
        'id': response.id,
        'prompt': user_prompt or system_prompt,
        'answer': response.choices[0].message.content,
        'model': response.model,
        'prompt_tokens': response.usage.prompt_tokens,
        'completion_tokens': response.usage.completion_tokens,
        'created': datetime.fromtimestamp(response.created).strftime('%Y-%m-%d %H:%M:%S')
    }