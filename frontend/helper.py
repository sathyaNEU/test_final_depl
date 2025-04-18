css = """
<style>
    .job-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 25px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .job-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .job-title {
        color: #2c3e50;
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .job-company {
        color: #3498db;
        font-weight: bold;
        font-size: 18px;
        margin-bottom: 8px;
    }
    .job-meta {
        margin-bottom: 10px;
        font-size: 14px;
        color: #555;
    }
    .job-role-tag {
        display: inline-block;
        background-color: #e1f5fe;
        color: #0288d1;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 13px;
        margin-right: 5px;
    }
    .job-date {
        color: #7f8c8d;
        font-size: 14px;
        margin-top: 5px;
        margin-bottom: 15px;
    }
    .job-buttons {
        display: flex;
        gap: 10px;
        margin-top: 15px;
    }
    .view-button, .prep-button {
        display: inline-block;
        padding: 8px 16px;
        text-decoration: none !important;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
        border: none;
        cursor: pointer;
        transition: background-color 0.2s;
        color: white !important;
    }
    .view-button {
        background-color: #3498db;
    }
    .view-button:hover {
        background-color: #2980b9;
    }
    .prep-button {
        background-color: #2ecc71;
    }
    .prep-button:hover {
        background-color: #27ae60;
    }

    .skills-title {
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 10px;
        color: #3498db;
    }
    .skill-tag {
        display: inline-block;
        background-color: #e8f4fc;
        color: #3498db;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 13px;
        margin-right: 5px;
        margin-bottom: 5px;
    }
</style>
"""