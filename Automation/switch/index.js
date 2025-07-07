import { db } from './firebase-config.js';
import { ref, get } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-database.js";

document.addEventListener("DOMContentLoaded", async () => {
  const switchList = document.getElementById("switchList");
  const snapshot = await get(ref(db, "switches"));

  if (snapshot.exists()) {
    const data = snapshot.val();
    Object.keys(data).forEach(switchName => {
      const li = document.createElement("li");
      li.textContent = switchName;
      li.onclick = () => {
        window.location.href = `switch-details.html?name=${encodeURIComponent(switchName)}`;
      };
      switchList.appendChild(li);
    });
  }
});
