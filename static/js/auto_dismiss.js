document.addEventListener("DOMContentLoaded", function () {
    const alerts = document.querySelectorAll(".alert.auto-dismiss");
    alerts.forEach(function (alert) {
      setTimeout(() => {
        alert.classList.remove("show"); // Ẩn hiệu ứng fade out
        setTimeout(() => alert.remove(), 500); // Xoá khỏi DOM sau 0.5s
      }, 3000);
    });
  });
  