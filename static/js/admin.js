import { api, guard, getUser, clearAuth, toast, fmtDate, riskBadge, roleBadge, statusBadge, loading } from "./utils.js";
if(!guard("admin"))throw new Error("blocked");
const user=getUser();
document.getElementById("sb-name").textContent=user.name||user.email.split("@")[0];

const navItems=document.querySelectorAll(".nav-item[data-s]");
const sections=document.querySelectorAll(".section");
function showSection(name){
  navItems.forEach(n=>n.classList.toggle("active",n.dataset.s===name));
  sections.forEach(s=>s.classList.toggle("active",s.id==="s-"+name));
  ({overview:loadStats,users:loadUsers,logs:loadLogs,analytics:loadAnalytics})[name]?.();
}
navItems.forEach(n=>n.addEventListener("click",()=>showSection(n.dataset.s)));

async function loadStats(){
  try{
    const d=await api("/api/admin/stats");
    Object.entries(d).forEach(([k,v])=>{const el=document.getElementById("st-"+k);if(el)el.textContent=v;});
  }catch(e){toast(e.message,"error");}
}

let allUsers=[];
async function loadUsers(){
  loading("users-tbody",4);
  try{
    const d=await api("/api/admin/users");
    allUsers=d.users; renderUsers(allUsers);
  }catch(e){toast(e.message,"error");}
}
function renderUsers(users){
  const tb=document.getElementById("users-tbody");
  if(!users.length){tb.innerHTML=`<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:20px">No users</td></tr>`;return;}
  tb.innerHTML=users.map(u=>`<tr>
    <td>${u.email}</td><td>${u.name||"—"}</td>
    <td>${roleBadge(u.role)}</td>
    <td>${statusBadge(u.status)}
      <button class="dbtn ${u.status==="active"?"dbtn-danger":"dbtn-success"}" style="margin-left:8px"
        onclick="toggleStatus(${u.id},'${u.status}')">
        ${u.status==="active"?"Block":"Unblock"}
      </button>
    </td>
  </tr>`).join("");
}
window.toggleStatus=async(uid,cur)=>{
  const st=cur==="active"?"blocked":"active";
  try{await api(`/api/admin/users/${uid}/status`,{method:"PUT",body:JSON.stringify({status:st})});toast(`User ${st}`,"success");loadUsers();}
  catch(e){toast(e.message,"error");}
};
document.getElementById("user-search")?.addEventListener("input",e=>{
  const q=e.target.value.toLowerCase();
  renderUsers(allUsers.filter(u=>u.email.toLowerCase().includes(q)||(u.name||"").toLowerCase().includes(q)));
});

async function loadLogs(){
  loading("logs-tbody",5);
  try{
    const d=await api("/api/admin/logs?limit=200");
    const tb=document.getElementById("logs-tbody");
    tb.innerHTML=d.logs.map(l=>`<tr>
      <td>${l.email||"—"}</td><td>${l.action||"—"}</td>
      <td>${riskBadge(l.risk_label||"low")}</td>
      <td>${statusBadge(l.status||"—")}</td>
      <td style="font-size:11px;color:var(--muted)">${fmtDate(l.timestamp)}</td>
    </tr>`).join("")||`<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:20px">No logs</td></tr>`;
  }catch(e){toast(e.message,"error");}
}

let charts={};
async function loadAnalytics(){
  try{
    const d=await api("/api/admin/analytics");
    const co={plugins:{legend:{labels:{color:"#e2e8f0"}}},responsive:true};
    const sc={ticks:{color:"#64748b"},grid:{color:"#232d45"}};
    const tCtx=document.getElementById("chart-trend")?.getContext("2d");
    if(tCtx){charts.trend?.destroy();charts.trend=new Chart(tCtx,{type:"line",data:{
      labels:d.trend.map(t=>t.date.slice(5)),
      datasets:[
        {label:"Success",data:d.trend.map(t=>t.success),borderColor:"#10b981",backgroundColor:"rgba(16,185,129,.08)",tension:.4},
        {label:"Failed",data:d.trend.map(t=>t.failed),borderColor:"#f43f5e",backgroundColor:"rgba(244,63,94,.08)",tension:.4},
        {label:"High Risk",data:d.trend.map(t=>t.high_risk),borderColor:"#f59e0b",backgroundColor:"rgba(245,158,11,.08)",tension:.4}
      ]},options:{...co,scales:{x:sc,y:{...sc,beginAtZero:true}}}});}
    const rCtx=document.getElementById("chart-risk")?.getContext("2d");
    if(rCtx){charts.risk?.destroy();charts.risk=new Chart(rCtx,{type:"doughnut",data:{
      labels:["Safe","High Risk"],
      datasets:[{data:[d.risk_distribution.low,d.risk_distribution.high],backgroundColor:["#10b981","#f43f5e"],borderColor:"#141926",borderWidth:3}]
    },options:co});}
  }catch(e){toast(e.message,"error");}
}

document.getElementById("logout-btn").addEventListener("click",async()=>{
  try{await api("/api/logout",{method:"POST"});}catch{}
  clearAuth();window.location.href="/";
});
showSection("overview");
