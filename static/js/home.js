// home.js — User dashboard
import { api, guard, getUser, clearAuth, toast, fmtDate, riskBadge, statusBadge, loading } from "./utils.js";

if (!guard("user")) throw new Error("blocked");
const user = getUser();
document.getElementById("sb-name").textContent = user.name||user.email.split("@")[0];

const navItems=document.querySelectorAll(".nav-item[data-s]");
const sections=document.querySelectorAll(".section");
function showSection(name){
  navItems.forEach(n=>n.classList.toggle("active",n.dataset.s===name));
  sections.forEach(s=>s.classList.toggle("active",s.id==="s-"+name));
  if(name==="profile")  loadProfile();
  if(name==="activity") loadActivity();
  if(name==="security") loadSecurity();
}
navItems.forEach(n=>n.addEventListener("click",()=>showSection(n.dataset.s)));

async function loadProfile(){
  try{
    const d=await api("/api/user/profile");
    const p=d.profile;
    const init=(p.name||p.email||"U")[0].toUpperCase();
    document.getElementById("pav").textContent=init;
    document.getElementById("pname").textContent=p.name||"—";
    document.getElementById("pemail").textContent=p.email;
    document.getElementById("prole").innerHTML=`<span class="badge b-${p.role}">${p.role}</span>`;
    document.getElementById("pstatus").innerHTML=`<span class="badge b-${p.status}">${p.status}</span>`;
    document.getElementById("i-email").textContent=p.email;
    document.getElementById("i-name").textContent=p.name||"—";
    document.getElementById("i-role").textContent=p.role;
    document.getElementById("i-status").textContent=p.status;
    document.getElementById("i-created").textContent=fmtDate(p.created_at);
  }catch(e){toast(e.message,"error");}
}

const editBtn=document.getElementById("edit-btn");
const editForm=document.getElementById("edit-form");
editBtn?.addEventListener("click",()=>{
  editForm.style.display=editForm.style.display==="none"?"flex":"none";
});
document.getElementById("save-name")?.addEventListener("click",async()=>{
  const name=document.getElementById("new-name").value;
  try{
    await api("/api/user/profile",{method:"PUT",body:JSON.stringify({name})});
    toast("Name updated","success");
    editForm.style.display="none";
    loadProfile();
  }catch(e){toast(e.message,"error");}
});

async function loadActivity(){
  loading("act-tbody",4);
  try{
    const d=await api("/api/user/logs");
    const tb=document.getElementById("act-tbody");
    if(!d.logs.length){
      tb.innerHTML=`<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:20px">No activity yet</td></tr>`; return;
    }
    tb.innerHTML=d.logs.map(l=>`
      <tr>
        <td>${l.action||"—"}</td>
        <td>${riskBadge(l.risk_label||"low")}</td>
        <td>${statusBadge(l.status||"—")}</td>
        <td style="font-size:12px;color:var(--muted)">${fmtDate(l.timestamp)}</td>
      </tr>`).join("");
  }catch(e){toast(e.message,"error");}
}

async function loadSecurity(){
  try{
    const d=await api("/api/user/logs");
    const last=d.logs[0];
    document.getElementById("sec-last-risk").innerHTML   = last?riskBadge(last.risk_label||"low"):"—";
    document.getElementById("sec-last-time").textContent = last?fmtDate(last.timestamp):"—";
    document.getElementById("sec-last-action").textContent = last?last.action:"—";
  }catch(e){toast(e.message,"error");}
}

document.getElementById("logout-btn").addEventListener("click",async()=>{
  try{await api("/api/logout",{method:"POST"});}catch{}
  clearAuth(); window.location.href="/";
});

showSection("profile");
