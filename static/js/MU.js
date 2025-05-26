document.addEventListener('DOMContentLoaded', function() {
    // Fetch and display users
    loadUsers();
    
    // Add user button click event
    document.querySelector('.add-user-btn').addEventListener('click', function() {
        document.getElementById('user-modal').style.display = 'flex';
        document.querySelector('.modal-header h3').textContent = 'Add New User';
        document.getElementById('user-form').reset();
    });
    
    // Close modal button
    document.querySelector('.close-modal').addEventListener('click', closeModal);
    
    // Cancel button
    document.getElementById('cancel-user').addEventListener('click', closeModal);
    
    // Save user button
    document.getElementById('save-user').addEventListener('click', saveUser);
    
    // File upload display name
    document.getElementById('user-image').addEventListener('change', function() {
        const fileName = this.files[0] ? this.files[0].name : 'No file chosen';
        document.querySelector('.file-name').textContent = fileName;
    });
    
    // Search functionality
    document.getElementById('search-input').addEventListener('keyup', function() {
        const searchText = this.value.toLowerCase();
        const tableRows = document.querySelectorAll('#users-table-body tr');
        
        tableRows.forEach(row => {
            const text = row.textContent.toLowerCase();
            if (text.includes(searchText)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
    
    // Status filter
    document.querySelectorAll('.filter-dropdown-content a[data-filter]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const filter = this.getAttribute('data-filter');
            const filterButton = this.closest('.filter-dropdown').querySelector('.filter-btn');
            filterButton.innerHTML = this.textContent + ' <i class="fas fa-chevron-down"></i>';
            
            const tableRows = document.querySelectorAll('#users-table-body tr');
            
            tableRows.forEach(row => {
                const statusCell = row.querySelector('td:nth-child(4)');
                if (filter === 'all' || statusCell.textContent.toLowerCase() === filter) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });
    
    // Sort functionality
    document.querySelectorAll('.filter-dropdown-content a[data-sort]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const sortType = this.getAttribute('data-sort');
            const sortButton = this.closest('.filter-dropdown').querySelector('.filter-btn');
            sortButton.innerHTML = this.textContent + ' <i class="fas fa-chevron-down"></i>';
            
            // Reload users with sort type
            loadUsers(sortType);
        });
    });
    
    // Select all checkbox
    document.getElementById('select-all-checkbox').addEventListener('change', function() {
        const checkboxes = document.querySelectorAll('#users-table-body input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
    });
});

// Function to load users from API
function loadUsers(sortType = 'newest') {
    const tableBody = document.getElementById('users-table-body');
    tableBody.innerHTML = '<tr><td colspan="9">Loading users...</td></tr>';
    
    fetch('/api/users/?sort=' + sortType)
        .then(response => response.json())
        .then(data => {
            tableBody.innerHTML = '';
            
            if (data.users.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="9">No users found</td></tr>';
                return;
            }
            
            data.users.forEach(user => {
                const row = document.createElement('tr');
                
                // Create checkbox cell
                const checkboxCell = document.createElement('td');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.dataset.userId = user.id;
                checkboxCell.appendChild(checkbox);
                
                // Create picture cell
                const pictureCell = document.createElement('td');
                const pictureDiv = document.createElement('div');
                pictureDiv.className = 'user-picture';
                
                if (user.picture) {
                    const picture = document.createElement('img');
                    picture.src = user.picture;
                    picture.alt = user.name;
                    picture.className = 'user-thumbnail';
                    picture.style.width = '40px';
                    picture.style.height = '40px';
                    picture.style.borderRadius = '50%';
                    picture.style.objectFit = 'cover';
                    picture.addEventListener('click', () => {
                        window.open(user.picture, '_blank');
                    });
                    pictureDiv.appendChild(picture);
                } else {
                    const placeholder = document.createElement('div');
                    placeholder.className = 'avatar-placeholder';
                    placeholder.textContent = user.name.charAt(0).toUpperCase();
                    placeholder.style.width = '40px';
                    placeholder.style.height = '40px';
                    placeholder.style.backgroundColor = '#2563eb';
                    placeholder.style.color = 'white';
                    placeholder.style.borderRadius = '50%';
                    placeholder.style.display = 'flex';
                    placeholder.style.alignItems = 'center';
                    placeholder.style.justifyContent = 'center';
                    placeholder.style.fontWeight = 'bold';
                    placeholder.style.fontSize = '16px';
                    pictureDiv.appendChild(placeholder);
                }
                pictureCell.appendChild(pictureDiv);
                
                // Create other cells
                const nameCell = document.createElement('td');
                nameCell.textContent = user.name;
                
                const statusCell = document.createElement('td');
                const statusBadge = document.createElement('span');
                statusBadge.className = 'status-badge';
                statusBadge.classList.add('status-' + user.status.toLowerCase());
                statusBadge.textContent = user.status.charAt(0).toUpperCase() + user.status.slice(1);
                statusCell.appendChild(statusBadge);
                
                const categoryCell = document.createElement('td');
                const categoryBadge = document.createElement('span');
                categoryBadge.className = 'status-badge';
                categoryBadge.classList.add('status-' + user.category.toLowerCase());
                categoryBadge.textContent = user.category;
                categoryCell.appendChild(categoryBadge);
                
                const typeCell = document.createElement('td');
                typeCell.textContent = user.type;
                
                const emailCell = document.createElement('td');
                emailCell.textContent = user.email;
                
                const fieldCell = document.createElement('td');
                fieldCell.textContent = user.field || 'N/A';
                
                const yearCell = document.createElement('td');
                yearCell.textContent = user.year || 'N/A';
                
                // Append all cells to row
                row.appendChild(checkboxCell);
                row.appendChild(pictureCell);
                row.appendChild(nameCell);
                row.appendChild(statusCell);
                row.appendChild(categoryCell);
                row.appendChild(typeCell);
                row.appendChild(emailCell);
                row.appendChild(fieldCell);
                row.appendChild(yearCell);
                
                // Add actions to status badge for admin
                statusBadge.addEventListener('click', function(e) {
                    e.stopPropagation();
                    showStatusOptions(this, user.id, user.status);
                });
                
                // Add row click event to edit user
                row.addEventListener('click', function(e) {
                    if (e.target !== checkbox && e.target !== statusBadge) {
                        editUser(user);
                    }
                });
                
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error loading users:', error);
            tableBody.innerHTML = '<tr><td colspan="9">Error loading users. Please try again.</td></tr>';
            
            // If API not available, use sample data for demo
            const sampleData = getSampleUserData();
            populateTable(sampleData);
        });
}

// Sample data as fallback
function getSampleUserData() {
    return [
        {
            id: 1,
            name: "John Smith",
            status: "approved",
            category: "paid",
            type: "Student",
            email: "john.smith@example.com",
            field: "MBBS",
            year: "1st",
            picture: "https://i.pravatar.cc/100?img=3",
        },
        {
            id: 2,
            name: "Emily Johnson",
            status: "pending",
            category: "unpaid",
            type: "Student",
            email: "emily.johnson@example.com",
            field: "BDS",
            year: "2nd",
            picture: null, // Test with no picture
        },
        {
            id: 3,
            name: "Michael Brown",
            status: "rejected",
            category: "unpaid",
            type: "Student",
            email: "michael.brown@example.com",
            field: "MBBS",
            year: "3rd",
            picture: "https://i.pravatar.cc/100?img=5",
        }
    ];
}

// Updated populateTable function to handle profile images properly
function populateTable(data) {
    const tableBody = document.getElementById('users-table-body');
    tableBody.innerHTML = '';
    
    data.forEach(user => {
        const row = document.createElement('tr');
        
        // Create checkbox cell
        const checkboxCell = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'row-checkbox';
        checkbox.dataset.userId = user.id;
        checkboxCell.appendChild(checkbox);
        
        // Create picture cell with proper image handling
        const pictureCell = document.createElement('td');
        const pictureDiv = document.createElement('div');
        pictureDiv.className = 'user-picture';
        
        if (user.picture) {
            const picture = document.createElement('img');
            picture.src = user.picture;
            picture.alt = user.name;
            picture.className = 'user-thumbnail';
            picture.style.width = '40px';
            picture.style.height = '40px';
            picture.style.borderRadius = '50%';
            picture.style.objectFit = 'cover';
            pictureDiv.appendChild(picture);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'avatar-placeholder';
            placeholder.textContent = user.name.charAt(0).toUpperCase();
            placeholder.style.width = '40px';
            placeholder.style.height = '40px';
            placeholder.style.backgroundColor = '#2563eb';
            placeholder.style.color = 'white';
            placeholder.style.borderRadius = '50%';
            placeholder.style.display = 'flex';
            placeholder.style.alignItems = 'center';
            placeholder.style.justifyContent = 'center';
            placeholder.style.fontWeight = 'bold';
            placeholder.style.fontSize = '16px';
            pictureDiv.appendChild(placeholder);
        }
        pictureCell.appendChild(pictureDiv);
        
        // Create other cells
        const nameCell = document.createElement('td');
        nameCell.textContent = user.name;
        
        const statusCell = document.createElement('td');
        const statusBadge = document.createElement('span');
        statusBadge.className = `status-badge status-${user.status}`;
        statusBadge.textContent = user.status;
        statusCell.appendChild(statusBadge);
        
        const categoryCell = document.createElement('td');
        const categoryBadge = document.createElement('span');
        categoryBadge.className = `status-badge status-${user.category}`;
        categoryBadge.textContent = user.category;
        categoryCell.appendChild(categoryBadge);
        
        const typeCell = document.createElement('td');
        typeCell.textContent = user.type;
        
        const emailCell = document.createElement('td');
        emailCell.textContent = user.email;
        
        const fieldCell = document.createElement('td');
        fieldCell.textContent = user.field;
        
        const yearCell = document.createElement('td');
        yearCell.textContent = user.year;
        
        // Append all cells to row
        row.appendChild(checkboxCell);
        row.appendChild(pictureCell);
        row.appendChild(nameCell);
        row.appendChild(statusCell);
        row.appendChild(categoryCell);
        row.appendChild(typeCell);
        row.appendChild(emailCell);
        row.appendChild(fieldCell);
        row.appendChild(yearCell);
        
        tableBody.appendChild(row);
        
        // Add click event for status badge
        statusBadge.addEventListener('click', function(e) {
            e.stopPropagation();
            showStatusOptions(this, user.id, user.status);
        });
        
        // Add row click event
        row.addEventListener('click', function(e) {
            if (e.target.type !== 'checkbox' && !e.target.classList.contains('status-badge')) {
                editUser(user);
            }
        });
    });
}

// Rest of your functions remain the same...
function closeModal() {
    document.getElementById('user-modal').style.display = 'none';
    document.body.style.overflow = 'auto';
    document.getElementById('user-form').reset();
    document.getElementById('user-form').removeAttribute('data-user-id');
}

function saveUser() {
    const form = document.getElementById('user-form');
    const formData = new FormData();
    const userId = form.dataset.userId;
    
    const name = document.getElementById('user-name').value;
    const email = document.getElementById('user-email').value;
    
    if (!name) {
        showNotification('Please enter a user name', 'error');
        return;
    }
    
    if (!email) {
        showNotification('Please enter an email address', 'error');
        return;
    }
    
    formData.append('user-name', name);
    formData.append('user-email', email);
    formData.append('user-category', document.getElementById('user-category').value);
    formData.append('user-type', document.getElementById('user-type').value);
    formData.append('user-field', document.getElementById('user-field').value);
    formData.append('user-year', document.getElementById('user-year').value);
    formData.append('user-status', document.getElementById('user-status').checked);
    
    const userImage = document.getElementById('user-image').files[0];
    if (userImage) {
        formData.append('user-image', userImage);
    }
    
    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Determine if this is an edit or create
    let url = '/api/users/add/';
    let method = 'POST';
    
    if (userId) {
        url = `/api/users/${userId}/update/`;
        method = 'PUT';
        formData.append('user-id', userId);
    }
    
    fetch(url, {
        method: method,
        headers: {
            'X-CSRFToken': csrfToken,
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification(userId ? 'User updated successfully!' : 'User added successfully!', 'success');
            closeModal();
            loadUsers();
        } else {
            showNotification(data.message || 'Error saving user.', 'error');
        }
    })
    .catch(error => {
        console.error('Error saving user:', error);
        showNotification('Error saving user. Please try again.', 'error');
        
        // For demo purposes if the API isn't connected yet
        if (!document.querySelector('[name=csrfmiddlewaretoken]')) {
            showNotification('Demo mode: User would be saved in production.', 'success');
            closeModal();
        }
    });
}

function editUser(user) {
    document.getElementById('user-modal').style.display = 'flex';
    document.querySelector('.modal-header h3').textContent = 'Edit User';
    
    // Fill form with user data
    document.getElementById('user-name').value = user.name;
    document.getElementById('user-email').value = user.email;
    document.getElementById('user-category').value = user.category.toLowerCase();
    document.getElementById('user-type').value = user.type;
    document.getElementById('user-field').value = user.field || '';
    document.getElementById('user-year').value = user.year || '';
    document.getElementById('user-status').checked = user.status === 'approved';
    document.querySelector('.toggle-label').textContent = user.status === 'approved' ? 'Active' : 'Inactive';
    
    // Store user ID for update
    document.getElementById('user-form').dataset.userId = user.id;
}

function showStatusOptions(element, userId, currentStatus) {
    // Create dropdown for status change
    const dropdown = document.createElement('div');
    dropdown.className = 'status-dropdown';
    
    const options = ['pending', 'approved', 'rejected'];
    options.forEach(status => {
        if (status !== currentStatus) {
            const option = document.createElement('a');
            option.href = '#';
            option.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            option.addEventListener('click', function(e) {
                e.preventDefault();
                changeUserStatus(userId, status, element);
                document.body.removeChild(dropdown);
            });
            dropdown.appendChild(option);
        }
    });
    
    // Position dropdown at status badge
    const rect = element.getBoundingClientRect();
    dropdown.style.position = 'absolute';
    dropdown.style.top = rect.bottom + window.scrollY + 'px';
    dropdown.style.left = rect.left + window.scrollX + 'px';
    dropdown.style.backgroundColor = 'white';
    dropdown.style.border = '1px solid #e5e7eb';
    dropdown.style.borderRadius = '4px';
    dropdown.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
    dropdown.style.zIndex = '1000';
    dropdown.style.minWidth = '120px';
    
    // Add to body and handle outside click
    document.body.appendChild(dropdown);
    
    document.addEventListener('click', function closeDropdown(e) {
        if (!dropdown.contains(e.target) && e.target !== element) {
            document.body.removeChild(dropdown);
            document.removeEventListener('click', closeDropdown);
        }
    });
}

function changeUserStatus(userId, status, element) {
    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(`/api/users/${userId}/status/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ status: status })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Update UI
            element.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            element.className = 'status-badge status-' + status.toLowerCase();
            showNotification('User status updated!', 'success');
        } else {
            showNotification(data.message || 'Error updating status.', 'error');
        }
    })
    .catch(error => {
        console.error('Error changing status:', error);
        showNotification('Error updating status. Please try again.', 'error');
        
        // For demo purposes if API isn't connected yet
        if (!document.querySelector('[name=csrfmiddlewaretoken]')) {
            element.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            element.className = 'status-badge status-' + status.toLowerCase();
            showNotification('Demo mode: Status would be updated in production.', 'success');
        }
    });
}

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = 'notification show ' + type;
    
    setTimeout(() => {
        notification.className = 'notification';
    }, 3000);
}