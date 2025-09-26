Installation
============

1. **Clone the repository**

   .. code-block:: bash

      git clone https://github.com/RealBI-SaaS/cloud-cost-backend.git
      cd cloud-cost-backend


2. **Configure environment variables**

   Rename the provided example file:

   .. code-block:: bash

      mv .env.example .env

   Then edit ``.env`` and add the required values.


3. **Install dependencies**

   You have three options:

   A. **Using Docker**

   1. Build the Docker image:

      .. code-block:: bash

         docker build -t numlock-backend .

   2. Run the container:

      .. code-block:: bash

         docker run -p 8000:8000 numlock-backend

      The service will be available at: ``http://localhost:8000``

   **Using Docker Compose**  
   If you also want to run Prometheus and Grafana alongside the backend:

   .. code-block:: bash

      docker-compose up

   - Backend: ``http://localhost:8000``  
   - Prometheus: ``http://localhost:9090``  
   - Grafana: ``http://localhost:3000``


   B. **Using pip (virtual environment)**

   1. Create and activate a virtual environment (Linux/Unix):

      .. code-block:: bash

         python3 -m venv .venv
         source .venv/bin/activate

   2. Install packages:

      .. code-block:: bash

         pip install -r requirements.txt

   3. Run the development server:

      .. code-block:: bash

         python3 manage.py runserver


   C. **Using uv**

   .. code-block:: bash

      uv add -r requirements.txt
      uv run manage.py runserver


4. **Build documentation locally**

   To generate Sphinx docs:

   .. code-block:: bash

      cd docs
      make html
