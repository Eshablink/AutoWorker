import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const stages = [
  ["01","Planning","Turning the goal into safe executable actions."],
  ["02","Execution","Worker is interacting with the environment."],
  ["03","Recovery","Handling exceptions without losing state."],
  ["04","Verification","Proving the result before completion."],
];

function App() {
  return (
    <main className="shell">
      <aside className="rail">
        <div className="brand"><span>AW</span><div><b>AutoWorker</b><small>Autonomous operations</small></div></div>
        <nav><a className="active">Overview</a><a>Tasks</a><a>Approvals</a><a>Evidence</a><a>Workers</a></nav>
        <div className="worker"><i/>Worker cluster <strong>Online</strong></div>
      </aside>
      <section className="content">
        <header><div><p className="eyebrow">AUTONOMOUS CONTROL CENTER</p><h1>Good afternoon. <em>Your workers are ready.</em></h1><p className="sub">Observe, approve and verify autonomous computer work from one place.</p></div><button className="primary">+ New task</button></header>
        <section className="hero">
          <div><div className="live"><i/> LIVE WORKER</div><h2>Invoice operations</h2><p>Extracting invoice data, validating fields and preparing the ERP record.</p><div className="progress"><span/></div><small>Step 2 of 4 · Executing browser interaction</small></div>
          <div className="orb"><div>AI<br/><b>WORKER</b></div></div>
        </section>
        <div className="grid">
          {stages.map(([n,t,d]) => <article key={n} className="stage"><span>{n}</span><h3>{t}</h3><p>{d}</p></article>)}
        </div>
        <section className="lower"><div className="panel"><div className="panelHead"><h2>Execution timeline</h2><span>LIVE</span></div>{["Task created","Policy approved","Browser session started","Invoice fields extracted","ERP validation pending"].map((x,i)=><div className="event" key={x}><i className={i===4?"pulse":""}/><div><b>{x}</b><small>{i<3?"Completed":"In progress"} · just now</small></div></div>)}</div><div className="panel approval"><div className="panelHead"><h2>Human approval</h2><span>1 WAITING</span></div><p>The worker wants to submit an ERP record containing a financial side effect.</p><button className="approve">Review & approve</button><button className="ghost">Reject</button></div></section>
      </section>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
