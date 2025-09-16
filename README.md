# 💳 Banking Simulation App

A full-stack demo banking system with a **Flask + SQLAlchemy backend** and a **React + Vite + Tailwind frontend**.  
It simulates customers, accounts, transfers, and merchant payments with a REST API and modern UI.

---

## 📂 Project Structure

```
.
├── app.py                  # Flask backend API
├── load_csv_into_ultipa.py # Script to import CSV data into DB
├── App.jsx                 # React frontend app
├── requirements.txt        # Python dependencies
├── package.json            # Node + Vite dependencies
├── .env                    # Environment variables
```

---

## ⚙️ Backend (Flask API)

### Features
- REST endpoints for **accounts, balances, transfers, payments, merchants, and customer transactions**  
- SQLite database (configurable via `.env`)  
- Simple seeding API with `X-Seed-Token` for demo data  
- CORS enabled for frontend integration  

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows

# Install requirements
pip install -r requirements.txt

# Run Flask server
python app.py
```

By default the server runs at:  
👉 `http://localhost:5050`

---

## 🎨 Frontend (React + Vite + Tailwind)

### Features
- Account selector with real-time **balance**  
- Transfer form (between accounts)  
- Pay form (search & pay merchants)  
- Recent transactions list with customer switcher  
- Styled with TailwindCSS for clean UI  

### Setup
```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

By default the UI runs at:  
👉 `http://localhost:5173`

---

## 🗄️ Database Utilities

- `load_csv_into_ultipa.py`: Import CSV data into the database with customers, accounts, merchants, transfers, and pays  

Example:
```bash
python load_csv_into_ultipa.py --db sqlite:///bank.db --dir ./data
```

---

## 🔑 Environment Variables

Define in `.env`:

```
DATABASE_URL=sqlite:///./records/bank.db
DEV_SEED_TOKEN=let-me-seed
```

- `DATABASE_URL`: Connection string for SQLAlchemy  
- `DEV_SEED_TOKEN`: Token required for `/api/seed/minimal` endpoint  

---

## 🚀 API Quick Reference

| Method | Endpoint                              | Description                          |
|--------|---------------------------------------|--------------------------------------|
| GET    | `/api/health`                         | Check backend health                 |
| GET    | `/api/accounts`                       | List all accounts                    |
| GET    | `/api/account/<acct>/balance`         | Get balance of account               |
| GET    | `/api/customer/<cid>/transactions`    | Get customer’s transactions          |
| GET    | `/api/merchants?q=...`                | Search merchants                     |
| POST   | `/api/transfer`                       | Make a transfer                      |
| POST   | `/api/pay`                            | Make a payment                       |
| POST   | `/api/seed/minimal`                   | Seed demo data (requires token)      |

---

## 📦 Dependencies

**Backend** (`requirements.txt`)  
- Flask, Flask-CORS, SQLAlchemy, python-dotenv, Ultipa client  

**Frontend** (`package.json`)  
- React 19, Vite, TailwindCSS, ESLint  

---

## 👤 Author
Created by **Barton Hou**

---

## 📜 License
MIT (or your choice)
