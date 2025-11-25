from sqlmodel import Session, select
from database import engine
from models import User
from auth import get_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

def create_users():
    with Session(engine) as session:
        # Check if users already exist
        existing = session.exec(select(User)).first()
        if existing:
            print("Users already seeded. Skipping.")
            return

        sales_password = os.getenv("SALES_PASSWORD", "").strip()

        # Create sales team users
        users_data = [
            {"username": "sales_a", "password": sales_password},
            {"username": "sales_b", "password": sales_password},
        ]

        for user_data in users_data:
            password = user_data["password"] 

            if password is None:
                raise ValueError("Password is None!")
            password_str = str(password)
            byte_len = len(password_str.encode('utf-8'))
            print(f"⚠️ Hashing: {password_str} (length: {byte_len} bytes)")
            if byte_len > 72:
                raise ValueError(f"Password too long: {byte_len} bytes")

            hashed_pw = get_password_hash(password_str)
            user = User(
                username=user_data["username"],
                password=hashed_pw
            )
            session.add(user)

        session.commit()
        print("Sales team users seeded successfully!")

if __name__ == "__main__":
    create_users()