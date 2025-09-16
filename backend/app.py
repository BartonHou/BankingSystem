import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from sqlalchemy import (create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, func, select, or_, literal)

from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

# -------------------- setup --------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DEV_SEED_TOKEN = os.getenv("DEV_SEED_TOKEN")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True))
Base = declarative_base()

app = Flask(__name__)
CORS(app)

# -------------------- models --------------------
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    customer_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128))

    accounts = relationship("Owns", back_populates="customer", cascade="all, delete-orphan")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    account_no = Column(String(64), unique=True, index=True, nullable=False)
    type = Column(String(32))
    currency = Column(String(8), default="USD")
    status = Column(String(32), default="active")

    owners = relationship("Owns", back_populates="account", cascade="all, delete-orphan")
    transfers_out = relationship("Transfer", foreign_keys="Transfer.from_account_id", back_populates="from_account")
    transfers_in = relationship("Transfer", foreign_keys="Transfer.to_account_id", back_populates="to_account")
    pays_out = relationship("Pay", back_populates="from_account")

class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(Integer, primary_key=True)
    merchant_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128))
    mcc = Column(String(8))

    pays_in = relationship("Pay", back_populates="merchant")

class Owns(Base):
    __tablename__ = "owns"
    id = Column(Integer, primary_key=True)
    customer_id_fk = Column(Integer, ForeignKey("customers.id"), nullable=False)
    account_id_fk = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    since = Column(DateTime, default=datetime.now)

    customer = relationship("Customer", back_populates="accounts")
    account = relationship("Account", back_populates="owners")
    __table_args__ = (UniqueConstraint("customer_id_fk", "account_id_fk", name="uq_owns"),)

class Transfer(Base):
    __tablename__ = "transfers"
    id = Column(Integer, primary_key=True)
    tx_id = Column(String(128), unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    channel = Column(String(32), default="api")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="transfers_out")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="transfers_in")

