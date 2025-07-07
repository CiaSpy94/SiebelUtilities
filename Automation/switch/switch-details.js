import { db } from './firebase-config.js';
import { ref, get, set } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-database.js";

const urlParams = new URLSearchParams(window.location.search);
const switchName = urlParams.get("name");
document.getElementById("switchHeader").textContent = `${switchName} Details`;

const releaseInput = document.getElementById("release");
const modeInput = document.getElementById("mode");
const basedOnInput = document.getElementById("basedOn");
const accessControlInput = document.getElementById("accessControl");
const addReleaseBtn = document.getElementById("addReleaseBtn");
const releaseData = document.getElementById("releaseData");

addReleaseBtn.onclick = async () => {
  const release = releaseInput.value;
  const mode = modeInput.value;
  const basedOn = basedOnInput.value;
  const accessControl = accessControlInput.value;

  if (!release) return;

  const releaseRef = ref(db, `switches/${switchName}/${release}`);
  const snapshot = await get(releaseRef);
  if (snapshot.exists()) {
    alert("Release already exists.");
    return;
  }

  await set(releaseRef, {
    mode,
    basedOn,
    accessControl
  });

  loadReleases();
};

async function loadReleases() {
  releaseData.innerHTML = "";
  const snapshot = await get(ref(db, `switches/${switchName}`));
  if (snapshot.exists()) {
    const data = snapshot.val();
    Object.keys(data).forEach(release => {
      const div = document.createElement("div");
      div.innerHTML = `<strong>${release}</strong><pre>${JSON.stringify(data[release], null, 2)}</pre>`;
      releaseData.appendChild(div);
    });
  }
}

loadReleases();
