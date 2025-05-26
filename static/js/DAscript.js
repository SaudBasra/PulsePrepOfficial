// Dashboard JavaScript - Professional & Clean Implementation
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    setupSidebar();
    setupResponsiveHandlers();
    initializeCounters();
    setupEventListeners();
    setupNotifications();
    setupPerformanceMonitoring();
}

// Sidebar Management
function setupSidebar() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.toggle('active');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 768 && sidebar.classList.contains('active')) {
                if (!sidebar.contains(e.target) && e.target !== sidebarToggle) {
                    sidebar.classList.remove('active');
                }
            }
        });

        // Prevent sidebar from closing when clicking inside
        sidebar.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
}

// Responsive Handlers
function setupResponsiveHandlers() {
    const mediaQuery = window.matchMedia('(max-width: 768px)');
    
    function handleMediaChange(e) {
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (sidebar && mainContent) {
            if (e.matches) {
                sidebar.classList.remove('active');
            }
        }
    }

    mediaQuery.addEventListener('change', handleMediaChange);
    handleMediaChange(mediaQuery);

    // Handle window resize for chart responsiveness
    window.addEventListener('resize', debounce(function() {
        if (window.chartInstances) {
            Object.values(window.chartInstances).forEach(chart => {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            });
        }
    }, 250));
}

// Counter Animations
function initializeCounters() {
    const countElements = document.querySelectorAll('.count-up');
    const observerOptions = {
        threshold: 0.5,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.dataset.counted) {
                animateCounter(entry.target);
            }
        });
    }, observerOptions);

    countElements.forEach(element => {
        observer.observe(element);
    });
}

function animateCounter(element) {
    const target = parseInt(element.getAttribute('data-value')) || 0;
    const duration = 2000;
    const start = performance.now();
    
    element.dataset.counted = 'true';

    function updateCounter(currentTime) {
        const elapsed = currentTime - start;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function for smooth animation
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const current = Math.floor(easeOutQuart * target);
        
        element.textContent = current.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(updateCounter);
        } else {
            element.textContent = target.toLocaleString();
        }
    }
    
    requestAnimationFrame(updateCounter);
}

// Event Listeners
function setupEventListeners() {
    // Refresh button functionality
    const refreshBtn = document.querySelector('.refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            handleRefresh(this);
        });
    }

    // Chart control buttons
    const chartControls = document.querySelectorAll('.chart-control');
    chartControls.forEach(control => {
        control.addEventListener('click', function() {
            handleChartControlClick(this);
        });
    });

    // User action buttons
    setupUserActionButtons();

    // Keyboard navigation
    setupKeyboardNavigation();
}

function handleRefresh(button) {
    const icon = button.querySelector('i');
    if (icon) {
        icon.style.animation = 'spin 1s linear';
        
        // Simulate refresh operation
        setTimeout(() => {
            icon.style.animation = '';
            showNotification('Dashboard refreshed successfully', 'success');
        }, 1000);
    }
}

function handleChartControlClick(button) {
    const controls = button.parentElement.querySelectorAll('.chart-control');
    controls.forEach(control => control.classList.remove('active'));
    button.classList.add('active');
    
    const view = button.getAttribute('data-view');
    updateDistributionChart(view);
}

function setupUserActionButtons() {
    // Approve buttons
    const approveButtons = document.querySelectorAll('.approve-btn');
    approveButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            handleUserAction(this, 'approve');
        });
    });

    // Reject buttons
    const rejectButtons = document.querySelectorAll('.reject-btn');
    rejectButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            handleUserAction(this, 'reject');
        });
    });
}

function handleUserAction(button, action) {
    const userItem = button.closest('.user-item');
    const userName = userItem.querySelector('.user-name').textContent;
    
    if (confirm(`Are you sure you want to ${action} ${userName}?`)) {
        // Add loading state
        button.classList.add('loading');
        
        // Simulate API call
        setTimeout(() => {
            button.classList.remove('loading');
            userItem.style.opacity = '0.5';
            showNotification(`User ${action}ed successfully`, 'success');
            
            // Remove from pending list after animation
            setTimeout(() => {
                userItem.remove();
            }, 300);
        }, 1000);
    }
}

function setupKeyboardNavigation() {
    // Add keyboard support for interactive elements
    const interactiveElements = document.querySelectorAll('.stat-card, .action-card, .user-item');
    
    interactiveElements.forEach(element => {
        element.setAttribute('tabindex', '0');
        
        element.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (element.onclick) {
                    element.onclick();
                } else {
                    element.click();
                }
            }
        });
    });
}

