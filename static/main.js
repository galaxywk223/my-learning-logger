/**
 * Creates and displays a Bootstrap toast notification.
 * @param {string} message - The message to display.
 * @param {string} category - The category of the message ('success', 'error', 'info', 'warning').
 */
const showToast = (message, category = 'info') => {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        console.error('Toast container element not found!');
        return;
    }

    const toastInfoMap = {
        success: {bg: 'bg-success', title: '成功'},
        danger: {bg: 'bg-danger', title: '错误'},
        error: {bg: 'bg-danger', title: '错误'},
        info: {bg: 'bg-primary', title: '提示'},
        warning: {bg: 'bg-warning', title: '警告'}
    };
    const toastInfo = toastInfoMap[category] || {bg: 'bg-secondary', title: '消息'};

    const toastId = `toast-${Date.now()}`;
    const toastHTML = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="5000">
          <div class="toast-header ${toastInfo.bg} text-white">
            <strong class="me-auto">${toastInfo.title}</strong>
            <small>刚刚</small>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
          <div class="toast-body">
            ${message}
          </div>
        </div>`;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const newToast = new bootstrap.Toast(toastElement);
    newToast.show();
    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
};

/**
 * NEW & IMPROVED: Handles all AJAX form submissions gracefully.
 * This function is designed to be more generic.
 * @param {HTMLFormElement} form - The form element being submitted.
 */
const handleAjaxFormSubmit = async (form) => {
    const modalInstance = form.closest('.modal') ? bootstrap.Modal.getInstance(form.closest('.modal')) : null;

    try {
        const formData = new FormData(form);
        const response = await fetch(form.action, {
            method: form.method || 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            }
        });

        const result = await response.json();

        if (response.ok) {
            showToast(result.message || '操作成功！', 'success');

            if (modalInstance) modalInstance.hide();

            // --- SCENARIO 1: Reload the page ---
            // The server can ask for a reload by sending { "reload": true }
            if (result.reload) {
                setTimeout(() => window.location.reload(), 500);
                return;
            }

            // --- SCENARIO 2: Inject new HTML content ---
            // Server sends { "html": "...", "target_container": "#id", "action": "append/prepend" }
            if (result.html && result.target_container) {
                const container = document.querySelector(result.target_container);
                if (container) {
                    const action = result.action === 'append' ? 'beforeend' : 'afterbegin';
                    container.insertAdjacentHTML(action, result.html);
                    lucide.createIcons({ nodes: [container.lastElementChild] });
                }
                form.reset(); // Reset form after successful submission
            }

            // --- SCENARIO 3: Update specific element's text content ---
            // Server sends { "update_target": "#id", "update_content": "New text" }
            if (result.update_target && result.update_content) {
                const targetElement = document.querySelector(result.update_target);
                if (targetElement) {
                    targetElement.textContent = result.update_content;
                }
            }

            // --- SCENARIO 4: Remove an element from the DOM ---
            // Server sends { "remove_target": "#id" }
            if (result.remove_target) {
                const elementToRemove = document.querySelector(result.remove_target);
                if (elementToRemove) {
                    elementToRemove.style.transition = 'opacity 0.3s ease';
                    elementToRemove.style.opacity = '0';
                    setTimeout(() => elementToRemove.remove(), 300);
                }
            }

        } else {
            // Handle server-side validation errors or other failures
            showToast(result.message || '操作失败，请检查您的输入。', 'error');
            const errorDiv = form.querySelector('.error-message');
            if (errorDiv) {
                errorDiv.textContent = result.message;
                errorDiv.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Form submission failed:', error);
        showToast('提交失败，请检查您的网络连接。', 'error');
    }
};

// --- Global Event Listener ---
// We use a single, delegated event listener to handle all our forms.
document.addEventListener('submit', function(event) {
    // Check if the submitted form has the 'ajax-form' class
    if (event.target.matches('form.ajax-form')) {
        event.preventDefault(); // Prevent the default page reload
        handleAjaxFormSubmit(event.target);
    }
});