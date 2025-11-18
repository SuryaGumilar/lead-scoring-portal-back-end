import joblib
import pandas as pd
from sqlmodel import Session, select
from models import Customer

COLUMN_MAPPING = {
    # Demographics
    "age": "age",
    "job": "job",
    "marital_status": "marital",
    "education": "education",
    "has_default_credit": "default",
    "has_housing_loan": "housing",
    "has_personal_loan": "loan",
    
    # Last contact of current campaign
    "contact_method": "contact",
    "last_contact_month": "month",
    "last_contact_weekday": "day_of_week",
    "last_call_duration_sec": "duration",
    
    # Campaign info
    "current_campaign_contacts": "campaign",
    "days_since_last_campaign": "pdays",
    "previous_campaign_contacts": "previous",
    "previous_campaign_outcome": "poutcome",
    
    # Socioeconomic context
    "employment_variation_rate": "emp.var.rate",
    "consumer_price_index": "cons.price.idx",
    "consumer_confidence_index": "cons.conf.idx",
    "euribor_3m_rate": "euribor3m",
    "number_of_employed": "nr.employed",
}

ML_FEATURES = [
    "age",
    "job",
    "marital",
    "education",
    "default",
    "housing",
    "loan",
    "contact",
    "month",
    "day_of_week",
    "duration",
    "campaign",
    "pdays",
    "previous",
    "poutcome",
    "emp.var.rate",
    "cons.price.idx",
    "cons.conf.idx",
    "euribor3m",
    "nr.employed",
]

def run_prediction_and_update_db(session: Session):
    # Load models
    preprocessor = joblib.load("pre-trained-model/preprocessor.pkl")
    model = joblib.load("pre-trained-model/best_model.pkl")
    label_encoder = joblib.load("pre-trained-model/label_encoder.pkl")

    # Fetch customers without predictions
    customers = session.exec(select(Customer).where(Customer.y_percentage == None)).all()
    if not customers:
        return

    # Build DataFrame from DB
    data = []
    for c in customers:
        data.append({
            "age": c.age,
            "job": c.job,
            "marital_status": c.marital_status,
            "education": c.education,
            "has_default_credit": c.has_default_credit,
            "has_housing_loan": c.has_housing_loan,
            "has_personal_loan": c.has_personal_loan,
            "contact_method": c.contact_method,
            "last_contact_month": c.last_contact_month,
            "last_contact_weekday": c.last_contact_weekday,
            "last_call_duration_sec": c.last_call_duration_sec,
            "current_campaign_contacts": c.current_campaign_contacts,
            "days_since_last_campaign": c.days_since_last_campaign,
            "previous_campaign_contacts": c.previous_campaign_contacts,
            "previous_campaign_outcome": c.previous_campaign_outcome,
            "employment_variation_rate": c.employment_variation_rate,
            "consumer_price_index": c.consumer_price_index,
            "consumer_confidence_index": c.consumer_confidence_index,
            "euribor_3m_rate": c.euribor_3m_rate,
            "number_of_employed": c.number_of_employed,
        })
    
    df_db = pd.DataFrame(data)
    df_ml = df_db.rename(columns=COLUMN_MAPPING)
    df_input = df_ml[ML_FEATURES].copy()

    for col in ["job", "marital", "education", "default", "housing", "loan", 
                "contact", "month", "day_of_week", "poutcome"]:
        if col in df_input.columns:
            df_input[col] = label_encoders[col].transform(df_input[col])

    # Predict
    X = preprocessor.transform(df_input)
    proba = model.predict_proba(X)[:, 1]
    percentages = proba * 100.0

    # Update DB
    for customer, pct in zip(customers, percentages):
        customer.subscription_probability = float(pct)
        session.add(customer)
    session.commit()
    