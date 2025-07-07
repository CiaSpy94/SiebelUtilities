
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.0/firebase-app.js";
import { getDatabase, ref, get, set } from "https://www.gstatic.com/firebasejs/10.11.0/firebase-database.js";
import { firebaseConfig } from './firebase-config.js';

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

const urlParams = new URLSearchParams(window.location.search);
const switchName = urlParams.get('switch');
document.getElementById('switchHeader').innerText = switchName + " details";

const tableBody = document.querySelector("#detailsTable tbody");
const modal = document.getElementById("editModal");
const releaseField = document.getElementById("releaseField");
const modeField = document.getElementById("modeField");
const basedOnField = document.getElementById("basedOnField");
const accessControlField = document.getElementById("accessControlField");
const modalTitle = document.getElementById("modalTitle");

let currentEditRelease = null;

function loadSwitchDetails() {
  const switchRef = ref(db, 'switches/' + switchName);
  get(switchRef).then(snapshot => {
    if (snapshot.exists()) {
      const data = snapshot.val();
      tableBody.innerHTML = '';
      for (const release in data) {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td><b>${release}</b></td>
          <td>${data[release].mode}</td>
          <td>${data[release].basedOn}</td>
          <td>${data[release].accessControl}</td>
          <td><button onclick="editRelease('${release}')">Edit</button></td>
        `;
        tableBody.appendChild(row);
      }
    }
  });
}

window.editRelease = function(release) {
  currentEditRelease = release;
  modalTitle.innerText = "Edit Switch";
  releaseField.value = release;
  releaseField.readOnly = true;
  const switchRef = ref(db, 'switches/' + switchName + '/' + release);
  get(switchRef).then(snapshot => {
    if (snapshot.exists()) {
      const data = snapshot.val();
      modeField.value = data.mode;
      basedOnField.value = data.basedOn;
      accessControlField.value = data.accessControl;
      modal.style.display = "block";
    }
  });
};

window.openAddModal = function() {
  currentEditRelease = null;
  modalTitle.innerText = "Add New Release";
  releaseField.value = "";
  releaseField.readOnly = false;
  modeField.value = "RESTRICTED";
  basedOnField.value = "Responsibility";
  accessControlField.value = "";
  modal.style.display = "block";
};

window.closeModal = function() {
  modal.style.display = "none";
};

window.saveDetails = function() {
  const release = releaseField.value.trim();
  const mode = modeField.value;
  const basedOn = basedOnField.value;
  const accessControl = accessControlField.value.trim();

  if (!release) {
    alert("Release is required.");
    return;
  }

  const switchRef = ref(db, 'switches/' + switchName + '/' + release);
  set(switchRef, {
    mode,
    basedOn,
    accessControl
  }).then(() => {
    modal.style.display = "none";
    loadSwitchDetails();
  });
};

loadSwitchDetails();
