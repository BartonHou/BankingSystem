# load_csv_into_sqlite.py
import argparse, csv
from datetime import datetime, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    customer_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128))

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    account_no = Column(String(64), unique=True, index=True, nullable=False)
    type = Column(String(32))
    currency = Column(String(8), default="USD")
    status = Column(String(32), default="active")

class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(Integer, primary_key=True)
    merchant_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128))
    mcc = Column(String(8))

class Owns(Base):
    __tablename__ = "owns"
    id = Column(Integer, primary_key=True)
    customer_id_fk = Column(Integer, ForeignKey("customers.id"), nullable=False)
    account_id_fk = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    since = Column(DateTime)
    __table_args__ = (UniqueConstraint("customer_id_fk", "account_id_fk", name="uq_owns"),)

class Transfer(Base):
    __tablename__ = "transfers"
    id = Column(Integer, primary_key=True)
    tx_id = Column(String(128), unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    channel = Column(String(32), default="api")
    created_at = Column(DateTime, default=datetime.now)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

class Pay(Base):
    __tablename__ = "pays"
    id = Column(Integer, primary_key=True)
    tx_id = Column(String(128), unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    channel = Column(String(32), default="api")
    created_at = Column(DateTime, default=datetime.now)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    merchant_id_fk = Column(Integer, ForeignKey("merchants.id"), nullable=False)

def upsert_customer(s, customer_id, name):
    obj = s.execute(select(Customer).where(Customer.customer_id==customer_id)).scalar_one_or_none()
    if obj: return obj
    obj = Customer(customer_id=customer_id, name=name)
    s.add(obj); s.flush(); return obj

def upsert_account(s, account_no, typ, ccy, status):
    obj = s.execute(select(Account).where(Account.account_no==account_no)).scalar_one_or_none()
    if obj: return obj
    obj = Account(account_no=account_no, type=typ, currency=ccy, status=status)
    s.add(obj); s.flush(); return obj

def upsert_merchant(s, merchant_id, name, mcc):
    obj = s.execute(select(Merchant).where(Merchant.merchant_id==merchant_id)).scalar_one_or_none()
    if obj: return obj
    obj = Merchant(merchant_id=merchant_id, name=name, mcc=mcc)
    s.add(obj); s.flush(); return obj

def ensure_owns(s, customer_id, account_no, since_iso):
    cust = s.execute(select(Customer).where(Customer.customer_id==customer_id)).scalar_one()
    acct = s.execute(select(Account).where(Account.account_no==account_no)).scalar_one()
    o = s.execute(select(Owns).where(Owns.customer_id_fk==cust.id, Owns.account_id_fk==acct.id)).scalar_one_or_none()
    if o: return o
    since = datetime.fromisoformat(since_iso)
    o = Owns(customer_id_fk=cust.id, account_id_fk=acct.id, since=since)
    s.add(o); s.flush(); return o

def insert_transfer(s, row):
    src = s.execute(select(Account).where(Account.account_no==row["from_account_no"])).scalar_one()
    dst = s.execute(select(Account).where(Account.account_no==row["to_account_no"])).scalar_one()
    exists = s.execute(select(Transfer).where(Transfer.tx_id==row["tx_id"])).scalar_one_or_none()
    if exists: return False
    t = Transfer(
        tx_id=row["tx_id"],
        amount=float(row["amount"]),
        currency=row["currency"],
        channel=row["channel"],
        created_at=datetime.fromisoformat(row["created_at"]),
        from_account_id=src.id,
        to_account_id=dst.id,
    )
    s.add(t); return True

def insert_pay(s, row):
    acc = s.execute(select(Account).where(Account.account_no==row["from_account_no"])).scalar_one()
    m = s.execute(select(Merchant).where(Merchant.merchant_id==row["merchant_id"])).scalar_one()
    exists = s.execute(select(Pay).where(Pay.tx_id==row["tx_id"])).scalar_one_or_none()
    if exists: return False
    p = Pay(
        tx_id=row["tx_id"],
        amount=float(row["amount"]),
        currency=row["currency"],
        channel=row["channel"],
        created_at=datetime.fromisoformat(row["created_at"]),
        from_account_id=acc.id,
        merchant_id_fk=m.id,
    )
    s.add(p); return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="sqlite:///bank.db")
    ap.add_argument("--dir", default=".")
    args = ap.parse_args()

    engine = create_engine(args.db, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    s = Session()

    # customers
    with open(f"{args.dir}/customers.csv", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            upsert_customer(s, row["customer_id"], row["name"])

    # accounts
    with open(f"{args.dir}/accounts.csv", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            upsert_account(s, row["account_no"], row["type"], row["currency"], row["status"])

    # merchants
    with open(f"{args.dir}/merchants.csv", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            upsert_merchant(s, row["merchant_id"], row["name"], row["mcc"])

    s.commit()

    # owns
    with open(f"{args.dir}/owns.csv", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            ensure_owns(s, row["customer_id"], row["account_no"], row["since"])
    s.commit()

    # transfers
    with open(f"{args.dir}/transfers.csv", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        n=0
        for row in r:
            if insert_transfer(s, row): n+=1
        s.commit()
        print("inserted transfers:", n)

    # pays
    with open(f"{args.dir}/pays.csv", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        n=0
        for row in r:
            if insert_pay(s, row): n+=1
        s.commit()
        print("inserted pays:", n)

    s.close()

if __name__ == "__main__":
    main()
