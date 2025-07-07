import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-app.js";
import { getDatabase } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-database.js";

const firebaseConfig = {
  apiKey: "AIzaSyAXlc3rMxUxesxDm-tZF0qh48d1VKVX20w",
  authDomain: "haloswitches.firebaseapp.com",
  databaseURL: "https://haloswitches-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "haloswitches",
  storageBucket: "haloswitches.firebasestorage.app",
  messagingSenderId: "388925647621",
  appId: "1:388925647621:web:ef26bcbc0651520cace56c"
};

const app = initializeApp(firebaseConfig);
const database = getDatabase(app);
export { database };