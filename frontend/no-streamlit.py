import streamlit as st

# Sample questions
questions = [
    "What is your name?",
    "What is your favorite color?",
    "What is your favorite food?",
    "Where do you live?",
    "What is your hobby?"
]

# Initialize session state
if "question_index" not in st.session_state:
    st.session_state.question_index = 0
if "answers" not in st.session_state:
    st.session_state.answers = [""] * len(questions)

# Current question
index = st.session_state.question_index
st.markdown(f"### Question {index + 1}")
st.write(questions[index])

# Answer input
answer = st.text_input("Your answer:", value=st.session_state.answers[index])

# Update answer in session
st.session_state.answers[index] = answer

# Navigation
col1, col2 = st.columns([1, 2])
with col1:
    if index < len(questions) - 1:
        if st.button("Next"):
            st.session_state.question_index += 1
    else:
        if st.button("Submit"):
            st.success("All answers submitted!")
            st.write("### Your Answers:")
            for i, ans in enumerate(st.session_state.answers):
                st.write(f"**Q{i+1}:** {questions[i]}")
                st.write(f"**A{i+1}:** {ans}")

with col2:
    if index > 0:
        if st.button("Previous"):
            st.session_state.question_index -= 1
