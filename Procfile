web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
worker: uvicorn backend.main:app --host 0.0.0.0 --port ${BACKEND_PORT:-8000}
