"""Curated RAG knowledge base. Resources only reference well-known official/public material."""

def _lr(skill, title, content):
    return {"title": title, "category": "learning_resource", "skill": skill, "content": content}


KNOWLEDGE_DOCS = [
    # ------------------------- learning resources (tagged per skill)
    _lr("Python", "Learning Python for ML and backend", "Work through the official Python tutorial (docs.python.org/3/tutorial), then build 2-3 small CLI/API projects. Focus on functions, classes, comprehensions, virtual environments and typing."),
    _lr("SQL", "Learning SQL", "Practise joins, GROUP BY, window functions and CTEs on a real database (PostgreSQL). Solve 30+ query problems on a public SQL practice site and model a small schema of your own."),
    _lr("Machine Learning", "Machine Learning fundamentals", "Cover supervised vs unsupervised learning, bias-variance, regularisation, evaluation metrics and cross-validation. Andrew Ng's Machine Learning Specialization on Coursera and the scikit-learn user guide are standard references."),
    _lr("Scikit-learn", "Scikit-learn practice", "Use the scikit-learn user guide and tutorials: pipelines, ColumnTransformer, GridSearchCV, metrics. Reproduce a Kaggle tabular competition with a clean Pipeline."),
    _lr("Deep Learning", "Deep Learning foundations", "Learn backpropagation, CNNs, RNNs and optimisation. Andrej Karpathy's 'Neural Networks: Zero to Hero' videos and the fast.ai Practical Deep Learning course are excellent, free starting points."),
    _lr("PyTorch", "PyTorch learning path", "Follow the official PyTorch tutorials (pytorch.org/tutorials): tensors, autograd, nn.Module, DataLoader, training loops. Then re-implement a CNN classifier and a small text model from scratch."),
    _lr("TensorFlow", "TensorFlow and Keras", "The official TensorFlow/Keras guides cover model building, tf.data and callbacks. Prioritise PyTorch unless a job explicitly requires TensorFlow."),
    _lr("Docker", "Docker for developers", "Follow Docker's official 'Get Started' guide (docs.docker.com/get-started). Containerise a FastAPI app, write a multi-stage Dockerfile and a docker-compose file with Postgres and Redis."),
    _lr("Kubernetes", "Kubernetes basics", "Use the official Kubernetes tutorials (kubernetes.io/docs/tutorials) with minikube or kind: pods, deployments, services, config maps, ingress."),
    _lr("FastAPI", "FastAPI learning path", "The official FastAPI tutorial (fastapi.tiangolo.com/tutorial) is excellent: path/query params, Pydantic models, dependency injection, auth with JWT, background tasks and testing."),
    _lr("REST APIs", "REST API design", "Learn resource modelling, HTTP verbs and status codes, pagination, versioning and idempotency. Build a CRUD API with validation, auth and OpenAPI docs."),
    _lr("MLOps", "MLOps essentials", "Learn experiment tracking (MLflow), model packaging, serving behind an API, CI/CD for models, drift monitoring. 'Made With ML' (madewithml.com) is a practical, free end-to-end course."),
    _lr("Git", "Git and GitHub workflow", "Practise branching, rebasing, pull requests and resolving conflicts. The Pro Git book (git-scm.com/book) is free and complete."),
    _lr("Statistics", "Statistics for data science", "Study distributions, hypothesis testing, confidence intervals, A/B testing and Bayesian basics. Khan Academy statistics and 'Think Stats' (free) are solid."),
    _lr("Pandas", "Pandas practice", "Work through the official pandas user guide: indexing, groupby, merge, time series. Clean a messy real dataset end to end."),
    _lr("Large Language Models", "LLM fundamentals", "Understand tokenisation, context windows, sampling parameters and failure modes. Hugging Face's LLM course (huggingface.co/learn) and provider documentation are good starting points."),
    _lr("RAG", "Retrieval-Augmented Generation", "Build a RAG app: chunking, embeddings, a vector store (pgvector/FAISS), retrieval, reranking and grounded prompts. Evaluate retrieval quality (recall@k) and answer faithfulness."),
    _lr("LangGraph", "LangGraph for agents", "The LangGraph documentation covers StateGraph, conditional edges, tool nodes and persistence. Build a multi-step agent with an explicit state object."),
    _lr("LangChain", "LangChain basics", "Use LangChain documentation for chains, retrievers and tool calling; keep prompts and tools simple and testable."),
    _lr("Vector Databases", "Vector databases", "Learn embeddings, cosine similarity, ANN indexes (HNSW, IVF). pgvector inside PostgreSQL is a pragmatic choice for projects."),
    _lr("Hugging Face", "Hugging Face ecosystem", "The Hugging Face NLP/LLM course (huggingface.co/learn) covers Transformers, Datasets, tokenizers and fine-tuning."),
    _lr("NLP", "NLP roadmap", "Cover tokenisation, TF-IDF, embeddings, sequence labelling and transformers. Fine-tune a BERT-style classifier on a public dataset."),
    _lr("React", "React learning path", "The official React documentation (react.dev) teaches components, state, effects and data fetching. Build a dashboard consuming a real API."),
    _lr("JavaScript", "JavaScript fundamentals", "Learn closures, promises/async-await, array methods and the DOM through javascript.info, then build small interactive apps."),
    _lr("Data Structures & Algorithms", "DSA preparation", "Practise arrays, hashing, trees, graphs, DP and sliding window; solve 150+ problems on a coding platform with timed practice."),
    _lr("PostgreSQL", "PostgreSQL practice", "Use the official PostgreSQL tutorial: indexes, EXPLAIN, transactions, JSONB and extensions such as pgvector."),
    _lr("CI/CD", "CI/CD pipelines", "Build a GitHub Actions workflow that lints, tests, builds a Docker image and deploys on merge."),
    _lr("Computer Vision", "Computer vision roadmap", "Cover image classification with CNNs, transfer learning, detection (YOLO-style) and augmentation using PyTorch/torchvision."),
    _lr("Feature Engineering", "Feature engineering", "Practise encoding, scaling, missing-value strategies, target leakage avoidance and feature importance analysis."),
    _lr("Model Evaluation", "Model evaluation", "Know precision/recall/F1, ROC-AUC, PR curves, calibration and proper cross-validation; always keep a leakage-free hold-out set."),
    # ------------------------- role overviews
    {"title": "What an ML Engineer does", "category": "role_overview", "skill": None,
     "content": "ML Engineers turn models into reliable products: data pipelines, training code, evaluation, packaging with Docker, serving with APIs and monitoring drift. Strong Python, ML fundamentals, deep learning frameworks and MLOps practices are expected."},
    {"title": "What a Data Scientist does", "category": "role_overview", "skill": None,
     "content": "Data Scientists frame business questions, analyse data with statistics, build predictive models and communicate findings. SQL, Python, statistics and storytelling matter as much as modelling."},
    {"title": "What an AI Engineer does", "category": "role_overview", "skill": None,
     "content": "AI Engineers build LLM-powered products: prompt design, RAG pipelines, tool-using agents, evaluation of answer quality and cost/latency optimisation, usually behind FastAPI services."},
    # ------------------------- resume guidelines
    {"title": "Resume bullet formula", "category": "resume_guideline", "skill": None,
     "content": "Write bullets as: Action verb + what you built + technology + measurable result. Example pattern: 'Built a churn model with scikit-learn that improved recall by 12% on 50k records.' Avoid 'responsible for' and 'worked on'."},
    {"title": "ATS-friendly resume formatting", "category": "resume_guideline", "skill": None,
     "content": "Use a single column, standard headings (Education, Skills, Projects, Experience), no text inside images or tables, a standard font, and keep keywords that match the job description. Export as PDF unless the portal asks otherwise."},
    {"title": "Resume for freshers", "category": "resume_guideline", "skill": None,
     "content": "Lead with Education and Projects. Show 2-4 strong projects with links to GitHub, tools used and measurable outcomes. Add internships, hackathons and certifications relevant to the target role. Keep it to one page."},
    # ------------------------- interview tips
    {"title": "STAR method for behavioural answers", "category": "interview_tip", "skill": None,
     "content": "Structure answers as Situation, Task, Action, Result. Spend most time on your specific actions and the measurable result, and finish with what you learned."},
    {"title": "Explaining ML projects in interviews", "category": "interview_tip", "skill": None,
     "content": "Be ready to justify every choice: why this model, how you validated it, what baselines you tried, which metric and why, what failed, and how you would deploy and monitor it."},
    {"title": "Technical answer structure", "category": "interview_tip", "skill": None,
     "content": "Define the concept briefly, explain how it works, give a concrete example, then discuss trade-offs and when you would not use it. Mention the dataset or project where you applied it."},
    # ------------------------- career guides
    {"title": "Building a job-ready portfolio", "category": "career_guide", "skill": None,
     "content": "Two or three deployed, well-documented projects beat ten notebooks. Include a README with problem, approach, results and a live demo or Docker instructions, plus tests and an evaluation section."},
    {"title": "Applying effectively", "category": "career_guide", "skill": None,
     "content": "Tailor the resume to each posting, prioritise roles where you match about 60-80% of requirements, reach out to referrers, and track every application with its status and follow-up date."},
    {"title": "Closing skill gaps efficiently", "category": "career_guide", "skill": None,
     "content": "Prioritise skills that appear most often in your target job listings. Learn by building: pair every new skill with a small project you can show on your resume."},
]
