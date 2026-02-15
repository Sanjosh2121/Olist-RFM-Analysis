import pandas as pd
from sqlalchemy import create_engine
import urllib.parse

# 1. ENCODE PASSWORD & CONNECT
raw_password = "YOUR_DATABASE_PASSWORD"
encoded_password = urllib.parse.quote_plus(raw_password)
engine = create_engine(f'mysql+mysqlconnector://root:{encoded_password}@localhost/ecommerce_clv')

def run_clv_pipeline():
    print("--- Connecting to MySQL ---")
    try:
        df = pd.read_sql("SELECT * FROM customer_summary", con=engine)
        return df
    except Exception as e:
        print(f"Connection Failed: {e}")
        return None

if __name__ == "__main__":
    df = run_clv_pipeline()

    if df is not None:
        print("\n--- Starting Heuristic RFM Analysis ---")

        # 1. RANKING (The 'Skeptic's' Way)
        # We divide customers into 5 groups (Quintiles)
        # For Recency: Lower is better (bought recently)
        # For Frequency & Monetary: Higher is better
        
        df['r_score'] = pd.qcut(df['T'], 5, labels=[5, 4, 3, 2, 1]) # Lower T = More Recent Join
        
        # Frequency is tricky because many are 0. We use 'rank' with 'first' method.
        df['f_score'] = pd.cut(df['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
        df['m_score'] = pd.qcut(df['monetary_value'], 5, labels=[1, 2, 3, 4, 5])

        # 2. CREATE RFM SEGMENT
        df['rfm_score'] = df['r_score'].astype(str) + df['f_score'].astype(str) + df['m_score'].astype(str)
        
        # 3. CALCULATE 'PREDICTED VALUE' PROXY
        # We weight them: 20% Recency, 50% Frequency, 30% Monetary
        df['clv_score'] = (df['r_score'].astype(int) * 0.2) + \
                          (df['f_score'].astype(int) * 0.5) + \
                          (df['m_score'].astype(int) * 0.3)

        # 4. CUSTOMER SEGMENTATION LOGIC
        def segment_me(score):
            if score >= 4.5: return 'Champions'
            if score >= 3.5: return 'Loyal Customers'
            if score >= 2.5: return 'At Risk'
            return 'Hibernating / Lost'

        df['segment'] = df['clv_score'].apply(segment_me)

        # 5. EXPORT FOR TABLEAU
        output_path = "rfm_final_results.csv"
        df.to_csv(output_path, index=False)
        
        print(f"--- SUCCESS! ---")
        print(f"File saved at: {output_path}")
        print("\nBreakdown of Customer Segments:")
        print(df['segment'].value_counts())