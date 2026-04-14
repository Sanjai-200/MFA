// otp.js — YOUR exact OTP verification flow
import { setToken, setUser } from "./utils.js";

const raw = sessionStorage.getItem("otp_pending");
if (!raw) { window.location.href="/"; }
const pending = JSON.parse(raw);

document.getElementById("otp-email").textContent = pending.email;
document.getElementById("risk-info").textContent = "⚠️ High risk login detected. OTP sent to " + pending.email;

// YOUR exact input handling — single input field (otpInput)
// plus split inputs — we support both

const otpInput = document.getElementById("otpInput");
const verifyBtn = document.getElementById("verifyBtn");
const resendBtn = document.getElementById("resendBtn");
const msgEl    = document.getElementById("msg");
const timerEl  = document.getElementById("timer");

// 60s timer (YOUR project uses 60s)
let countdown = 60, interval;
function startTimer(){
  clearInterval(interval);
  interval = setInterval(()=>{
    countdown--;
    const m=String(Math.floor(countdown/60)).padStart(2,"0");
    const s=String(countdown%60).padStart(2,"0");
    timerEl.textContent=`${m}:${s}`;
    if(countdown<=0){
      clearInterval(interval);
      msgEl.textContent="OTP expired. Please request a new one.";
      verifyBtn.disabled=true;
    }
  },1000);
}
startTimer();

// YOUR exact verifyOTP logic (adapted — no Firebase, uses JWT API)
async function verifyOTP(){
  const entered = otpInput.value.trim();
  if (!entered) { msgEl.textContent="Enter OTP."; return; }

  verifyBtn.disabled=true; verifyBtn.textContent="Verifying..."; msgEl.textContent="";

  try {
    const res  = await fetch("/api/verify-otp",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({user_id:pending.user_id, otp:entered})
    });
    const data = await res.json();

    if (!res.ok) {
      msgEl.textContent = data.error || "Wrong OTP ❌";
      verifyBtn.disabled=false; verifyBtn.textContent="Verify OTP";
      return;
    }

    msgEl.textContent = "OTP Verified ✅";
    clearInterval(interval);

    // YOUR cleanup pattern
    const email = pending.email;
    const lc    = parseInt(localStorage.getItem(email+"_loginCount")||"0")+1;
    localStorage.setItem(email+"_loginCount", lc);
    sessionStorage.setItem(email+"_failedAttempts", 0);
    localStorage.removeItem(email+"_pendingFailed");
    sessionStorage.removeItem("otp_pending");
    sessionStorage.removeItem("pendingDevice");
    sessionStorage.removeItem("pendingLocation");
    sessionStorage.removeItem("pendingTime");
    sessionStorage.removeItem("pendingLoginCount");
    sessionStorage.removeItem("pendingFailedAttempts");

    setToken(data.token);
    setUser({role:data.role, email:data.email, name:data.name});

    const map={super_admin:"/super-admin",admin:"/admin",user:"/user"};
    setTimeout(()=>window.location.href=map[data.role]||"/home",1000);

  } catch(e) {
    msgEl.textContent="Error: "+e.message;
    verifyBtn.disabled=false; verifyBtn.textContent="Verify OTP";
  }
}

// YOUR exact resendOTP logic (adapted — calls /api/resend-otp)
async function resendOTP(){
  const email = pending.email;
  if (!email) { msgEl.textContent="Session lost. Please login again."; setTimeout(()=>window.location.href="/",2000); return; }
  try {
    await fetch("/api/resend-otp",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({user_id:pending.user_id, email})
    });
    msgEl.textContent="New OTP sent 📩";
  } catch { msgEl.textContent="Failed to resend OTP. Try again."; }
  countdown=60; startTimer();
}

verifyBtn.addEventListener("click", verifyOTP);
resendBtn.addEventListener("click", resendOTP);
