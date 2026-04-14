// developer.js
import { api, guard, getUser, clearToken, toast, fmtDate, riskBadge, statusBadge, loading } from "./utils.js";

if (!guard("developer")) throw new Error("blocked");
const user = getUser();
document.getElementById("sb-name").textContent = user.name || user.email.split("@")[0];

const navItems = document.querySelectorAll(".nav-item[data-s]");
const sections = document.querySelectorAll(".section");
function showSection(name) {
  navItems.forEach(n => n.classList.toggle("active", n.dataset.s===name));
  sections.forEach(s => s.classList.toggle("active", s.id==="s-"+name));
  if (name==="analytics") loadAnalytics();
  if (name==="logs")      loadLogs();
}
navItems.forEach(n => n.addEventListener("click",()=>showSection(n.dataset.s)));

let charts = {};
async function loadAnalytics() {
  try {
    const d = await api("/api/dev/analytics");
    document.getElementById("st-total").textContent = d.trend.reduce((a,t)=>a+t.success+t.failed,0);
    const co = { plugins:{legend:{labels:{color:"#e2e8f0"}}}, responsive:true };
    const sc = { ticks:{color:"#64748b"}, grid:{color:"#232d45"} };

    const tCtx = document.getElementById("chart-trend")?.getContext("2d");
    if (tCtx) {
      charts.trend?.destroy();
      charts.trend = new Chart(tCtx, { type:"line", data:{
        labels: d.trend.map(t=>t.date.slice(5)),
        datasets:[
          {label:"Success",  data:d.trend.map(t=>t.success),   borderColor:"#10b981",backgroundColor:"rgba(16,185,129,.08)",tension:.4},
          {label:"Failed",   data:d.trend.map(t=>t.failed),    borderColor:"#f43f5e",backgroundColor:"rgba(244,63,94,.08)",tension:.4},
          {label:"High Risk",data:d.trend.map(t=>t.high_risk), borderColor:"#f59e0b",backgroundColor:"rgba(245,158,11,.08)",tension:.4}
        ]}, options:{...co,scales:{x:sc,y:{...sc,beginAtZero:true}}}
      });
    }
    const rCtx = document.getElementById("chart-risk")?.getContext("2d");
    if (rCtx) {
      charts.risk?.destroy();
      charts.risk = new Chart(rCtx, { type:"bar", data:{
        labels:["Low","Medium","High"],
        datasets:[{data:[d.risk_distribution.low,d.risk_distribution.medium,d.risk_distribution.high],
          backgroundColor:["#10b981","#f59e0b","#f43f5e"],borderRadius:6}]
      }, options:{...co,plugins:{legend:{display:false}},scales:{x:sc,y:{...sc,beginAtZero:true}}}});
    }
  } catch(e) { toast(e.message,"error"); }
}

async function loadLogs() {
  loading("logs-tbody",5);
  try {
    const d = await api("/api/dev/logs?limit=200");
    const tb = document.getElementById("logs-tbody");
    if (!d.logs.length) { tb.innerHTML=`<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:20px">No logs</td></tr>`; return; }
    tb.innerHTML = d.logs.map(l=>`
      <tr>
        <td>${l.email||"—"}</td>
        <td>${l.action||"—"}</td>
        <td>${riskBadge(l.risk_score)}</td>
        <td>${statusBadge(l.status||"—")}</td>
        <td style="font-size:12px;color:var(--muted)">${fmtDate(l.timestamp)}</td>
      </tr>`).join("");
  } catch(e) { toast(e.message,"error"); }
}

document.getElementById("logout-btn").addEventListener("click", async () => {
  try { await api("/api/logout",{method:"POST"}); } catch {}
  clearToken(); window.location.href = "/";
});

showSection("analytics");
