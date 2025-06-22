// static/js/notifications.js
// Global notification management for PulsePrep

class NotificationManager {
  constructor() {
      this.unreadCount = 0;
      this.updateInterval = 30000; // 30 seconds
      this.csrfToken = this.getCSRFToken();
      this.init();
  }

  init() {
      this.updateNotificationBadges();
      this.startPeriodicUpdates();
      this.bindEventListeners();
  }

  getCSRFToken() {
      const cookieValue = document.cookie
          .split('; ')
          .find(row => row.startsWith('csrftoken='));
      return cookieValue ? cookieValue.split('=')[1] : '';
  }

  // Update all notification badges on the page
  updateNotificationBadges(count = null) {
      if (count !== null) {
          this.unreadCount = count;
      }

      const badges = document.querySelectorAll('.notification-badge, .notification-badge-sidebar');
      
      badges.forEach(badge => {
          if (this.unreadCount > 0) {
              badge.textContent = this.unreadCount;
              badge.style.display = 'flex';
              badge.classList.remove('hidden');
          } else {
              badge.style.display = 'none';
              badge.classList.add('hidden');
          }
      });

      // Update unread count displays
      const unreadCountElements = document.querySelectorAll('[id*="unread-count"]');
      unreadCountElements.forEach(element => {
          element.textContent = this.unreadCount;
      });
  }

  // Fetch current unread count from server
  async fetchUnreadCount() {
      try {
          const response = await fetch('/notification/api/unread-count/', {
              headers: {
                  'X-Requested-With': 'XMLHttpRequest',
              },
          });

          if (response.ok) {
              const data = await response.json();
              if (data.success) {
                  this.updateNotificationBadges(data.unread_count);
                  return data.unread_count;
              }
          }
      } catch (error) {
          console.error('Error fetching unread count:', error);
      }
      return null;
  }

  // Start periodic updates
  startPeriodicUpdates() {
      setInterval(() => {
          this.fetchUnreadCount();
      }, this.updateInterval);
  }

  // Bind event listeners
  bindEventListeners() {
      // Handle mark as read buttons
      document.addEventListener('click', (e) => {
          if (e.target.matches('.btn-mark-read, .btn-mark-read *')) {
              const button = e.target.closest('.btn-mark-read');
              if (button) {
                  const notificationId = button.getAttribute('data-notification-id') || 
                                       button.onclick?.toString().match(/markAsRead\((\d+)\)/)?.[1];
                  if (notificationId) {
                      this.markAsRead(notificationId, button);
                  }
              }
          }

          // Handle mark all as read buttons
          if (e.target.matches('.mark-all-read, .mark-all-read *')) {
              const button = e.target.closest('.mark-all-read');
              if (button) {
                  this.markAllAsRead(button);
              }
          }
      });
  }

  // Mark individual notification as read
  async markAsRead(notificationId, button) {
      const originalText = button.innerHTML;
      
      try {
          button.disabled = true;
          button.innerHTML = '<div class="loading-spinner"></div> Marking...';
          
          const response = await fetch(`/notification/mark-read/${notificationId}/`, {
              method: 'POST',
              headers: {
                  'X-CSRFToken': this.csrfToken,
                  'X-Requested-With': 'XMLHttpRequest',
                  'Content-Type': 'application/json',
              },
          });
          
          const data = await response.json();
          
          if (data.success) {
              // Update the notification item appearance
              const notificationItem = document.querySelector(`[data-notification-id="${notificationId}"]`);
              if (notificationItem) {
                  notificationItem.classList.remove('unread');
                  notificationItem.classList.add('read');
                  
                  // Hide the mark as read button
                  button.style.display = 'none';
              }
              
              // Update notification badges
              this.updateNotificationBadges(data.unread_count);
              
              // Update mark all button visibility
              this.updateMarkAllButtonVisibility(data.unread_count);
              
              this.showMessage(data.message, 'success');
          } else {
              this.showMessage(data.message || 'Error marking notification as read', 'error');
              button.disabled = false;
              button.innerHTML = originalText;
          }
      } catch (error) {
          console.error('Error:', error);
          this.showMessage('Network error. Please try again.', 'error');
          button.disabled = false;
          button.innerHTML = originalText;
      }
  }

