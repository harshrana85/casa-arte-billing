# Casa Arte Privée Billing System

## Run locally
pip install -r requirements.txt
streamlit run app.py

## Deploy on Streamlit Cloud
1. Upload these files to a GitHub repository.
2. Go to Streamlit Cloud.
3. Create New App.
4. Select this repo.
5. Main file path: app.py
6. Deploy.

## Storage
This version uses local JSON storage:
- data/customers.json
- data/documents.json
- data/settings.json

For permanent multi-user cloud storage, upgrade to Supabase later.
