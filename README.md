# Project Title

## Introduction


## Installation Guide
To install this project, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone .git link
   ```

2. **Navigate to the project directory**:
   ```bash
   cd yourproject
   ```

3. **Set up a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   ```

4. **Activate the virtual environment**:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

5. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

6. **add your environment variables**:
   *** add your variable to .example_env and rename .eample_env to .env
   
6. **Migrate your db**:
   ```bash
   python manage.py migrate
   ```

6. **Run the application**:
   ```bash
   python manage.py runserver
   ```