// Chart Management
function updateDistributionChart(view) {
    if (!window.distributionChart) return;
    
    const chart = window.distributionChart;
    
    if (view === 'status') {
        chart.data.labels = ['Approved', 'Pending', 'Rejected'];
        chart.data.datasets[0].backgroundColor = ['#10b981', '#f59e0b', '#ef4444'];
        // These values would come from the backend in a real implementation
        // chart.data.datasets[0].data = [approvedUsers, pendingUsers, rejectedUsers];
    } else {
        chart.data.labels = ['MBBS', 'BDS'];
        chart.data.datasets[0].backgroundColor = ['#2563eb', '#dc2626'];
        // chart.data.datasets[0].data = [mbbsUsers, bdsUsers];
    }
    
    chart.update('active');
}

// Notifications System
function setupNotifications() {
    // Create notification container if it doesn't exist
    if (!document.querySelector('.notification-container')) {
        const container = document.createElement('div');
        container.className = 'notification-container';
        container.innerHTML = `
            <style>
                .notification-container {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 10000;
                    max-width: 400px;
                }
                .notification {
                    background: white;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 12px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    border-left: 4px solid;
                    animation: slideInRight 0.3s ease-out;
                    position: relative;
                    overflow: hidden;
                }
                .notification.success { border-left-color: #10b981; }
                .notification.error { border-left-color: #ef4444; }
                .notification.warning { border-left-color: #f59e0b; }
                .notification.info { border-left-color: #3b82f6; }
                .notification-content {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                .notification-icon {
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 12px;
                }
                .notification.success .notification-icon { background: #10b981; }
                .notification.error .notification-icon { background: #ef4444; }
                .notification.warning .notification-icon { background: #f59e0b; }
                .notification.info .notification-icon { background: #3b82f6; }
                .notification-text {
                    flex: 1;
                    font-size: 14px;
                    font-weight: 500;
                    color: #374151;
                }
                .notification-progress {
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    height: 2px;
                    background: rgba(0, 0, 0, 0.1);
                    animation: progress 4s linear forwards;
                }
                @keyframes slideInRight {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes progress {
                    from { width: 100%; }
                    to { width: 0%; }
                }
            </style>
        `;
        document.body.appendChild(container);
    }
}

function showNotification(message, type = 'info', duration = 4000) {
    const container = document.querySelector('.notification-container');
    if (!container) return;

    const icons = {
        success: '✓',
        error: '✕',
        warning: '!',
        info: 'i'
    };

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <div class="notification-icon">${icons[type] || icons.info}</div>
            <div class="notification-text">${message}</div>
        </div>
        <div class="notification-progress"></div>
    `;

    container.appendChild(notification);

    // Auto remove notification
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideInRight 0.3s ease-out reverse';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, duration);

    // Click to dismiss
    notification.addEventListener('click', () => {
        notification.remove();
    });
}

// Performance Monitoring
function setupPerformanceMonitoring() {
    // Monitor page load performance
    window.addEventListener('load', function() {
        setTimeout(() => {
            const perfData = performance.getEntriesByType('navigation')[0];
            if (perfData) {
                const loadTime = perfData.loadEventEnd - perfData.loadEventStart;
                console.log(`Dashboard loaded in ${loadTime.toFixed(2)}ms`);
                
                // Show performance warning if load time is too high
                if (loadTime > 3000) {
                    showNotification('Dashboard loaded slowly. Consider optimizing.', 'warning');
                }
            }
        }, 100);
    });

    // Monitor memory usage (if available)
    if ('memory' in performance) {
        setInterval(() => {
            const memory = performance.memory;
            if (memory.usedJSHeapSize > 50 * 1024 * 1024) { // 50MB threshold
                console.warn('High memory usage detected');
            }
        }, 30000); // Check every 30 seconds
    }
}

// Utility Functions
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func.apply(this, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(this, args);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Error Handling
window.addEventListener('error', function(e) {
    console.error('Dashboard error:', e.error);
    showNotification('An error occurred. Please refresh the page.', 'error');
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    showNotification('An error occurred. Please try again.', 'error');
});

// Export functions for use in templates
window.DashboardUtils = {
    showNotification,
    updateDistributionChart,
    handleRefresh,
    debounce,
    throttle
};