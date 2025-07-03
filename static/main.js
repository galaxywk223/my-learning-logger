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

    // Map categories to Bootstrap background colors and titles
    const toastInfoMap = {
        success: { bg: 'bg-success', title: '成功' },
        danger: { bg: 'bg-danger', title: '错误' }, // Flask uses 'danger' for errors
        error: { bg: 'bg-danger', title: '错误' },
        info: { bg: 'bg-primary', title: '提示' },
        warning: { bg: 'bg-warning', title: '警告' }
    };
    const toastInfo = toastInfoMap[category] || { bg: 'bg-secondary', title: '消息' };

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

    // Clean up the toast from the DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
};


/**
 * Handles the submission of a form via AJAX, showing a toast notification on completion.
 * @param {HTMLFormElement} form - The form element being submitted.
 * @param {bootstrap.Modal} [modalInstance] - Optional: The modal instance to hide on success.
 * @param {boolean} [reloadPage=true] - Optional: Whether to reload the page after success.
 */
const handleAjaxFormSubmit = async (form, modalInstance = null, reloadPage = true) => {
    try {
        const formData = new FormData(form);
        const response = await fetch(form.action, {
            method: form.method || 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        const result = await response.json();

        if (result.success) {
            if (modalInstance) {
                modalInstance.hide();
            }
            showToast(result.message, 'success');

            if (reloadPage) {
                // Delay reload to allow the user to see the toast message
                setTimeout(() => location.reload(), 1500);
            }
        } else {
            // Display error message inside the form or as a toast
            const errorDiv = form.querySelector('.error-message');
            if (errorDiv) {
                errorDiv.textContent = result.message || '发生未知错误。';
                errorDiv.style.display = 'block';
            } else {
                showToast(result.message || '发生未知错误。', 'error');
            }
        }
    } catch (error) {
        console.error('Form submission failed:', error);
        showToast('提交失败，请检查您的网络连接。', 'error');
    }
};

// --- This is the function that will be attached to form submissions inside modals ---
// We make it globally available so it can be called from inline `onsubmit` attributes.
window.submitAjaxForm = (form) => {
    const modalEl = form.closest('.modal');
    const modalInstance = modalEl ? bootstrap.Modal.getInstance(modalEl) : null;
    handleAjaxFormSubmit(form, modalInstance, true);
};