class Pay(Base):
    __tablename__ = "pays"
    id = Column(Integer, primary_key=True)
    tx_id = Column(String(128), unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    channel = Column(String(32), default="api")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    merchant_id_fk = Column(Integer, ForeignKey("merchants.id"), nullable=False)

    from_account = relationship("Account", back_populates="pays_out")
    merchant = relationship("Merchant", back_populates="pays_in")


Base.metadata.create_all(engine)

# -------------------- helpers --------------------
def db():  # context helper
    return SessionLocal()

def ok(data: Any = None):
    if data is None:
        return jsonify({"ok": True})
    return jsonify(data)

def json_error(msg: str, code: int = 400):
    return jsonify({"error": msg}), code

def require_fields(obj: Dict[str, Any], fields: List[str]):
    for f in fields:
        if f not in obj or (isinstance(obj[f], str) and not obj[f].strip()):
            return False
    return True

# -------------------- endpoints --------------------
@app.get("/api/health")
def api_health():
    try:
        with db() as s:
            s.execute(select(func.count(Account.id)))
        return ok({"ok": True})
    except Exception as e:
        return json_error(f"backend not ready: {e}", 500)

@app.get("/api/accounts")
def api_accounts():
    with db() as s:
        rows = s.execute(
            select(Account.account_no, Account.type, Account.currency, Account.status).order_by(Account.account_no)
        ).all()
        return ok([
            {"accountNo": r[0], "type": r[1], "currency": r[2], "status": r[3]}
            for r in rows
        ])

@app.get("/api/account/<acct>/balance")
def api_balance(acct):
    with db() as s:
        acc = s.execute(select(Account).where(Account.account_no == acct)).scalar_one_or_none()
        if not acc:
            return ok({"accountNo": acct, "balance": 0})
        incoming = s.execute(
            select(func.coalesce(func.sum(Transfer.amount), 0.0))
            .where(Transfer.to_account_id == acc.id)
        ).scalar_one()
        outgoing_transfers = s.execute(
            select(func.coalesce(func.sum(Transfer.amount), 0.0))
            .where(Transfer.from_account_id == acc.id)
        ).scalar_one()
        outgoing_pays = s.execute(
            select(func.coalesce(func.sum(Pay.amount), 0.0))
            .where(Pay.from_account_id == acc.id)
        ).scalar_one()
        balance = float(incoming) - float(outgoing_transfers) - float(outgoing_pays)
        return ok({"accountNo": acct, "balance": balance})

@app.get("/api/customer/<cid>/transactions")
def api_customer_tx(cid):
    with db() as s:
        cust = s.execute(select(Customer).where(Customer.customer_id == cid)).scalar_one_or_none()
        if not cust:
            return ok([])
        # 该客户拥有的账户
        acct_ids = [o.account_id_fk for o in s.execute(select(Owns).where(Owns.customer_id_fk == cust.id)).scalars().all()]
        if not acct_ids:
            return ok([])
        # outgoing transfers
        t_rows = s.execute(
            select(
                literal("Transfers").label("kind"),
                Account.account_no,               # from
                Account.account_no,               # placeholder; we'll replace with dst acct in loop
                Transfer.tx_id, Transfer.amount, Transfer.currency,
                Transfer.channel, Transfer.created_at, Transfer.to_account_id
            )
            .join(Account, Account.id == Transfer.from_account_id)
            .where(Transfer.from_account_id.in_(acct_ids))
            .order_by(Transfer.created_at.desc())
            .limit(200)
        ).all()

        # pays
        p_rows = s.execute(
            select(
                literal("Pays").label("kind"),
                Account.account_no,
                Merchant.merchant_id,
                Pay.tx_id, Pay.amount, Pay.currency,
                Pay.channel, Pay.created_at
            )
            .join(Account, Account.id == Pay.from_account_id)
            .join(Merchant, Merchant.id == Pay.merchant_id_fk)
            .where(Pay.from_account_id.in_(acct_ids))
            .order_by(Pay.created_at.desc())
            .limit(200)
        ).all()

        # map to dicts; for transfers, resolve target (dst accountNo)
        id_to_acct = {a.id: a.account_no for a in s.execute(select(Account.id, Account.account_no)).all()}
        out = []
        for kind, fromAcct, _placeholder, txId, amount, currency, channel, ts, dst_id in t_rows:
            out.append({
                "kind": kind,
                "fromAcct": fromAcct,
                "target": id_to_acct.get(dst_id, None),
                "txId": txId,
                "amount": float(amount),
                "currency": currency,
                "channel": channel,
                "createdAt": ts.isoformat() if isinstance(ts, datetime) else str(ts),
            })
        for kind, fromAcct, merchId, txId, amount, currency, channel, ts in p_rows:
            out.append({
                "kind": kind,
                "fromAcct": fromAcct,
                "target": merchId,
                "txId": txId,
                "amount": float(amount),
                "currency": currency,
                "channel": channel,
                "createdAt": ts.isoformat() if isinstance(ts, datetime) else str(ts),
            })
        # 按时间统一排序并截 200
        out.sort(key=lambda r: r["createdAt"], reverse=True)
        return ok(out[:200])

@app.get("/api/merchants")
def api_merchants():
    q = (request.args.get("q") or "").strip()
    with db() as s:
        stmt = select(Merchant.merchant_id, Merchant.name, Merchant.mcc)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Merchant.name.like(like), Merchant.merchant_id.like(like)))
        stmt = stmt.order_by(Merchant.name).limit(50)
        rows = s.execute(stmt).all()
        return ok([{"merchantId": r[0], "name": r[1], "mcc": r[2]} for r in rows])

