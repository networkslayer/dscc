const logoutLink = document.getElementById("logout-link");
if (logoutLink) {
  logoutLink.addEventListener("click", (e) => {
    e.preventDefault();
    localStorage.removeItem("dscc_token");
    window.location.href = "http://localhost:8000";
  });
}
