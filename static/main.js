document.addEventListener('DOMContentLoaded', () => {

    /**
     * 动态创建并显示一个 Bootstrap toast 弹窗通知.
     * @param {string} message - 要显示的消息.
     * @param {string} category - 消息类别 ('success', 'error', 'info', 'warning').
     */
    const showToast = (message, category = 'success') => {
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            console.error('Toast container element not found!');
            return;
        }

        const toastInfoMap = {
            success: { bg: 'bg-success', title: '成功' },
            error: { bg: 'bg-danger', title: '错误' },
            info: { bg: 'bg-info', title: '提示' },
            warning: { bg: 'bg-warning', title: '警告' }
        };
        const toastInfo = toastInfoMap[category] || { bg: 'bg-secondary', title: '消息' };

        const toastId = `toast-${Date.now()}`;
        const toastHTML = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
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
        const newToast = new bootstrap.Toast(toastElement, { delay: 5000 });
        newToast.show();
        toastElement.addEventListener('hidden.bs.toast', function () {
            this.remove();
        });
    };

    // --- 模态框核心逻辑 ---
    const mainModalEl = document.getElementById('mainModal');
    if (mainModalEl) {
        const mainModal = new bootstrap.Modal(mainModalEl);
        const modalTitle = mainModalEl.querySelector('.modal-title');
        const modalBody = mainModalEl.querySelector('.modal-body');

        /**
         * 异步加载内容并打开模态框
         * @param {string} url - 获取表单内容的URL
         * @param {string} title - 模态框的标题
         */
        const openModal = async (url, title) => {
            modalTitle.textContent = title;
            modalBody.innerHTML = '<div class="text-center p-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            mainModal.show();

            try {
                const response = await fetch(url);
                if (!response.ok) throw new Error(`Network response was not ok. Status: ${response.status}`);
                const formHtml = await response.text();
                modalBody.innerHTML = formHtml;
                // 表单加载后，为其提交按钮附加处理器
                attachFormSubmitHandler(modalBody, mainModal);
            } catch (error) {
                modalBody.innerHTML = '<div class="alert alert-danger">无法加载内容，请稍后重试。</div>';
                console.error('Failed to load modal content:', error);
            }
        };

        /**
         * 为模态框中的表单附加提交事件监听器
         * @param {HTMLElement} container - 模态框的主体元素
         * @param {bootstrap.Modal} modalInstance - 模态框实例
         */
        const attachFormSubmitHandler = (container, modalInstance) => {
            const form = container.querySelector('form');
            if (form) {
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    // 对于删除操作，进行二次确认
                    if (form.id === 'deleteForm') {
                        if (!confirm('警告：您确定要永久删除这条记录吗？此操作无法撤销。')) {
                            return;
                        }
                    }
                    await handleFormSubmit(form, modalInstance);
                });
            }
        };

        /**
         * 通用表单提交处理函数 (AJAX)
         * @param {HTMLFormElement} form - 被提交的表单
         * @param {bootstrap.Modal} modalInstance - 模态框实例
         */
        const handleFormSubmit = async (form, modalInstance) => {
            try {
                const formData = new FormData(form);
                const response = await fetch(form.action, {
                    method: form.method || 'POST',
                    body: formData,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });

                const result = await response.json();

                if (result.success) {
                    modalInstance.hide();
                    showToast(result.message, 'success');
                    // 延迟刷新页面以显示更改，并给用户时间看toast
                    setTimeout(() => location.reload(), 1500);
                } else {
                    let errorDiv = form.querySelector('.form-error-message');
                    if (!errorDiv) {
                        errorDiv = document.createElement('div');
                        errorDiv.className = 'alert alert-danger mt-3 form-error-message';
                        form.prepend(errorDiv);
                    }
                    errorDiv.textContent = result.message || '发生未知错误。';
                }
            } catch (error) {
                console.error('Form submission failed:', error);
                let errorDiv = form.querySelector('.form-error-message');
                if (!errorDiv) {
                    errorDiv = document.createElement('div');
                    errorDiv.className = 'alert alert-danger mt-3 form-error-message';
                    form.prepend(errorDiv);
                }
                errorDiv.textContent = '提交失败，请检查您的网络连接。';
            }
        };

        // --- [核心 Bug 修复] 统一的事件监听器设置 ---
        // 使用事件委托来处理动态加载的元素，但对于页面上固定的按钮，直接监听更简单。
        // Optional chaining (?.) 避免在元素不存在的页面上抛出错误。

        // 记录页面的按钮
        document.getElementById('addRecordBtn')?.addEventListener('click', () => openModal('/records/form/add', '添加新的学习记录'));
        document.querySelectorAll('tr.record-row').forEach(row => row.addEventListener('dblclick', () => openModal(`/records/form/edit/${row.dataset.logId}`, '编辑学习记录')));

        // 编辑周/日效率的链接
        document.querySelectorAll('a.edit-week-eff').forEach(link => link.addEventListener('click', e => {
            e.preventDefault();
            openModal(`/records/form/edit_week/${link.dataset.year}/${link.dataset.weekNum}`, '编辑周效率');
        }));
        document.querySelectorAll('a.edit-day-eff').forEach(link => link.addEventListener('click', e => {
            e.preventDefault();
            openModal(`/records/form/edit_day/${link.dataset.isoDate}`, '编辑日效率');
        }));

        // 倒计时页面的按钮
        document.getElementById('addCountdownBtn')?.addEventListener('click', () => openModal('/countdown/form/add', '添加新目标'));
        document.querySelectorAll('.countdown-item[data-event-id]').forEach(row => row.addEventListener('dblclick', e => {
            // 防止点击删除按钮时触发
            if (e.target.closest('form, a, button')) return;
            openModal(`/countdown/form/edit/${row.dataset.eventId}`, '编辑目标');
        }));
    }

    // --- 实时倒计时更新 (逻辑无变化) ---
    const countdownTimers = document.querySelectorAll('.timer[data-target-utc]');
    if (countdownTimers.length > 0) {
        const updateTimers = () => {
            countdownTimers.forEach(timer => {
                const targetUTCStr = timer.dataset.targetUtc;
                if (!targetUTCStr) return;
                const targetTime = new Date(targetUTCStr).getTime();
                const now = new Date().getTime();
                const difference = targetTime - now;

                if (difference <= 0) {
                    timer.textContent = "目标时间已到！";
                    const countdownItem = timer.closest('.countdown-item');
                    countdownItem?.classList.add('table-success', 'expired');
                } else {
                    const days = Math.floor(difference / (1000 * 60 * 60 * 24));
                    const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((difference % (1000 * 60)) / 1000);
                    const pad = (num) => String(num).padStart(2, '0');
                    timer.innerHTML = `${days} 天 ${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
                }
            });
        };
        setInterval(updateTimers, 1000);
        updateTimers();
    }
});
