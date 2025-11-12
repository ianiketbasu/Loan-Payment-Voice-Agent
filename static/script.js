// Configuration
const API_BASE_URL = '/api';

// State
let customers = [];
let pollingIntervals = {};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Loan Reminder Voice Agent initialized');
    refreshCustomers();
});

// Fetch customers from backend
async function refreshCustomers() {
    try {
        showLoading();
        const response = await fetch(`${API_BASE_URL}/customers`);
        const data = await response.json();
        customers = data.customers;
        renderCustomers();
        updateStats();
        hideLoading();
    } catch (error) {
        console.error('Error fetching customers:', error);
        alert('Failed to fetch customers. Please check backend connection.');
        hideLoading();
    }
}

// Auto-refresh customers periodically to catch tool webhook updates
setInterval(() => {
    // Only refresh if not currently loading and no active polling
    if (document.getElementById('loadingOverlay').classList.contains('active')) {
        return; // Don't refresh while loading
    }
    // Refresh every 10 seconds to catch tool webhook updates
    refreshCustomers();
}, 10000);

// Render customers table
function renderCustomers() {
    const tbody = document.getElementById('customersTableBody');
    
    if (customers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px;">
                    No customers found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = customers.map(customer => `
        <tr>
            <td>${customer.id}</td>
            <td><strong>${customer.first_name} ${customer.last_name}</strong></td>
            <td>${customer.phone_number}</td>
            <td>₹${customer.loan_amount}</td>
            <td>${customer.due_date}</td>
            <td>
                <span class="status-badge status-${customer.status}">
                    ${getStatusIcon(customer.status)} ${customer.status.replace('_', ' ')}
                </span>
            </td>
            <td>
                ${customer.wants_to_pay_early ? 
                    `<span class="response-badge response-${customer.wants_to_pay_early}">${customer.wants_to_pay_early}</span>` 
                    : '-'}
            </td>
            <td>
                <button 
                    class="btn btn-success" 
                    onclick="sendReminder(${customer.id})"
                    ${customer.status !== 'pending' && customer.status !== 'completed' ? 'disabled' : ''}
                >
                    ${customer.status === 'calling' || customer.status === 'in_progress' ? 
                        'Calling...' : 
                        customer.status === 'completed' ? 
                        'Call Again' : 
                        'Send Reminder'}
                </button>
                ${customer.status === 'completed' ? 
                    `<button class="btn btn-danger" onclick="resetCustomer(${customer.id})" style="margin-left: 8px;">Reset</button>` 
                    : ''}
            </td>
        </tr>
    `).join('');
}

// Send batch reminders to all pending customers
async function sendBatchReminders() {
    // Get all pending customers
    const pendingCustomers = customers.filter(c => c.status === 'pending');
    
    if (pendingCustomers.length === 0) {
        alert('No pending customers to send reminders to.');
        return;
    }
    
    const customerNames = pendingCustomers.map(c => `${c.first_name} ${c.last_name}`).join(', ');
    const customerIds = pendingCustomers.map(c => c.id);
    
    if (!confirm(`Send batch reminders to ${pendingCustomers.length} customer(s)?\n\n${customerNames}\n\nThis will create ONE batch call with all selected customers.`)) {
        return;
    }
    
    try {
        showLoading();
        const batchBtn = document.getElementById('batchReminderBtn');
        batchBtn.disabled = true;
        batchBtn.textContent = 'Processing...';
        
        // Generate batch call name with timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const callName = `Batch Reminder - ${timestamp}`;
        
        // Call batch call API
        const response = await fetch(`${API_BASE_URL}/batch-call`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                call_name: callName,
                customer_ids: customerIds
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to initiate batch call');
        }
        
        const data = await response.json();
        
        hideLoading();
        batchBtn.disabled = false;
        batchBtn.textContent = 'Send Reminders to All';
        
        console.log('Batch call initiated:', data);
        
        // Update local state - mark all as calling
        customerIds.forEach(customerId => {
            const customerIndex = customers.findIndex(c => c.id === customerId);
            if (customerIndex !== -1) {
                customers[customerIndex].status = 'calling';
            }
        });
        
        renderCustomers();
        updateStats();
        
        alert(`Batch call initiated successfully!\n\n` +
              `Batch Name: ${data.call_name}\n` +
              `Batch ID: ${data.batch_id}\n` +
              `Recipients: ${data.recipients_count}\n\n` +
              `All customers are now being called.`);
        
    } catch (error) {
        hideLoading();
        const batchBtn = document.getElementById('batchReminderBtn');
        batchBtn.disabled = false;
        batchBtn.textContent = 'Send Reminders to All';
        console.error('Error sending batch reminders:', error);
        
        // Check for Terms & Conditions error
        let errorMessage = error.message;
        if (errorMessage.includes('batch_calling_agreement_required') || 
            errorMessage.includes('Terms & Conditions')) {
            errorMessage = 
                'BATCH CALLING TERMS & CONDITIONS REQUIRED\n\n' +
                'You need to accept the Batch Calling Terms & Conditions in your ElevenLabs account.\n\n' +
                'Steps to fix:\n' +
                '1. Go to https://elevenlabs.io and log in\n' +
                '2. Navigate to Settings or Batch Calling section\n' +
                '3. Accept the Batch Calling Terms & Conditions\n' +
                '4. Try again after accepting';
        }
        
        alert(`Error: ${errorMessage}`);
    }
}

// Send reminder to single customer - creates a batch call with 1 recipient
async function sendReminder(customerId) {
    const customer = customers.find(c => c.id === customerId);
    if (!customer) return;
    
    if (!confirm(`Send voice reminder to ${customer.first_name} ${customer.last_name}?`)) {
        return;
    }
    
    try {
        showLoading();
        
        // Generate batch call name with timestamp and customer name
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const callName = `Reminder - ${customer.first_name} ${customer.last_name} - ${timestamp}`;
        
        // Create batch call with single customer (1 recipient = 1 batch call)
        const response = await fetch(`${API_BASE_URL}/batch-call`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                call_name: callName,
                customer_ids: [customerId]  // Single customer in batch
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to initiate batch call');
        }
        
        const data = await response.json();
        
        hideLoading();
        
        console.log('Batch call initiated (single customer):', data);
        
        // Update local state
        const customerIndex = customers.findIndex(c => c.id === customerId);
        if (customerIndex !== -1) {
            customers[customerIndex].status = 'calling';
            customers[customerIndex].conversation_id = data.batch_id; // Store batch_id
            renderCustomers();
            updateStats();
        }
        
        alert(`Batch call created for ${customer.first_name} ${customer.last_name}!\n\n` +
              `Batch ID: ${data.batch_id}\n` +
              `This is a batch call with 1 recipient.`);
        
    } catch (error) {
        hideLoading();
        console.error('Error sending reminder:', error);
        
        // Check for Terms & Conditions error
        let errorMessage = error.message;
        if (errorMessage.includes('batch_calling_agreement_required') || 
            errorMessage.includes('Terms & Conditions')) {
            errorMessage = 
                'BATCH CALLING TERMS & CONDITIONS REQUIRED\n\n' +
                'You need to accept the Batch Calling Terms & Conditions in your ElevenLabs account.\n\n' +
                'Steps to fix:\n' +
                '1. Go to https://elevenlabs.io and log in\n' +
                '2. Navigate to Settings or Batch Calling section\n' +
                '3. Accept the Batch Calling Terms & Conditions\n' +
                '4. Try again after accepting';
        }
        
        alert(`Error: ${errorMessage}`);
    }
}

// Start polling for call status
function startPolling(customerId, conversationId) {
    // Stop any existing polling for this customer
    if (pollingIntervals[customerId]) {
        clearInterval(pollingIntervals[customerId]);
    }
    
    let attempts = 0;
    const maxAttempts = 60; // 5 minutes max
    
    pollingIntervals[customerId] = setInterval(async () => {
        attempts++;
        
        try {
            const response = await fetch(`${API_BASE_URL}/call-status/${conversationId}`);
            const data = await response.json();
            
            console.log(`Poll attempt ${attempts} for customer ${customerId}:`, data.status);
            
            // Update customer status
            const customerIndex = customers.findIndex(c => c.id === customerId);
            if (customerIndex !== -1) {
                if (data.status === 'done') {
                    customers[customerIndex].status = 'completed';
                    // Note: wants_to_pay_early is updated by tool webhook, not here
                    
                    // Stop polling
                    clearInterval(pollingIntervals[customerId]);
                    delete pollingIntervals[customerId];
                    
                    // Refresh from backend to get latest data (including wants_to_pay_early)
                    await refreshCustomers();
                    
                    // Show notification
                    alert(`Call completed!\n\nCustomer Response: ${data.customer_response || 'UNCLEAR'}\nPayment Intent: ${data.payment_intent ? 'Yes' : 'No'}`);
                    
                } else if (data.status === 'in_progress') {
                    customers[customerIndex].status = 'in_progress';
                    renderCustomers();
                    updateStats();
                } else if (data.status === 'failed') {
                    customers[customerIndex].status = 'error';
                    clearInterval(pollingIntervals[customerId]);
                    delete pollingIntervals[customerId];
                    renderCustomers();
                    updateStats();
                    alert('Call failed');
                }
            }
            
            // Timeout
            if (attempts >= maxAttempts) {
                clearInterval(pollingIntervals[customerId]);
                delete pollingIntervals[customerId];
                console.log('Polling timeout for customer', customerId);
            }
            
        } catch (error) {
            console.error('Polling error:', error);
        }
        
    }, 5000); // Poll every 5 seconds
}

// Reset customer status
async function resetCustomer(customerId) {
    if (!confirm('Reset this customer status to pending?')) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/customers/${customerId}/reset`, {
            method: 'PUT'
        });
        
        if (response.ok) {
            await refreshCustomers();
        }
    } catch (error) {
        console.error('Error resetting customer:', error);
    }
}

// Test backend connection
async function testConnection() {
    try {
        showLoading();
        const response = await fetch('/health');
        const data = await response.json();
        hideLoading();
        
        alert(`Backend Connection OK!\n\n` +
              `Status: ${data.status}\n` +
              `ElevenLabs Configured: ${data.elevenlabs_configured}\n` +
              `Total Customers: ${data.total_customers}`);
    } catch (error) {
        hideLoading();
        alert(`Backend connection failed!\n\n${error.message}\n\nMake sure backend is running`);
    }
}

// Update statistics
function updateStats() {
    document.getElementById('totalCustomers').textContent = customers.length;
    document.getElementById('completedCalls').textContent = 
        customers.filter(c => c.status === 'completed').length;
    document.getElementById('yesResponses').textContent = 
        customers.filter(c => c.wants_to_pay_early === 'YES').length;
    document.getElementById('noResponses').textContent = 
        customers.filter(c => c.wants_to_pay_early === 'NO').length;
}

// Get status icon
function getStatusIcon(status) {
    const icons = {
        'pending': '',
        'calling': '',
        'in_progress': '',
        'completed': '',
        'error': ''
    };
    return icons[status] || '';
}

// Loading overlay
function showLoading() {
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

