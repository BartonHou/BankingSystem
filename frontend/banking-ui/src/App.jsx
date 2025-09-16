import { useEffect, useMemo, useState } from "react";

const API = "http://localhost:5050";

export default function App() {
  const [accounts, setAccounts] = useState([]);
  const [selected, setSelected] = useState("");
  const [balance, setBalance] = useState(null);
  const [cid, setCid] = useState("C001");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  // Transfer form
  const [tf, setTf] = useState({ from: "", to: "", amount: "", currency: "USD", txId: "", channel: "ui" });
  // Pay form
  const [pf, setPf] = useState({ from: "", merchantId: "", amount: "", currency: "USD", txId: "", channel: "ui" });
  const [merchQuery, setMerchQuery] = useState("");
  const [merchList, setMerchList] = useState([]);

  useEffect(() => {
    fetch(`${API}/api/accounts`).then(r => r.json()).then(setAccounts);
  }, []);

  useEffect(() => {
    if (selected) {
      fetch(`${API}/api/account/${encodeURIComponent(selected)}/balance`)
        .then(r => r.json())
        .then(d => setBalance(d.balance));
    } else {
      setBalance(null);
    }
  }, [selected]);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/api/customer/${encodeURIComponent(cid)}/transactions`)
      .then(r => r.json())
      .then(setRows)
      .finally(() => setLoading(false));
  }, [cid]);

  useEffect(() => {
    const q = merchQuery.trim();
    if (!q) { setMerchList([]); return; }
    const t = setTimeout(() => {
      fetch(`${API}/api/merchants?q=${encodeURIComponent(q)}`)
        .then(r => r.json()).then(setMerchList);
    }, 250);
    return () => clearTimeout(t);
  }, [merchQuery]);

  const acctOptions = useMemo(() => accounts.map(a => a.accountNo), [accounts]);

  const submitTransfer = async (e) => {
    e.preventDefault();
    if (!tf.from || !tf.to || !tf.amount || !tf.currency || !tf.txId) {
      alert("请填写完整转账信息"); return;
    }
    const res = await fetch(`${API}/api/transfer`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(tf) });
    const j = await res.json();
    if (res.ok) {
      alert("转账成功！");
      if (selected === tf.from) {
        // refresh balance
        fetch(`${API}/api/account/${encodeURIComponent(selected)}/balance`).then(r => r.json()).then(d => setBalance(d.balance));
      }
    } else {
      alert("失败：" + (j.error || "unknown"));
    }
  };

  const submitPay = async (e) => {
    e.preventDefault();
    if (!pf.from || !pf.merchantId || !pf.amount || !pf.currency || !pf.txId) {
      alert("请填写完整支付信息"); return;
    }
    const res = await fetch(`${API}/api/pay`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(pf) });
    const j = await res.json();
    if (res.ok) {
      alert("支付成功！");
      if (selected === pf.from) {
        fetch(`${API}/api/account/${encodeURIComponent(selected)}/balance`).then(r => r.json()).then(d => setBalance(d.balance));
      }
    } else {
      alert("失败：" + (j.error || "unknown"));
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold">模拟银行</h1>
          <div className="flex gap-2">
            <select value={selected} onChange={e => setSelected(e.target.value)}
                    className="px-2 py-1 border rounded-md bg-white">
              <option value="">选择账户</option>
              {acctOptions.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
            <div className="px-3 py-1 rounded-md bg-slate-100 border">
              余额：{balance === null ? "—" : balance}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 左侧：操作卡片 */}
        <section className="space-y-4 lg:col-span-1">
          <div className="bg-white rounded-2xl shadow p-4 border">
            <h2 className="font-semibold mb-3">转账</h2>
            <form className="space-y-2" onSubmit={submitTransfer}>
              <input className="w-full border rounded-md px-3 py-2" placeholder="From accountNo"
                     value={tf.from} onChange={e => setTf({ ...tf, from: e.target.value })}/>
              <input className="w-full border rounded-md px-3 py-2" placeholder="To accountNo"
                     value={tf.to} onChange={e => setTf({ ...tf, to: e.target.value })}/>
              <div className="flex gap-2">
                <input className="flex-1 border rounded-md px-3 py-2" placeholder="Amount"
                       value={tf.amount} onChange={e => setTf({ ...tf, amount: e.target.value })}/>
                <input className="w-24 border rounded-md px-3 py-2" placeholder="CCY"
                       value={tf.currency} onChange={e => setTf({ ...tf, currency: e.target.value.toUpperCase() })}/>
              </div>
              <input className="w-full border rounded-md px-3 py-2" placeholder="TxId"
                     value={tf.txId} onChange={e => setTf({ ...tf, txId: e.target.value })}/>
              <input className="w-full border rounded-md px-3 py-2" placeholder="Channel (可选)"
                     value={tf.channel} onChange={e => setTf({ ...tf, channel: e.target.value })}/>
              <button className="w-full rounded-lg py-2 font-medium border bg-slate-900 text-white hover:opacity-90">
                提交转账
              </button>
            </form>
          </div>

          <div className="bg-white rounded-2xl shadow p-4 border">
            <h2 className="font-semibold mb-3">支付给商户</h2>
            <form className="space-y-2" onSubmit={submitPay}>
              <input className="w-full border rounded-md px-3 py-2" placeholder="From accountNo"
                     value={pf.from} onChange={e => setPf({ ...pf, from: e.target.value })}/>
              <div className="relative">
                <input className="w-full border rounded-md px-3 py-2" placeholder="搜索商户名称…"
                       value={merchQuery} onChange={e => setMerchQuery(e.target.value)}/>
                {merchList.length > 0 && (
                  <div className="absolute mt-1 w-full bg-white border rounded-md max-h-48 overflow-auto shadow">
                    {merchList.map(m => (
                      <div key={m.merchantId}
                           className="px-3 py-2 hover:bg-slate-100 cursor-pointer"
                           onClick={() => { setPf({ ...pf, merchantId: m.merchantId }); setMerchQuery(m.name); setMerchList([]); }}>
                        {m.name} <span className="text-xs text-slate-500">({m.merchantId})</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <input className="w-full border rounded-md px-3 py-2" placeholder="MerchantId"
                     value={pf.merchantId} onChange={e => setPf({ ...pf, merchantId: e.target.value })}/>
              <div className="flex gap-2">
                <input className="flex-1 border rounded-md px-3 py-2" placeholder="Amount"
                       value={pf.amount} onChange={e => setPf({ ...pf, amount: e.target.value })}/>
                <input className="w-24 border rounded-md px-3 py-2" placeholder="CCY"
                       value={pf.currency} onChange={e => setPf({ ...pf, currency: e.target.value.toUpperCase() })}/>
              </div>
              <input className="w-full border rounded-md px-3 py-2" placeholder="TxId"
                     value={pf.txId} onChange={e => setPf({ ...pf, txId: e.target.value })}/>
              <input className="w-full border rounded-md px-3 py-2" placeholder="Channel (可选)"
                     value={pf.channel} onChange={e => setPf({ ...pf, channel: e.target.value })}/>
              <button className="w-full rounded-lg py-2 font-medium border bg-slate-900 text-white hover:opacity-90">
                提交支付
              </button>
            </form>
          </div>
        </section>

        {/* 右侧：交易列表 */}
        <section className="lg:col-span-2 bg-white rounded-2xl shadow p-4 border">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">最近交易</h2>
            <div className="flex items-center gap-2">
              <input value={cid} onChange={(e) => setCid(e.target.value)}
                     className="border rounded-md px-3 py-1" placeholder="CustomerId"/>
              <button onClick={() => setCid(cid)} className="rounded-md px-3 py-1 border">
                刷新
              </button>
            </div>
          </div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-left border-b bg-slate-50">
                <tr>
                  <th className="py-2 px-2">类型</th>
                  <th className="py-2 px-2">From</th>
                  <th className="py-2 px-2">To</th>
                  <th className="py-2 px-2">金额</th>
                  <th className="py-2 px-2">币别</th>
                  <th className="py-2 px-2">渠道</th>
                  <th className="py-2 px-2">时间</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td className="py-4 px-2" colSpan="7">加载中…</td></tr>
                ) : rows.length === 0 ? (
                  <tr><td className="py-4 px-2" colSpan="7">暂无数据</td></tr>
                ) : rows.map((r, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 px-2">{r.kind}</td>
                    <td className="py-2 px-2 font-mono">{r.fromAcct}</td>
                    <td className="py-2 px-2 font-mono">{r.target}</td>
                    <td className="py-2 px-2">{r.amount}</td>
                    <td className="py-2 px-2">{r.currency}</td>
                    <td className="py-2 px-2">{r.channel}</td>
                    <td className="py-2 px-2">{r.createdAt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <footer className="max-w-6xl mx-auto p-4 text-xs text-slate-500">
        Create by Barton Hou
      </footer>
    </div>
  );
}
