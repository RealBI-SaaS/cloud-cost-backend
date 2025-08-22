
Installation
------------
To install NumLock locally, follow these steps:

1. **Clone the frontend repository**:

   .. code-block:: bash

       git clone https://github.com/RealBI-SaaS/cloud-cost-saas.git
       cd cloud-cost-saas

2. **Install frontend packages**:

   .. code-block:: bash

       npm install

3. **Run the frontend app**:

   .. code-block:: bash

       npm run dev

4. **Clone the backend repository**:

   .. code-block:: bash

       git clone https://github.com/RealBI-SaaS/cloud-cost-backend.git
       cd cloud-cost-backend

5. **Setup backend environment**:

   - Rename `.env_example` to `.env` and add all required values.  
   - Create a virtual environment:

     .. code-block:: bash

         python -m venv venv
         source venv/bin/activate   # Linux/macOS
         # .\venv\Scripts\activate  # Windows

   - Install backend packages:

     .. code-block:: bash

         pip install -r requirements.txt

6. **Run backend migrations**:

   .. code-block:: bash

       python manage.py migrate

7. **Run the backend server**:

   .. code-block:: bash

       python manage.py runserver

8. **Open the frontend app in your browser**:

   Go to: `http://localhost:5173`
4. Run Sphinx locally:

   .. code-block:: bash

       cd docs
       make html



