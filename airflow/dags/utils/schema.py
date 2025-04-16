from pydantic import BaseModel, ValidationError
from typing import List

class QAItem(BaseModel):
    question: str
    answer: str


class QAList(BaseModel):
    qa_pairs: List[QAItem]
    
def validate_qa_data(qa_response):
    try:
        # Attempt to validate and create a QAList object
        validated = QAList(**qa_response)
        return validated.model_dump()  # Return the validated data as a dictionary
    except ValidationError:
        # If validation fails, return an empty list
        return []