@app.post("/api/transfer")
def api_transfer():
    data = request.get_json(force=True) or {}
    if not require_fields(data, ["from", "to", "amount", "currency", "txId"]):
        return json_error("missing fields", 400)
    try:
        amt = float(data["amount"])
        if amt < 0: raise ValueError()
    except Exception:
        return json_error("invalid amount", 400)

    with db() as s:
        src = s.execute(select(Account).where(Account.account_no == data["from"])).scalar_one_or_none()
        dst = s.execute(select(Account).where(Account.account_no == data["to"])).scalar_one_or_none()
        if not src or not dst:
            return json_error("account not found", 400)
        # unique tx_id
        exists = s.execute(select(Transfer).where(Transfer.tx_id == data["txId"])).scalar_one_or_none()
        if exists:
            return json_error("duplicate txId", 409)

        t = Transfer(
            tx_id=data["txId"],
            amount=amt,
            currency=(data.get("currency") or "USD").upper(),
            channel=data.get("channel") or "api",
            created_at=datetime.fromisoformat(data["createdAt"]) if data.get("createdAt") else datetime.now(timezone.utc),
            from_account_id=src.id,
            to_account_id=dst.id,
        )
        s.add(t)
        s.commit()
        return ok()

@app.post("/api/pay")
def api_pay():
    data = request.get_json(force=True) or {}
    if not require_fields(data, ["from", "merchantId", "amount", "currency", "txId"]):
        return json_error("missing fields", 400)
    try:
        amt = float(data["amount"])
        if amt < 0: raise ValueError()
    except Exception:
        return json_error("invalid amount", 400)

    with db() as s:
        acc = s.execute(select(Account).where(Account.account_no == data["from"])).scalar_one_or_none()
        merch = s.execute(select(Merchant).where(Merchant.merchant_id == data["merchantId"])).scalar_one_or_none()
        if not acc or not merch:
            return json_error("account or merchant not found", 400)
        exists = s.execute(select(Pay).where(Pay.tx_id == data["txId"])).scalar_one_or_none()
        if exists:
            return json_error("duplicate txId", 409)

        p = Pay(
            tx_id=data["txId"],
            amount=amt,
            currency=(data.get("currency") or "USD").upper(),
            channel=data.get("channel") or "api",
            created_at=datetime.fromisoformat(data["createdAt"]) if data.get("createdAt") else datetime.now(timezone.utc),
            from_account_id=acc.id,
            merchant_id_fk=merch.id,
        )
        s.add(p)
        s.commit()
        return ok()

# ----------- minimal seed (optional) -----------
@app.post("/api/seed/minimal")
def api_seed_minimal():
    token = request.headers.get("X-Seed-Token")
    if token != DEV_SEED_TOKEN:
        return json_error("unauthorized", 401)

    with db() as s:
        # customers
        c1 = s.execute(select(Customer).where(Customer.customer_id == "C001")).scalar_one_or_none()
        if not c1:
            c1 = Customer(customer_id="C001", name="Alice")
            s.add(c1)
        c2 = s.execute(select(Customer).where(Customer.customer_id == "C002")).scalar_one_or_none()
        if not c2:
            c2 = Customer(customer_id="C002", name="Bob")
            s.add(c2)

        # accounts
        a1 = s.execute(select(Account).where(Account.account_no == "A-1002")).scalar_one_or_none()
        if not a1:
            a1 = Account(account_no="A-1002", type="checking", currency="USD", status="active")
            s.add(a1)
        a2 = s.execute(select(Account).where(Account.account_no == "A-1003")).scalar_one_or_none()
        if not a2:
            a2 = Account(account_no="A-1003", type="savings", currency="USD", status="active")
            s.add(a2)

        # merchants
        m = s.execute(select(Merchant).where(Merchant.merchant_id == "M-Grocery")).scalar_one_or_none()
        if not m:
            m = Merchant(merchant_id="M-Grocery", name="Fresh Grocery", mcc="5411")
            s.add(m)

        s.flush()  # get IDs

        # owns
        def ensure_owns(cust, acct):
            o = s.execute(select(Owns).where(Owns.customer_id_fk == cust.id, Owns.account_id_fk == acct.id)).scalar_one_or_none()
            if not o:
                s.add(Owns(customer_id_fk=cust.id, account_id_fk=acct.id, since=datetime(2025, 4, 1, 12, 0, 0)))

        ensure_owns(c1, a1)
        ensure_owns(c2, a2)

        s.commit()
        return ok({"seeded": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
