// file: learning_logger/static/main.js

document.addEventListener('DOMContentLoaded', () => {
    // 为所有带有 data-log-id 属性的表格行添加双击事件
    const logRows = document.querySelectorAll('tr[data-log-id]');

    logRows.forEach(row => {
        // 1. 添加可交互的鼠标指针样式
        row.style.cursor = 'pointer';

        // 2. 添加双击事件监听器
        row.addEventListener('dblclick', (event) => {
            // 获取被点击的单元格 (td)
            const clickedCell = event.target.closest('td');
            if (!clickedCell) return; // 如果没点在单元格上，则不执行任何操作

            // --- [核心修改] 检查单元格是否属于任何受保护的列 ---
            if (clickedCell.classList.contains('week-column') || clickedCell.classList.contains('day-info-column')) {
                return; // 如果是，则不执行任何操作
            }

            // 获取存储在行数据中的 logId
            const logId = row.dataset.logId;
            if (logId) {
                // 跳转到对应的编辑页面
                window.location.href = `/edit/${logId}`;
            }
        });
    });

    // --- [新增功能] 自动隐藏 Flash 消息 ---
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages) {
        flashMessages.forEach(flashMessage => {
            setTimeout(() => {
                // 平滑淡出效果
                flashMessage.style.transition = 'opacity 0.5s ease';
                flashMessage.style.opacity = '0';
                // 淡出动画结束后，彻底移除元素
                setTimeout(() => {
                    flashMessage.remove();
                }, 500); // 这里的延迟应与CSS中的transition时间匹配
            }, 4000); // 消息显示 4 秒后开始消失
        });
    }
});