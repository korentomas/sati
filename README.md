# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the development server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Option 2: Using the Makefile

# Install dependencies
make install

# Run development server
make dev

Option 3: Using Docker

# Build and run all services (API, Redis, PostgreSQL)
make up

# Or manually:
docker-compose up --build

Testing the API

Once running, you can:

1. View Swagger docs: http://localhost:8000/api/v1/docs
2. Test authentication:
- Login with: user@example.com / secret
- Generate API keys after getting a token
3. Health checks:
- http://localhost:8000/api/v1/health/live
- http://localhost:8000/api/v1/health/ready

The API will be available at http://localhost:8000 with full OpenAPI
documentation.
