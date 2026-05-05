<script type="module">
  // Import the functions you need from the SDKs you need
  import { initializeApp } from "https://www.gstatic.com/firebasejs/12.7.0/firebase-app.js";
  import { getAnalytics } from "https://www.gstatic.com/firebasejs/12.7.0/firebase-analytics.js";
  // TODO: Add SDKs for Firebase products that you want to use
  // https://firebase.google.com/docs/web/setup#available-libraries

  // Your web app's Firebase configuration
  // For Firebase JS SDK v7.20.0 and later, measurementId is optional
  const firebaseConfig = {
    apiKey: "AIzaSyCr8IMlw4vWO-a4VOFGdiisFWk46pzO8JA",
    authDomain: "login-derma.firebaseapp.com",
    projectId: "login-derma",
    storageBucket: "login-derma.firebasestorage.app",
    messagingSenderId: "919518863796",
    appId: "1:919518863796:web:7f4ce6cc6bd35182a212e1",
    measurementId: "G-QLM76YPF10"
  };

  // Initialize Firebase
  const app = initializeApp(firebaseConfig);
  const analytics = getAnalytics(app);
</script>