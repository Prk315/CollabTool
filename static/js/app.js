/**
 * Student Collaboration Tool common JavaScript functionality
 */

// Make alert messages dismissible
document.addEventListener('DOMContentLoaded', function() {
  // Add close buttons to all alerts
  document.querySelectorAll('.alert').forEach(function(alert) {
    // Only add dismiss button if it doesn't already exist
    if (!alert.querySelector('.alert-dismiss')) {
      const dismissBtn = document.createElement('button');
      dismissBtn.className = 'alert-dismiss';
      dismissBtn.innerHTML = '&times;';
      dismissBtn.setAttribute('aria-label', 'Close');
      dismissBtn.addEventListener('click', function() {
        alert.style.opacity = '0';
        setTimeout(function() {
          alert.style.display = 'none';
        }, 300);
      });
      alert.appendChild(dismissBtn);
    }
  });
});

// Add transition styles to alerts
document.addEventListener('DOMContentLoaded', function() {
  const style = document.createElement('style');
  style.textContent = `
    .alert {
      transition: opacity 0.3s ease-in-out;
    }
  `;
  document.head.appendChild(style);
});

// Add active state to current nav link
document.addEventListener('DOMContentLoaded', function() {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');
  
  navLinks.forEach(function(link) {
    const href = link.getAttribute('href');
    if (currentPath.startsWith(href) && href !== '/') {
      link.classList.add('active');
    }
  });
});