  // Mark all notifications as read
  async markAllAsRead(button) {
      const originalText = button.innerHTML;
      
      try {
          button.disabled = true;
          button.innerHTML = '<div class="loading-spinner"></div> Marking all...';
          
          const response = await fetch('/notification/mark-all-read/', {
              method: 'POST',
              headers: {
                  'X-CSRFToken': this.csrfToken,
                  'X-Requested-With': 'XMLHttpRequest',
                  'Content-Type': 'application/json',
              },
          });
          
          const data = await response.json();
          
          if (data.success) {
              // Update all unread notification items
              const unreadItems = document.querySelectorAll('.notification-item.unread');
              unreadItems.forEach(item => {
                  // Only update personal notifications (those with recipient)
                  const isPersonal = item.querySelector('.notification-type-badge.personal');
                  if (isPersonal) {
                      item.classList.remove('unread');
                      item.classList.add('read');
                      
                      // Hide mark as read buttons
                      const markReadBtn = item.querySelector('.btn-mark-read');
                      if (markReadBtn) {
                          markReadBtn.style.display = 'none';
                      }
                  }
              });
              
              // Update notification badges
              this.updateNotificationBadges(data.unread_count);
              
              // Hide the mark all button if no unread notifications
              this.updateMarkAllButtonVisibility(data.unread_count);
              
              this.showMessage(data.message, 'success');
          } else {
              this.showMessage(data.message || 'Error marking notifications as read', 'error');
              button.disabled = false;
              button.innerHTML = originalText;
          }
      } catch (error) {
          console.error('Error:', error);
          this.showMessage('Network error. Please try again.', 'error');
          button.disabled = false;
          button.innerHTML = originalText;
      }
  }

  // Update mark all button visibility
  updateMarkAllButtonVisibility(unreadCount) {
      const markAllButtons = document.querySelectorAll('#mark-all-read-btn, .mark-all-read');
      markAllButtons.forEach(button => {
          if (unreadCount === 0) {
              button.style.display = 'none';
          }
      });
  }

  // Show message to user
  showMessage(message, type = 'success') {
      // Try to find existing message container
      let messagesContainer = document.getElementById('messages-container');
      
      // If no container exists, create one
      if (!messagesContainer) {
          messagesContainer = document.createElement('div');
          messagesContainer.id = 'messages-container';
          messagesContainer.style.position = 'fixed';
          messagesContainer.style.top = '20px';
          messagesContainer.style.right = '20px';
          messagesContainer.style.zIndex = '9999';
          document.body.appendChild(messagesContainer);
      }
      
      const alertDiv = document.createElement('div');
      alertDiv.className = `alert alert-${type} alert-dismissible`;
      alertDiv.style.marginBottom = '10px';
      alertDiv.style.minWidth = '300px';
      alertDiv.innerHTML = `
          <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
          ${message}
          <button type="button" class="btn-close" onclick="this.parentElement.remove()">
              <i class="fas fa-times"></i>
          </button>
      `;
      
      messagesContainer.appendChild(alertDiv);
      
      // Auto-remove after 5 seconds
      setTimeout(() => {
          if (alertDiv.parentElement) {
              alertDiv.remove();
          }
      }, 5000);
  }

  // Initialize notification sounds (optional)
  playNotificationSound() {
      // Create a subtle notification sound
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
      oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
      
      gainNode.gain.setValueAtTime(0, audioContext.currentTime);
      gainNode.gain.linearRampToValueAtTime(0.1, audioContext.currentTime + 0.01);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.2);
  }
}

// Global functions for backward compatibility
window.markAsRead = function(notificationId) {
  const manager = window.notificationManager;
  const button = document.querySelector(`[onclick*="markAsRead(${notificationId})"]`);
  if (manager && button) {
      manager.markAsRead(notificationId, button);
  }
};

window.markAllAsRead = function() {
  const manager = window.notificationManager;
  const button = document.getElementById('mark-all-read-btn') || 
                 document.querySelector('.mark-all-read');
  if (manager && button) {
      manager.markAllAsRead(button);
  }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  window.notificationManager = new NotificationManager();
  
  // Add CSS for loading spinner if not already present
  if (!document.getElementById('notification-spinner-styles')) {
      const style = document.createElement('style');
      style.id = 'notification-spinner-styles';
      style.textContent = `
          .loading-spinner {
              display: inline-block;
              width: 16px;
              height: 16px;
              border: 2px solid #f3f3f3;
              border-top: 2px solid #82272e;
              border-radius: 50%;
              animation: spin 1s linear infinite;
          }
          
          @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
          }
          
          .alert {
              padding: 12px 16px;
              border-radius: 4px;
              border: 1px solid transparent;
              display: flex;
              align-items: center;
              gap: 8px;
              box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          }
          
          .alert-success {
              background-color: #d1fae5;
              border-color: #a7f3d0;
              color: #065f46;
          }
          
          .alert-error {
              background-color: #fecaca;
              border-color: #fca5a5;
              color: #991b1b;
          }
          
          .alert-dismissible {
              position: relative;
              padding-right: 3rem;
          }
          
          .btn-close {
              position: absolute;
              top: 50%;
              right: 1rem;
              transform: translateY(-50%);
              background: none;
              border: none;
              color: inherit;
              cursor: pointer;
              opacity: 0.7;
          }
          
          .btn-close:hover {
              opacity: 1;
          }
      `;
      document.head.appendChild(style);
  }
});