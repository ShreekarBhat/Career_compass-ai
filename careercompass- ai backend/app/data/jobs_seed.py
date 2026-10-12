"""Seed job postings so the system works with zero external API keys (illustrative listings)."""

def _j(i, title, company, location, remote, level_hint, desc, url="https://example.com/jobs"):
    return {"source": "seed", "external_id": f"seed-{i}", "title": title, "company": company,
            "location": location, "remote": remote, "description": f"{level_hint} {desc}", "url": f"{url}/{i}"}


SEED_JOBS = [
    _j(1, "Machine Learning Engineer Intern", "Nimbus AI Labs", "Bengaluru, India", False, "Internship.",
       "Work on training and deploying ML models. Requirements: Python, Machine Learning, Scikit-learn, Pandas, SQL, Git. "
       "Nice to have: PyTorch, Docker, REST APIs."),
    _j(2, "ML Engineer", "Orbit Analytics", "Bengaluru, India", False, "2+ years experience.",
       "Own the model lifecycle from experimentation to production. Requirements: Python, PyTorch, Deep Learning, MLOps, Docker, "
       "FastAPI, AWS, SQL, Model Evaluation, Git."),
    _j(3, "Data Scientist - Entry Level", "Quanta Retail", "Hyderabad, India", False, "Entry level / fresher.",
       "Build forecasting and customer-segmentation models. Requirements: Python, SQL, Statistics, Pandas, NumPy, Scikit-learn, "
       "Data Visualization, Feature Engineering."),
    _j(4, "Generative AI Engineer", "Lumen Systems", "Remote (India)", True, "1-3 years experience.",
       "Build RAG pipelines and LLM agents for enterprise clients. Requirements: Python, Large Language Models, RAG, LangChain, "
       "LangGraph, Vector Databases, FastAPI, Prompt Engineering, Docker, Git."),
    _j(5, "AI Engineer Intern", "Helix Robotics", "Pune, India", False, "Internship.",
       "Prototype AI features with LLMs and computer vision. Requirements: Python, Machine Learning, Deep Learning, PyTorch, "
       "Computer Vision, Git. Docker is a plus."),
    _j(6, "Backend Developer (Python)", "Cartwheel Commerce", "Bengaluru, India", False, "1-3 years experience.",
       "Build scalable APIs for our marketplace. Requirements: Python, FastAPI, PostgreSQL, REST APIs, Docker, Redis, Authentication, "
       "Testing, Git, System Design."),
    _j(7, "Full Stack Developer", "Brightpath EdTech", "Chennai, India", False, "2+ years experience.",
       "Ship features across our React and Node.js stack. Requirements: JavaScript, TypeScript, React, Node.js, HTML/CSS, "
       "REST APIs, MongoDB, Git, Testing."),
    _j(8, "Data Analyst", "Fintrek", "Mumbai, India", False, "Entry level.",
       "Create dashboards and weekly business reports. Requirements: SQL, Excel, Power BI, Python, Pandas, Data Visualization, "
       "Statistics."),
    _j(9, "DevOps Engineer", "Stackwise Cloud", "Remote (India)", True, "3+ years experience.",
       "Run CI/CD and Kubernetes clusters. Requirements: Linux, Docker, Kubernetes, CI/CD, Terraform, AWS, Bash, Monitoring, Git."),
    _j(10, "NLP Engineer", "Verbatim Labs", "Bengaluru, India", False, "2+ years experience.",
       "Build text classification and summarisation systems. Requirements: Python, NLP, Transformers, Hugging Face, PyTorch, "
       "Deep Learning, Docker, FastAPI."),
    _j(11, "Data Engineer", "Streamline Data", "Gurugram, India", False, "2-4 years experience.",
       "Design batch and streaming pipelines. Requirements: Python, SQL, ETL, Apache Spark, Apache Airflow, Apache Kafka, "
       "Data Warehousing, AWS."),
    _j(12, "Software Engineer - New Grad", "Pixelcraft", "Bengaluru, India", False, "Fresher / graduate.",
       "Join our core platform team. Requirements: Data Structures & Algorithms, OOP, Java, SQL, Git, REST APIs, Testing."),
    _j(13, "Machine Learning Intern (Computer Vision)", "Sightline Systems", "Remote (India)", True, "Internship.",
       "Help build image classification models. Requirements: Python, Computer Vision, Deep Learning, PyTorch, NumPy, Git."),
    _j(14, "MLOps Engineer", "Pipeline Forge", "Bengaluru, India", False, "3+ years experience.",
       "Productionise ML systems. Requirements: MLOps, Docker, Kubernetes, CI/CD, Python, AWS, Monitoring, FastAPI, Git."),
    _j(15, "Junior Data Scientist", "Insightly", "Remote (India)", True, "Junior, 0-2 years.",
       "Work on predictive models for logistics. Requirements: Python, Machine Learning, Scikit-learn, XGBoost, SQL, Pandas, "
       "Feature Engineering, Model Evaluation."),
]
