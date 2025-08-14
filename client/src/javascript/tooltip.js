window.addEventListener("DOMContentLoaded", () => {
    const tooltipElements = document.querySelectorAll("[data-tooltip]");

    tooltipElements.forEach(el => {
        const tooltip = document.createElement("div");
        tooltip.className = "tooltip";
        tooltip.textContent = el.getAttribute("data-tooltip") || "";
        document.body.appendChild(tooltip);

        function showTooltip() {
            const rect = el.getBoundingClientRect();
            const scrollX = window.pageXOffset;
            const scrollY = window.pageYOffset;
            const threshold = 50;

            let top, transform;

            if (rect.top < threshold) {
                // 按钮靠近顶部，气泡显示在按钮下方
                top = rect.bottom + scrollY + 8;
                transform = "translateX(-50%)";
                tooltip.classList.add("tooltip-arrow-up");
                tooltip.classList.remove("tooltip-arrow-down");
            } else {
                // 正常显示在按钮上方
                // 需要获取tooltip的高度来正确定位
                tooltip.style.left = rect.left + rect.width / 2 + scrollX + "px";
                tooltip.style.top = rect.top + scrollY + "px";
                tooltip.style.transform = "translateX(-50%)";
                tooltip.classList.add("show");
                
                // 强制重排以获取实际高度
                const tooltipHeight = tooltip.offsetHeight;
                top = rect.top + scrollY - tooltipHeight - 8;
                
                tooltip.classList.remove("show");
                tooltip.style.top = top + "px";
                tooltip.classList.add("tooltip-arrow-down");
                tooltip.classList.remove("tooltip-arrow-up");
            }

            tooltip.style.left = rect.left + rect.width / 2 + scrollX + "px";
            tooltip.style.top = top + "px";
            tooltip.style.transform = transform;
            tooltip.classList.add("show");
        }

        function hideTooltip() {
            tooltip.classList.remove("show");
        }

        el.addEventListener("mouseenter", showTooltip);
        el.addEventListener("mouseleave", hideTooltip);
    });
});
