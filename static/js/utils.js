// utils.js
export function toast(msg, type="info"){
  let c=document.getElementById("toast");
  if(!c){c=document.createElement("div");c.id="toast";document.body.appendChild(c);}
  const t=document.createElement("div");
  t.className=`toast t-${type==="success"?"ok":type==="error"?"err":"info"}`;
  t.textContent=msg;c.appendChild(t);setTimeout(()=>t.remove(),3200);
}
export const getToken =()=>localStorage.getItem("rbac_token");
export const setToken =t =>localStorage.setItem("rbac_token",t);
export const clearAuth=()=>{localStorage.removeItem("rbac_token");localStorage.removeItem("rbac_user");};
export const getUser  =()=>{try{return JSON.parse(localStorage.getItem("rbac_user")||"null")}catch{return null}};
export const setUser  =u =>localStorage.setItem("rbac_user",JSON.stringify(u));

export function guard(role=null){
  const token=getToken(),user=getUser();
  if(!token||!user){window.location.href="/";return false;}
  if(role&&user.role!==role){
    const map={super_admin:"/super-admin",admin:"/admin",user:"/user"};
    window.location.href=map[user.role]||"/";return false;
  }
  return true;
}

export async function api(url,options={}){
  const token=getToken();
  const headers={"Content-Type":"application/json",...(token?{Authorization:`Bearer ${token}`}:{}),...(options.headers||{})};
  const res=await fetch(url,{...options,headers});
  const data=await res.json().catch(()=>({}));
  if(!res.ok)throw new Error(data.error||`HTTP ${res.status}`);
  return data;
}

export function fmtDate(ts){if(!ts)return"—";return new Date(ts).toLocaleString();}
export function riskBadge(label){
  if(label==="high")return`<span class="risk-hi">⚠ High Risk</span>`;
  return`<span class="risk-lo">✓ Safe</span>`;
}
export function roleBadge(r){return`<span class="badge b-${r}">${r.replace("_"," ")}</span>`;}
export function statusBadge(s){return`<span class="badge b-${s}">${s}</span>`;}
export function loading(id,cols){
  const el=document.getElementById(id);
  if(el)el.innerHTML=`<tr><td colspan="${cols}" style="text-align:center;padding:20px"><span class="spinner"></span></td></tr>`;
}

// YOUR exact getDevice
export function getDevice(){
  if(navigator.userAgentData?.mobile||/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)||window.innerWidth<=768)return"Mobile";
  return"Laptop";
}

// YOUR exact getLocation with 3-API fallback
export async function getLocation(){
  try{
    const ipRes=await fetch("https://api.ipify.org?format=json");
    const ipData=await ipRes.json();
    const res=await fetch(`https://ipapi.co/${ipData.ip}/json/`);
    const data=await res.json();
    if(data.country_name)return data.country_name;
  }catch{}
  try{
    const res=await fetch("https://ipwho.is/",{cache:"no-store"});
    const data=await res.json();
    if(data.success&&data.country)return data.country;
  }catch{}
  return"Unknown";
}
