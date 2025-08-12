window.addEventListener("DOMContentLoaded", () => {
    const apiUrl = "https://twitchtracker.com/api/channels/summary/vedal987";
    const targetElement = document.getElementById("avg-viewers");
    let retryCount = 0;
    const maxRetries = 1;

    let timeoutId = null;  // 用于5小时后重新请求

    async function fetchAvgViewers() {
        try {
            const controller = new AbortController();
            const fetchTimeout = setTimeout(() => controller.abort(), 3000); // 3秒超时

            const response = await fetch(apiUrl, { signal: controller.signal });
            clearTimeout(fetchTimeout);

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            if (data && typeof data.avg_viewers === "number") {
                targetElement.textContent = data.avg_viewers.toLocaleString();
                retryCount = 0; // 成功重置重试计数

                // 成功后5小时再次获取
                if (timeoutId) clearTimeout(timeoutId);
                timeoutId = setTimeout(fetchAvgViewers, 5 * 60 * 60 * 1000); // 5小时后调用自己
            } else {
                throw new Error("接口数据格式异常");
            }
        } catch (error) {
            console.warn("获取 avg_viewers 失败:", error.message);
            retryCount++;
            if (retryCount > maxRetries) {
                // 超过重试次数，1分钟后重试
                console.log("停止获取，1分钟后重试...");
                setTimeout(() => {
                    retryCount = 0;
                    fetchAvgViewers();
                }, 60 * 1000);
            } else {
                // 立即重试一次
                fetchAvgViewers();
            }
        }
    }

    // 页面加载后立即调用一次
    fetchAvgViewers();
});
