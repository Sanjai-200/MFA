// auth.js — YOUR exact smart MFA login flow, adapted for JWT RBAC
import { getDevice, getLocation, setToken, setUser, toast } from "./utils.js";

const page = document.body.dataset.page;

// ══════════════════════════════════════════════
//  LOGIN — your exact flow preserved
// ══════════════════════════════════════════════
if (page === "login") {
  document.getElementById("login-btn").addEventListener("click", doLogin);
  document.getElementById("password").addEventListener("keydown", e => { if(e.key==="Enter") doLogin(); });

  async function doLogin() {
    const email    = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const msgEl    = document.getElementById("msg");

    // YOUR exact failed attempts logic
    let failedAttempts = parseInt(sessionStorage.getItem(email+"_failedAttempts")) || 0;
    const pendingFailed = parseInt(localStorage.getItem(email+"_pendingFailed")) || 0;
    if (pendingFailed >= 4 || failedAttempts >= 4) {
      msgEl.textContent = "⚠️ Too many attempts. Please refresh the page & try again later.";
      return;
    }

    const btn = document.getElementById("login-btn");
    btn.disabled = true;

    // YOUR exact messages
    msgEl.textContent = "Checking credentials...";

    try {
      // YOUR exact getDevice + getLocation
      msgEl.textContent = "Getting location...";
      const device   = getDevice();
      const location = await getLocation();
      const time     = new Date().toLocaleTimeString();

      // YOUR exact loginCount logic
      const lcKey    = email + "_loginCount";
      const loginCount = parseInt(localStorage.getItem(lcKey) || "0") + 1;
      const sessionFailedAttempts = pendingFailed > 0 ? pendingFailed : failedAttempts;

      // Store pending (YOUR pattern)
      sessionStorage.setItem("pendingDevice",          device);
      sessionStorage.setItem("pendingLocation",        location);
      sessionStorage.setItem("pendingTime",            time);
      sessionStorage.setItem("pendingLoginCount",      loginCount);
      sessionStorage.setItem("pendingFailedAttempts",  sessionFailedAttempts);
      sessionStorage.setItem("pendingEmail",           email);

      msgEl.textContent = "Analysing risk...";

      const context = { device, location, loginCount, time, failedAttempts: sessionFailedAttempts };

      const res  = await fetch("/api/login", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email, password, context })
      });
      const data = await res.json();

      if (!res.ok) {
        // YOUR exact failed attempt counting
        failedAttempts++;
        sessionStorage.setItem(email+"_failedAttempts", failedAttempts);
        if (failedAttempts >= 4) {
          localStorage.setItem(email+"_pendingFailed", failedAttempts);
          sessionStorage.setItem(email+"_failedAttempts", 0);
          msgEl.textContent = "⚠️ Too many attempts. Please refresh the page & try again later.";
        } else {
          msgEl.textContent = `Login failed ❌ (${failedAttempts})`;
        }
        btn.disabled = false;
        return;
      }

      if (data.status === "otp_required") {
        // YOUR exact OTP message + redirect
        msgEl.textContent = `Prediction: 1 → Sending OTP...`;
        sessionStorage.setItem("otp_pending", JSON.stringify({
          user_id: data.user_id, email: data.email, risk_label: data.risk_label
        }));
        setTimeout(() => window.location.href = "/otp", 1500);
        return;
      }

      // Safe login — YOUR exact message
      msgEl.textContent = `Prediction: 0 → Going Home...`;

      // Reset failed + save loginCount (YOUR pattern)
      sessionStorage.setItem(email+"_failedAttempts", 0);
      localStorage.removeItem(email+"_pendingFailed");
      localStorage.setItem(lcKey, loginCount);
      sessionStorage.removeItem("pendingDevice");
      sessionStorage.removeItem("pendingLocation");
      sessionStorage.removeItem("pendingTime");
      sessionStorage.removeItem("pendingLoginCount");
      sessionStorage.removeItem("pendingFailedAttempts");

      setToken(data.token);
      setUser({ role: data.role, email: data.email, name: data.name });

      const map = { super_admin:"/super-admin", admin:"/admin", user:"/user" };
      setTimeout(() => window.location.href = map[data.role] || "/home", 1500);

    } catch(e) {
      msgEl.textContent = "⚠️ Error: " + e.message;
      btn.disabled = false;
    }
  }
}

// ══════════════════════════════════════════════
//  SIGNUP
// ══════════════════════════════════════════════
if (page === "signup") {
  document.getElementById("signup-btn").addEventListener("click", async () => {
    const msgEl    = document.getElementById("msg");
    const btn      = document.getElementById("signup-btn");
    const name     = document.getElementById("name").value.trim();
    const email    = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirm  = document.getElementById("confirm").value;

    if (!name||!email||!password) { msgEl.textContent="All fields required."; return; }
    if (password!==confirm)       { msgEl.textContent="Passwords do not match."; return; }
    if (password.length<6)        { msgEl.textContent="Password must be at least 6 characters."; return; }

    btn.disabled=true; btn.textContent="Creating account...";
    try {
      const res  = await fetch("/api/signup",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,email,password})});
      const data = await res.json();
      if (!res.ok) { msgEl.textContent=data.error; btn.disabled=false; btn.textContent="Sign Up"; return; }
      msgEl.className="ok"; msgEl.textContent="Account created! Redirecting to login...";
      setTimeout(()=>window.location.href="/",1500);
    } catch(e) {
      msgEl.textContent=e.message; btn.disabled=false; btn.textContent="Sign Up";
    }
  });
}
