// SWUST 新生指南 - 通用脚本

document.addEventListener('DOMContentLoaded', function () {
    // 搜索框自动聚焦
    const searchInput = document.querySelector('.hero input[type="text"]');
    if (searchInput && !searchInput.value) {
        // 首页不自动聚焦，避免移动端弹出键盘遮挡
    }
});
