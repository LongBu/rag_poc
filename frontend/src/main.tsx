import {createRoot} from "react-dom/client";
import {App} from "./App";
import {loadConfig} from "./data";
import {captureCallback, clearTransient, finishCallback, manager} from "./auth";
import "./style.css";

const callback = captureCallback();
const root = document.getElementById("root")!;
void loadConfig().then(async config => {
  const auth = manager(config);
  let user = null;
  let notice = "";
  try { user = await finishCallback(auth, callback, config); }
  catch { notice = "Sign-in failed. Please sign in again."; }
  createRoot(root).render(<App config={config} auth={auth} initialUser={user} initialNotice={notice}/>);
}).catch(() => {
  try {clearTransient();} catch { /* Storage may be unavailable; never expose callback values. */ }
  root.textContent = "Application configuration or browser storage is unavailable. Please try again.";
});
