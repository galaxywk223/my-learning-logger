// 文件路径: static/main.js
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

            if (result.reload) {
                setTimeout(() => window.location.reload(), 500);
                return;
            }

            if (result.html && result.target_container) {
                const container = document.querySelector(result.target_container);
                if (container) {
                    const action = result.action === 'append' ? 'beforeend' : 'afterbegin';
                    container.insertAdjacentHTML(action, result.html);
                    const newElement = action === 'beforeend' ? container.lastElementChild : container.firstElementChild;
                    const sibling = newElement.nextElementSibling;
                    const nodesToRender = sibling ? [newElement, sibling] : [newElement];
                    lucide.createIcons({nodes: nodesToRender});
                } else {
                    showToast('正在为您刷新页面以显示新的一天...', 'info');
                    setTimeout(() => window.location.reload(), 800);
                    return;
                }
                form.reset();
            }

            if (result.updates) {
                for (const key in result.updates) {
                    const updateInfo = result.updates[key];
                    const targetElement = document.querySelector(updateInfo.target_id);
                    if (targetElement) {
                        targetElement.textContent = updateInfo.value;
                    }
                }
            }

            const targetsToRemove = result.remove_target ? [result.remove_target] : (result.remove_targets || []);
            if (targetsToRemove.length > 0) {
                targetsToRemove.forEach(selector => {
                    const elementToRemove = document.querySelector(selector);
                    if (elementToRemove) {
                        elementToRemove.style.transition = 'opacity 0.3s ease';
                        elementToRemove.style.opacity = '0';
                        setTimeout(() => elementToRemove.remove(), 300);
                    }
                });
            }

        } else {
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


document.addEventListener('submit', function (event) {
    if (event.target.matches('form.ajax-form')) {
        event.preventDefault();
        handleAjaxFormSubmit(event.target);
    }
});
