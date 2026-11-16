# AI-Driven Demand Forecasting & Inventory Optimization

An intelligent demand forecasting and inventory optimization system designed to help businesses predict future product demand and make data-driven inventory decisions.

The project combines machine learning, time-series forecasting, and explainable AI to generate demand predictions and support efficient inventory planning.

## Project Overview

This project uses historical supply chain data to forecast product demand across different product categories. It evaluates multiple forecasting approaches and integrates inventory optimization techniques to support better stock management.

The system provides a backend API using FastAPI and an interactive frontend built with React.js.

## Key Features

- **Demand Forecasting:** Predicts future product demand using machine learning and time-series models.
- **Multiple Models:** Implements XGBoost and Prophet for forecasting.
- **Ensemble Forecasting:** Combines model predictions to improve forecasting capabilities.
- **Explainable AI:** Uses SHAP to understand feature importance and model predictions.
- **Inventory Optimization:** Calculates important inventory metrics such as:
  - Safety Stock
  - Reorder Point (ROP)
  - Economic Order Quantity (EOQ)
- **Interactive Dashboard:** Provides a user-friendly interface to explore forecasting and inventory insights.
- **REST API:** Integrates backend forecasting functionality through FastAPI.

## Tech Stack

| Component | Technologies |
|---|---|
| Frontend | React.js, Vite, CSS |
| Backend | Python, FastAPI |
| Machine Learning | XGBoost, Prophet |
| Explainable AI | SHAP |
| Data Processing | Pandas, NumPy |
| Database | SQLite (local authentication data) |
| Tools | Git, GitHub, VS Code |

## Dataset

**DataCo Smart Supply Chain Dataset**

- Approximately 180,000 order records.
- Historical supply chain transactions from 2015–2018.
- Covers multiple product categories.
- Used for demand analysis, model training, and forecasting.

## Machine Learning Models

The project explores the following approaches:

1. **XGBoost Regression:** Used for demand prediction based on historical and engineered features.
2. **Prophet:** Used for time-series demand forecasting.
3. **Ensemble Model:** Combines forecasting approaches.
4. **SHAP:** Provides model explainability and feature importance analysis.

## Project Structure

```text
demand-forecasting-inventory-optimization/
│
├── backend/
│   ├── data/
│   ├── models/
│   ├── notebooks/
│   ├── outputs/
│   ├── src/
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
└── .gitignore
```

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/dikshaverma469/demand-forecasting-inventory-optimization.git

cd demand-forecasting-inventory-optimization
```

### 2. Backend Setup

```bash
cd backend

python -m venv venv
```

Activate virtual environment:

**Windows:**
```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn src.api:app --reload
```

Access API documentation:

```text
http://127.0.0.1:8000/docs
```

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend

npm install

npm run dev
```

Open the local URL displayed by Vite in your browser.

## Applications

- Demand planning and forecasting.
- Inventory level optimization.
- Reduction of overstocking and stockouts.
- Data-driven supply chain decisions.
- Understanding factors influencing demand predictions.

## Future Improvements

- Rolling-origin validation across multiple time windows.
- Further model performance comparisons.
- Real-time forecasting capabilities.
- Improved dashboard visualizations.
- Cloud deployment and scalability.

## Author

**Diksha Verma**

B.Tech | Indira Gandhi Delhi Technical University for Women (IGDTUW)

[GitHub](https://github.com/dikshaverma469)

---

*Developed as an AI/ML-based research and development project focused on demand forecasting and inventory optimization.*
