<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>全屏白板监听器 (V10 - 轮询版本)</title>
    <style>
        body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: white; overflow: hidden; }
        #whiteboard { position: fixed; top: 0; left: 0; width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; z-index: 1; }
        #codeDisplay { font-weight: bold; display: flex; visibility: visible; text-align: center; max-width: 90vw; max-height: 80vh; overflow-wrap: break-word; word-break: break-all; padding: 20px; line-height: 1.5; white-space: pre-wrap; overflow: visible; }
        #controls { position: fixed; bottom: 10px; left: 10px; background-color: rgba(240, 240, 240, 0.9); padding: 10px; border-radius: 8px; z-index: 10; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .slider-container { margin-bottom: 10px; }
        .slider-label { display: inline-block; width: 150px; font-size: 14px; }
        .slider-value { display: inline-block; width: 50px; text-align: right; font-weight: 500; }
        .color-buttons { display: flex; flex-wrap: nowrap; gap: 3px; margin-top: 5px; max-width: 400px; overflow-x: auto; scrollbar-width: none; -ms-overflow-style: none; }
        .color-btn { width: 24px; height: 24px; border: 1px solid #ddd; border-radius: 50%; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s; flex-shrink: 0; }
        .color-btn.active { transform: scale(1.2); box-shadow: 0 0 0 3px #1890ff; }
        .color-buttons::-webkit-scrollbar { display: none; }
        .status-panel { position: fixed; top: 10px; right: 10px; display: flex; flex-direction: column; align-items: flex-end; gap: 8px; z-index: 5; }
        .status-box { background-color: rgba(0, 0, 0, 0.7); color: white; padding: 6px 12px; border-radius: 15px; font-size: 14px; backdrop-filter: blur(5px); transition: background-color 0.5s ease; }
        .top-status-panel { position: fixed; top: 10px; right: 10px; display: flex; flex-direction: column; align-items: flex-end; gap: 8px; z-index: 20; }
        .bottom-status-panel { position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; z-index: 5; }
        #nodeStatus { cursor: pointer; }
        #nodeDetails { position: fixed; top: 50px; right: 10px; background-color: rgba(0, 0, 0, 0.85); color: white; padding: 15px; border-radius: 8px; font-size: 12px; display: none; z-index: 19; max-width: 320px; max-height: 400px; overflow-y: auto; backdrop-filter: blur(5px); }
        .node-detail-item { margin-bottom: 8px; padding: 8px; background-color: rgba(255,255,255,0.1); border-radius: 4px; }
        .node-detail-item .indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
        .indicator.healthy { background-color: #52c41a; }
        .indicator.unreachable { background-color: #faad14; }
        .indicator.unhealthy { background-color: #f5222d; }
        .bottom-right-controls { position: fixed; bottom: 10px; right: 10px; display: flex; flex-direction: column; gap: 10px; z-index: 5; }
        .bottom-right-controls button { padding: 8px 16px; font-size: 14px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .bottom-right-controls button:hover { background-color: #0056b3; }
        #skipButton { background-color: #dc3545; }
        #skipButton:hover { background-color: #c82333; }
        #clearQueueButton { background-color: #fd7e14; }
        #clearQueueButton:hover { background-color: #e55a00; }
    </style>
</head>
<body>
    <div id="whiteboard"><div id="codeDisplay"></div></div>

    <!-- 屏保显示区域 -->
    <div id="screensaver" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; display: none; justify-content: center; align-items: center; background: linear-gradient(135deg, #1a2a6c, #b21f1f, #1a2a6c); color: #fff; z-index: 2; flex-direction: column;">
        <!-- 今日天气显示区域 - 左上角 -->
        <div id="todayWeather" style="position: absolute; top: 20px; left: 20px; font-size: 2.5vw; text-align: left; line-height: 1.3;">
            <div style="font-size: 1em;">上海市宝山区 今日天气:</div>
            <div style="font-size: 1.5em; margin-top: 5px;">小雨</div>
            <div style="font-size: 1.5em;">22°C ~ 25°C</div>
        </div>

        <!-- 明日天气预报显示区域 - 右上角 -->
        <div id="tomorrowWeather" style="position: absolute; top: 20px; right: 20px; font-size: 2.5vw; text-align: right; line-height: 1.3;">
            <div style="font-size: 1em;">上海市宝山区 明日预报:</div>
            <div style="font-size: 1.5em; margin-top: 5px;">多云</div>
            <div style="font-size: 1.5em;">23°C ~ 27°C</div>
        </div>

        <div id="timeDisplay" style="font-size: 12vw; font-weight: bold; margin-bottom: 20px; text-shadow: 0 0 10px rgba(255,255,255,0.5);"></div>
        <div id="dateDisplay" style="font-size: 5vw; margin-bottom: 30px; text-shadow: 0 0 5px rgba(255,255,255,0.3);"></div>
        <div id="weatherDisplay" style="font-size: 2.5vw;"></div>
    </div>
    
    <!-- 左上角倒计时 -->
    <div id="countdownTimer" class="status-box" style="position: fixed; top: 10px; left: 10px; display: none; z-index: 20;">20s</div>

    <!-- 右上角状态面板 (节点状态、朗读状态、队列计数器) -->
    <div class="top-status-panel">
        <div id="nodeStatus" class="status-box">节点: 检查中...</div>
        <div id="readingStatus" class="status-box" style="display: none;">朗读中...</div>
        <div id="queueCounter" class="status-box" style="display: none;">队列: 0</div>
    </div>
    <div id="nodeDetails"></div>

    <!-- 底部系统状态 -->
    <div class="bottom-status-panel">
        <div id="systemStatus" class="status-box">系统: 连接中...</div>
    </div>

    <div id="controls">
        <div class="slider-container">
            <span class="slider-label">显示时间 (秒):</span>
            <input type="range" id="displayTimeSlider" min="10" max="30" value="20">
            <span class="slider-value" id="displayTimeValue">20</span>
        </div>
        <div class="slider-container">
            <span class="slider-label">语速 (倍速):</span>
            <input type="range" id="speechRateSlider" min="0.1" max="5.0" value="1.0" step="0.1">
            <span class="slider-value" id="speechRateValue">1.0</span>
        </div>
        <div class="slider-container">
            <span class="slider-label">字体大小 (vw):</span>
            <input type="range" id="fontSizeSlider" min="1" max="40" value="25" step="1">
            <span class="slider-value" id="fontSizeValue">25</span>
        </div>
        <div class="slider-container">
            <span class="slider-label">字体颜色:</span>
            <div class="color-buttons">
                <button class="color-btn active" data-color="#000000" style="background-color: #000000;" title="黑色"></button>
                <button class="color-btn" data-color="#FF0000" style="background-color: #FF0000;" title="红色"></button>
                <button class="color-btn" data-color="#0000FF" style="background-color: #0000FF;" title="蓝色"></button>
                <button class="color-btn" data-color="#00FF00" style="background-color: #00FF00;" title="绿色"></button>
                <button class="color-btn" data-color="#FFFF00" style="background-color: #FFFF00;" title="黄色"></button>
                <button class="color-btn" data-color="#FF00FF" style="background-color: #FF00FF;" title="紫色"></button>
                <button class="color-btn" data-color="#00FFFF" style="background-color: #00FFFF;" title="青色"></button>
                <button class="color-btn" data-color="#FFA500" style="background-color: #FFA500;" title="橙色"></button>
                <button class="color-btn" data-color="#800080" style="background-color: #800080;" title="深紫色"></button>
                <button class="color-btn" data-color="#FFC0CB" style="background-color: #FFC0CB;" title="粉色"></button>
                <button class="color-btn" data-color="#A52A2A" style="background-color: #A52A2A;" title="棕色"></button>
                <button class="color-btn" data-color="#808080" style="background-color: #808080;" title="灰色"></button>
            </div>
        </div>
    </div>

    <div class="bottom-right-controls">
        <button id="activateAudio">启用语音</button>
        <button id="skipButton">跳过当前</button>
        <button id="clearQueueButton">一键清空</button>
    </div>

    <script>
        // --- V9 Final --- 
        const codeDisplay = document.getElementById('codeDisplay');
        const systemStatus = document.getElementById('systemStatus');
        const nodeStatus = document.getElementById('nodeStatus');
        const queueCounter = document.getElementById('queueCounter');
        const nodeDetails = document.getElementById('nodeDetails');
        const readingStatus = document.getElementById('readingStatus');
        const countdownTimer = document.getElementById('countdownTimer');
        const controls = document.getElementById('controls');

        // --- Restored Controls ---
        const displayTimeSlider = document.getElementById('displayTimeSlider');
        const displayTimeValue = document.getElementById('displayTimeValue');
        const speechRateSlider = document.getElementById('speechRateSlider');
        const speechRateValue = document.getElementById('speechRateValue');
        const fontSizeSlider = document.getElementById('fontSizeSlider');
        const fontSizeValue = document.getElementById('fontSizeValue');
        const colorButtons = document.querySelectorAll('.color-btn');
        const skipButton = document.getElementById('skipButton');
        const activateAudioButton = document.getElementById('activateAudio');
        const clearQueueButton = document.getElementById('clearQueueButton');

        // --- State ---
        let codeQueue = [];
        let isDisplaying = false;
        let nodeDetailsVisible = false;
        let isSpeechEnabled = false;
        let currentDisplayTimer = null;
        let countdownInterval = null;
        let lastPollTime = 0; // 跟踪最后轮询时间戳
        let remainingTime = 0;
        let currentDisplayingCode = null; // 追踪当前正在显示的消息，用于队列去重

        // 连接状态监控变量
        let connectionState = 'unknown'; // 'healthy', 'stale', 'error', 'unknown'
        let consecutivePollFailures = 0; // 轮询连续失败次数
        let localPollStatus = 'unknown'; // 本地轮询接口状态

        // 屏保相关变量
        let screensaverInterval = null;
        let isScreensaverActive = false;

		// 添加这个跟触发系统重置相关的变量声明
		// let lastDisplayStartTime = 0;

        // 连接状态监控
        function updateConnectionState(newState) {
            connectionState = newState;

            // 根据连接状态更新UI
            switch (newState) {
                case 'healthy':
                    systemStatus.textContent = '系统: 连接正常';
                    systemStatus.style.backgroundColor = '#52c41a';
                    break;
                case 'stale':
                    systemStatus.textContent = '系统: 连接可能停滞';
                    systemStatus.style.backgroundColor = '#faad14';
                    showRefreshSuggestion('连接似乎停滞，建议刷新页面');
                    break;
                case 'error':
                    systemStatus.textContent = '系统: 连接错误';
                    systemStatus.style.backgroundColor = '#f5222d';
                    break;
            }
        }

        // 显示刷新建议
        function showRefreshSuggestion(message) {
            // 检查是否已经显示了提示，避免重复显示
            const existingSuggestion = document.querySelector('.refresh-suggestion');
            if (existingSuggestion) {
                return;
            }

            // 创建提示元素
            const suggestionDiv = document.createElement('div');
            suggestionDiv.className = 'refresh-suggestion';
            suggestionDiv.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: #fffbe6;
                border: 2px solid #ffe58f;
                border-radius: 8px;
                padding: 20px;
                margin: 10px;
                z-index: 1000;
                text-align: center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                max-width: 90%;
            `;
            suggestionDiv.innerHTML = `
                <div style="font-size: 18px; margin-bottom: 15px; font-weight: bold; color: #d48806;">
                    <span style="font-size: 24px; margin-right: 10px;">⚠️</span>
                    系统提示
                </div>
                <div style="font-size: 16px; margin-bottom: 20px; color: #666;">
                    ${message}
                </div>
                <div>
                    <button onclick="location.reload()" style="padding: 10px 20px; background: #1890ff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin-right: 10px;">
                        刷新页面
                    </button>
                    <button onclick="this.parentElement.parentElement.remove()" style="padding: 10px 20px; background: #ccc; color: #333; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;">
                        稍后提醒我
                    </button>
                </div>
            `;

            // 添加到页面
            document.body.appendChild(suggestionDiv);
        }

        // 隐藏刷新建议
        function hideRefreshSuggestion() {
            const existingSuggestion = document.querySelector('.refresh-suggestion');
            if (existingSuggestion) {
                existingSuggestion.remove();
            }
        }

        function adjustTextToFit(element, text) {
            // 创建测试元素进行精确计算
			console.time('adjustTextToFit');
			let loopCount = 0;
            const testElement = document.createElement('div');
            testElement.style.position = 'absolute';
            testElement.style.visibility = 'hidden';
            testElement.style.whiteSpace = 'pre-wrap';
            testElement.style.padding = '20px';
            testElement.style.fontWeight = 'bold';
            testElement.style.lineHeight = '1.5';
            document.body.appendChild(testElement);

            let fontSize = 40, maxChars = 5;
            while (fontSize >= 1) {
                while (maxChars <= 50) {
					loopCount++;
                    const formattedCode = formatCodeText(text, maxChars);
                    testElement.textContent = formattedCode;
                    testElement.style.fontSize = fontSize + 'vw';

                    // 检查是否在屏幕限制内 (85%宽度, 80%高度)
                    if (testElement.offsetWidth / window.innerWidth <= 0.85 &&
                        testElement.offsetHeight / window.innerHeight <= 0.8) {
                        document.body.removeChild(testElement);

                        // 应用到实际元素
                        element.textContent = formattedCode;
                        element.style.fontSize = fontSize + 'vw';

                        // 同步更新字体大小滑块
                        const fontSizeSlider = document.getElementById('fontSizeSlider');
                        const fontSizeValue = document.getElementById('fontSizeValue');
                        if (fontSizeSlider && fontSizeValue) {
                            fontSizeSlider.value = fontSize;
                            fontSizeValue.textContent = fontSize;
                        }
						console.timeEnd('adjustTextToFit');
						console.log('循环次数:', loopCount);
                        return { fontSize, maxChars, formattedCode };
                    }
                    maxChars += 1;
                }
                maxChars = 5;
                fontSize -= 1;
            }

            document.body.removeChild(testElement);
            // 最小回退值
            const fallbackCode = formatCodeText(text, 50);
            element.textContent = fallbackCode;
            element.style.fontSize = '1vw';
			console.timeEnd('adjustTextToFit');
			console.log('循环次数:', loopCount);
            return { fontSize: 1, maxChars: 50, formattedCode: fallbackCode };
        }

        // 格式化验证码文本，按指定字符数换行
        function formatCodeText(code, maxCharsPerLine) {
            if (!code) return '';

            // 如果是纯数字验证码且长度较短，不需要换行
            if (/^\d+$/.test(code) && code.length <= 8) {
                return code;
            }

            // 对于较长的文本，按指定字符数换行
            let formatted = '';
            for (let i = 0; i < code.length; i += maxCharsPerLine) {
                if (formatted !== '') formatted += '\n';
                formatted += code.substring(i, i + maxCharsPerLine);
            }
            return formatted;
        }

        // --- 相似度计算函数 ---
        function calculateSimilarity(str1, str2) {
            // 使用编辑距离（Levenshtein距离）计算相似度
            const longer = str1.length > str2.length ? str1 : str2;
            const shorter = str1.length > str2.length ? str2 : str1;
            
            if (longer.length === 0) return 1.0;
            
            // 计算编辑距离
            const editDistance = levenshteinDistance(longer, shorter);
            
            // 计算相似度百分比
            return (longer.length - editDistance) / longer.length;
        }
        
        // --- 编辑距离计算 ---
        function levenshteinDistance(str1, str2) {
            const matrix = [];
            
            for (let i = 0; i <= str2.length; i++) {
                matrix[i] = [i];
            }
            
            for (let j = 0; j <= str1.length; j++) {
                matrix[0][j] = j;
            }
            
            for (let i = 1; i <= str2.length; i++) {
                for (let j = 1; j <= str1.length; j++) {
                    if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                        matrix[i][j] = matrix[i - 1][j - 1];
                    } else {
                        matrix[i][j] = Math.min(
                            matrix[i - 1][j - 1] + 1,
                            matrix[i][j - 1] + 1,
                            matrix[i - 1][j] + 1
                        );
                    }
                }
            }
            
            return matrix[str2.length][str1.length];
        }
        
        // --- Core Display Logic ---
        function displayCode(code) {
            try {
                // 如果有消息要显示，先隐藏屏保
                hideScreensaver();

                // 隐藏轮询失败警告窗口
                hideRefreshSuggestion();

                if (isDisplaying) {
                    // 队列去重：检查是否与当前显示的消息重复
                    if (currentDisplayingCode === code) {
                        console.log("队列去重: 与当前显示消息重复，跳过 -", code);
                        return;
                    }

                    // 队列去重：基于相似度检查
                    const similarityThreshold = 0.70; // 70%相似度阈值
                    const hasDuplicateInQueue = codeQueue.some(item => {
                        if (item.code === code) return true;
                        const similarity = calculateSimilarity(code, item.code);
                        return similarity >= similarityThreshold;
                    });

                    if (!hasDuplicateInQueue) {
                        codeQueue.push({ code });
                        updateQueueCounter();
                    } else {
                        console.log("队列去重: 队列中已有相似消息，跳过 -", code);
                    }
                    return;
                }

                // 记录当前显示的消息
                currentDisplayingCode = code;
                isDisplaying = true;

                // 使用新的智能字体自适应算法
                adjustTextToFit(codeDisplay, code);
                codeDisplay.style.display = 'flex'; // 改为flex以确保正确显示
                codeDisplay.style.visibility = 'visible'; // 确保可见
                codeDisplay.textContent = code; // 确保设置文本内容

                // 启动倒计时
                const displayTime = parseInt(displayTimeSlider.value);
                remainingTime = displayTime;
                countdownTimer.style.display = 'block';
                updateCountdownDisplay();

                // 清除之前的倒计时
                if (countdownInterval) {
                    clearInterval(countdownInterval);
                }

                // 每秒更新倒计时
                countdownInterval = setInterval(() => {
                    remainingTime--;
                    updateCountdownDisplay();
                    if (remainingTime <= 0) {
                        clearInterval(countdownInterval);
                        // 倒计时结束，检查是否还在朗读
                        if (window.speechSynthesis.speaking) {
                            remainingTime = -1; // 显示为-1
                            updateCountdownDisplay();
                        } else {
                            // 没有在朗读，直接进入下一条
                            hideCode();
                        }
                    }
                }, 1000);

                // 语音朗读完成的回调
                const onSpeechEnd = () => {
                    if (remainingTime <= 0) {
                        // 倒计时已经结束，立即进入下一条
                        hideCode();
                    }
                    // 如果倒计时还没结束，继续等待倒计时
                };

                speakCode(code, false, onSpeechEnd);

                // 设置定时器作为备用（防止语音朗读无限期等待）
                currentDisplayTimer = setTimeout(() => {
                    if (window.speechSynthesis.speaking) {
                        // 如果还在朗读，显示-1并等待
                        remainingTime = -1;
                        updateCountdownDisplay();
                    } else {
                        hideCode();
                    }
                }, displayTime * 1000 + 5000); // 增加5秒缓冲时间

            } catch (error) {
                console.error("显示消息时出错:", error);
                hideCode(); // 出错时强制隐藏并继续处理队列
            }
        }

        function hideCode() {
            try {
                // 清除所有定时器
                if(currentDisplayTimer) clearTimeout(currentDisplayTimer);
                if(countdownInterval) clearInterval(countdownInterval);

                // 取消所有语音
                if (window.speechSynthesis) {
                    window.speechSynthesis.cancel();
                }

                // 隐藏显示元素
                if (codeDisplay) {
                    codeDisplay.style.display = 'none';
                    codeDisplay.style.visibility = 'hidden';
                    // 重置文本内容
                    codeDisplay.textContent = '';
                }
                if (countdownTimer) {
                    countdownTimer.style.display = 'none';
                }

                // 重置状态变量
                remainingTime = 0;
                isDisplaying = false;
                currentDisplayingCode = null;

            } catch (error) {
                console.error("隐藏消息时出错:", error);
                // 即使出错也要重置关键状态
                isDisplaying = false;
                currentDisplayingCode = null;
            } finally {
                // 确保继续处理队列
                setTimeout(() => {
                    try {
                        processCodeQueue();
                        checkScreensaver();
                    } catch (e) {
                        console.error("处理队列或屏保检查时出错:", e);
                    }
                }, 100);
            }
        }

        function clearQueue() {
            // 停止当前显示和语音
            if(currentDisplayTimer) clearTimeout(currentDisplayTimer);
            if(countdownInterval) clearInterval(countdownInterval);
            window.speechSynthesis.cancel();
            
            // 隐藏当前显示
            codeDisplay.style.display = 'none';
            countdownTimer.style.display = 'none';
            remainingTime = 0; // 重置倒计时
            isDisplaying = false;
            
            // 清除当前显示消息记录
            currentDisplayingCode = null;
            
            // 清空队列
            codeQueue = [];
            updateQueueCounter();
            
            // 调用服务器API清空数据文件
            fetch('clear_queue.php')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('队列已清空');
                    } else {
                        console.error('清空队列失败:', data.error);
                    }
                })
                .catch(error => {
                    console.error('清空队列请求失败:', error);
                });
        }

        function processCodeQueue() {
            try {
                if (isDisplaying || codeQueue.length === 0) {
                    // 检查是否应该显示屏保
                    checkScreensaver();
                    return;
                }

                // 添加队列处理超时保护
                const item = codeQueue.shift();
                if (!item || !item.code) {
                    console.warn("队列中存在无效消息项:", item);
                    updateQueueCounter();
                    checkScreensaver();
                    return;
                }

                updateQueueCounter();
                displayCode(item.code);

            } catch (error) {
                console.error("处理队列消息时出错:", error);
                // 确保即使出错也能继续处理其他消息
                isDisplaying = false;
                currentDisplayingCode = null;

                // 稍后重试处理队列
                setTimeout(() => {
                    processCodeQueue();
                }, 1000);
            }
        }

        function updateQueueCounter() {
            queueCounter.textContent = `队列: ${codeQueue.length}`;
            queueCounter.style.display = codeQueue.length > 0 ? 'block' : 'none';
        }

        function updateCountdownDisplay() {
            if (remainingTime === -1) {
                countdownTimer.textContent = '朗读中...';
            } else {
                countdownTimer.textContent = `${remainingTime}s`;
            }
        }

        // --- 轮询版本实时逻辑 ---
        let lastMessageId = 0;
        let pollingInterval = null;
        let lastProcessedCodes = new Set(); // 已处理的消息缓存
        let isPolling = false; // 防止并发轮询

        // 初始化时获取最新的消息ID
        async function initializeLastMessageId() {
            try {
                const response = await fetch('./events.php');
                const data = await response.json();
                if (data.last_id !== undefined) {
                    lastMessageId = data.last_id;
                    console.log('初始化 lastMessageId:', lastMessageId);
                }
            } catch (error) {
                console.error('初始化 lastMessageId 失败:', error);
            }
        }

        async function pollForMessages() {
            // 防止并发轮询
            if (isPolling) return;
            isPolling = true;

            try {
                // 设置超时控制器
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时

                // 为安卓兼容性添加时间戳防止缓存
                const timestamp = new Date().getTime();
                const response = await fetch(`./events.php?last_id=${lastMessageId}&t=${timestamp}`, {
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                // 检查HTTP状态码
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();

                // 检查响应数据完整性
                if (!data || typeof data !== 'object') {
                    throw new Error('Invalid response format');
                }

                // 更新最后轮询时间
                lastPollTime = Date.now();

                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        console.log("轮询消息收到:", msg);
                        if (msg && msg.code) {
                            // 去重：避免重复处理相同消息
                            const msgKey = msg.code + '_' + msg.timestamp;
                            if (!lastProcessedCodes.has(msgKey)) {
                                displayCode(msg.code);
                                lastProcessedCodes.add(msgKey);

                                // 清理缓存，防止内存泄漏
                                if (lastProcessedCodes.size > 100) {
                                    const oldestKeys = Array.from(lastProcessedCodes).slice(0, 20);
                                    oldestKeys.forEach(key => lastProcessedCodes.delete(key));
                                }
                            }
                        }
                    });
                    // 更新 lastMessageId 为最新消息的ID
                    if (data.messages.length > 0) {
                        const latestMsg = data.messages[data.messages.length - 1];
                        lastMessageId = latestMsg.id;
                    }
                }

                // 更新系统状态显示
                systemStatus.textContent = '系统: 轮询连接正常';
                systemStatus.style.backgroundColor = '#52c41a';

                // 隐藏轮询失败警告窗口
                hideRefreshSuggestion();

                // 重置连续失败计数
                consecutivePollFailures = 0;

            } catch (error) {
                console.error("轮询错误:", error);
                systemStatus.textContent = '系统: 轮询连接失败';
                systemStatus.style.backgroundColor = '#f5222d';

                // 增加连续失败计数
                consecutivePollFailures = (consecutivePollFailures || 0) + 1;

                // 如果连续失败超过10次，建议刷新页面
                if (consecutivePollFailures >= 10) {
                    showRefreshSuggestion('轮询连续失败，建议刷新页面');
                }
            } finally {
                // 重置轮询状态
                isPolling = false;
            }
        }

        async function startPolling() {
            console.log('启动轮询系统...');
            systemStatus.textContent = '系统: 连接中...';
            systemStatus.style.backgroundColor = '#faad14';
            
            // 首先初始化lastMessageId
            await initializeLastMessageId();
            
            // 立即执行一次轮询
            await pollForMessages();
            
            // 每3秒轮询一次
            pollingInterval = setInterval(pollForMessages, 3000);
        }

        function stopPolling() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
            }
        }

        // --- 智能健康检查策略（混合方案1+2+5）---
        let healthCheckInterval = null;
        let heartbeatInterval = null;
        let nodeHealthHistory = {}; // 节点健康历史记录
        let consecutiveFailures = {}; // 连续失败次数
        let lastHeartbeatCheck = 0; // 上次心跳检查时间
        let baseCheckInterval = 60000; // 基础检查间隔60秒
        let heartbeatIntervalTime = 300000; // 心跳间隔5分钟
        
        // 获取节点检查间隔（自适应）
        function getNodeCheckInterval(nodeId) {
            const failures = consecutiveFailures[nodeId] || 0;
            
            // 指数退避算法
            if (failures === 0) {
                return baseCheckInterval; // 正常节点：60秒
            } else if (failures === 1) {
                return 30000; // 第一次失败：30秒
            } else if (failures === 2) {
                return 60000; // 第二次失败：60秒
            } else {
                return Math.min(baseCheckInterval * Math.pow(2, failures - 2), 300000); // 指数退避，最大5分钟
            }
        }
        
        // 获取整体集群检查间隔
        function getClusterCheckInterval() {
            const nodeIds = Object.keys(consecutiveFailures);
            if (nodeIds.length === 0) return baseCheckInterval;
            
            // 如果有任何节点连续失败超过2次，使用更短的间隔
            const hasProblematicNodes = nodeIds.some(id => consecutiveFailures[id] > 2);
            return hasProblematicNodes ? Math.min(baseCheckInterval / 2, 30000) : baseCheckInterval;
        }
        
        // 简化的节点状态检查
        async function checkNodeStatus() {
            try {
                // 检查远程节点状态 - 使用AbortController实现超时
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 8000);

                const startTime = Date.now();
                const response = await fetch('https://mnizz.fly.dev/check.php?action=keepalive', {
                    method: 'GET',
                    signal: controller.signal,
                    mode: 'cors',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });

                clearTimeout(timeoutId);
                const responseTime = (Date.now() - startTime) / 1000;

                if (response.ok) {
                    const data = await response.json();
                    if (data && data.status === 'ok') {
                        // 远程节点正常
                        consecutiveFailures['mnizz'] = 0;
                        nodeHealthHistory['mnizz'] = {
                            status: 'healthy',
                            lastCheck: Date.now(),
                            responseTime: responseTime
                        };
                        console.log('远程节点检查成功，响应时间:', responseTime + 's');
                    } else {
                        throw new Error('Remote node response invalid: ' + JSON.stringify(data));
                    }
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            } catch (error) {
                console.error('远程节点检查失败:', error.message);
                consecutiveFailures['mnizz'] = (consecutiveFailures['mnizz'] || 0) + 1;
                nodeHealthHistory['mnizz'] = {
                    status: 'unhealthy',
                    lastCheck: Date.now(),
                    responseTime: 0
                };
            }
        }

        // 增强的健康检查
        async function enhancedHealthCheck() {
            try {
                // 检查轮询连接状态
                const now = Date.now();
                const timeSinceLastPoll = now - lastPollTime;

                // 如果超过30秒没有轮询成功，标记为潜在问题
                if (lastPollTime > 0 && timeSinceLastPoll > 30000) {
                    systemStatus.textContent = '系统: 轮询可能停滞';
                    systemStatus.style.backgroundColor = '#faad14';
                }

                // 检查远程节点状态
                await checkNodeStatus();

                // 检查本地轮询接口可用性
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000);

                const response = await fetch('./events.php?last_id=0', {
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`Poll endpoint HTTP ${response.status}`);
                }

                const data = await response.json();
                if (!data || typeof data !== 'object') {
                    throw new Error('Poll endpoint invalid response');
                }

                // 更新本地轮询状态
                localPollStatus = 'healthy';

            } catch (error) {
                console.error('健康检查失败:', error);
                localPollStatus = 'unhealthy';

                // 如果本地轮询接口不可用，建议刷新
                if (error.name === 'AbortError' || error.message.includes('HTTP')) {
                    showRefreshSuggestion('本地轮询接口异常，建议刷新页面');
                }
            }
        }
        
        // 更新节点健康历史
        function updateNodeHealthHistory(nodes) {
            const currentTime = Date.now();
            
            nodes.forEach(node => {
                const nodeId = node.node_id;
                const wasHealthy = nodeHealthHistory[nodeId]?.status === 'healthy';
                const isHealthy = node.status === 'healthy';
                
                // 更新历史记录
                nodeHealthHistory[nodeId] = {
                    status: node.status,
                    lastCheck: currentTime,
                    responseTime: node.response_time
                };
                
                // 更新连续失败计数
                if (isHealthy) {
                    consecutiveFailures[nodeId] = 0; // 重置失败计数
                } else if (wasHealthy) {
                    consecutiveFailures[nodeId] = 1; // 第一次失败
                } else {
                    consecutiveFailures[nodeId]++; // 增加失败计数
                }
            });
            
            // 清理超过1小时未检查的节点记录
            const oneHourAgo = currentTime - 3600000;
            Object.keys(nodeHealthHistory).forEach(nodeId => {
                if (nodeHealthHistory[nodeId].lastCheck < oneHourAgo) {
                    delete nodeHealthHistory[nodeId];
                    delete consecutiveFailures[nodeId];
                }
            });
        }
        
        // 更新集群状态函数
        async function updateClusterStatus() {
            try {
                // 执行增强的健康检查
                await enhancedHealthCheck();

                // 更新状态显示
                const totalNodes = 2; // 固定两个节点
                const healthyNodes = nodeHealthHistory['mnizz']?.status === 'healthy' ? 2 : 1;

                nodeStatus.textContent = `节点: ${healthyNodes}/${totalNodes}`;
                nodeStatus.style.backgroundColor = healthyNodes === totalNodes ? '#52c41a' : '#faad14';

                // 更新节点详情显示
                const nodes = [
                    {
                        node_id: 'zzsolo',
                        status: 'healthy',
                        response_time: 0.1,
                        is_current: true
                    },
                    {
                        node_id: 'mnizz',
                        status: nodeHealthHistory['mnizz']?.status || 'unknown',
                        response_time: nodeHealthHistory['mnizz']?.responseTime || 0,
                        is_current: false
                    }
                ];
                renderNodeDetails(nodes);

            } catch (error) {
                console.error('Failed to update cluster status:', error);
                nodeStatus.textContent = `节点: 离线`;
                nodeStatus.style.backgroundColor = '#f5222d';
            }
        }
        
        // 启动简化的健康检查
        function startSmartHealthCheck() {
            console.log('启动简化的健康检查系统...');
            
            // 立即执行一次健康检查
            updateClusterStatus();
            
            // 启动健康检查（60秒一次）
            healthCheckInterval = setInterval(updateClusterStatus, baseCheckInterval);
            
            console.log(`健康检查间隔: ${baseCheckInterval/1000}秒`);
        }
        
        // 停止健康检查
        function stopHealthCheck() {
            if (healthCheckInterval) {
                clearInterval(healthCheckInterval);
                healthCheckInterval = null;
            }
        }

        function renderNodeDetails(nodes) {
            if (!nodes) return;
            nodeDetails.innerHTML = nodes.map(node => {
                const statusClass = node.status;
                const isCurrent = node.is_current ? ' (当前)' : '';
                return `<div class="node-detail-item"><span class="indicator ${statusClass}"></span><strong>${node.node_id}${isCurrent}</strong><br><small>状态: ${statusClass}, 响应: ${node.response_time}s</small></div>`;
            }).join('');
        }

        // --- 高级验证码语音修复方案 ---
        function fixSpeechForCode(code) {
            if (!code) return code;
            
            // 方案1: 纯数字验证码 - 使用逐字符分离 + 特殊停顿
            if (/^\d+$/.test(code)) {
                // 方法A: 使用零宽空格分隔每个数字，阻止连续识别为数值
                return code.split('').join('\u200B');
            }
            
            // 方案2: 混合字符(字母+数字) - 只在数字间添加分隔符
            if (/[a-zA-Z]/.test(code) && /\d/.test(code)) {
                return code.replace(/(\d)(?=[a-zA-Z\d])/g, '$1\u200B');
            }
            
            // 方案3: 连续数字序列 - 在数字序列内部分离
            return code.replace(/(\d{2,})/g, function(match) {
                return match.split('').join('\u200B');
            });
        }
        
        // --- 备用修复方案 ---
        function alternativeFixSpeech(code) {
            if (!code) return code;
            
            // 方法B: 使用中文数字（备用方案）
            const chineseNumbers = {
                '0': '零', '1': '一', '2': '二', '3': '三', '4': '四',
                '5': '五', '6': '六', '7': '七', '8': '八', '9': '九'
            };
            
            // 如果是纯数字，转换为中文数字
            if (/^\d+$/.test(code)) {
                return code.split('').map(d => chineseNumbers[d]).join('');
            }
            
            // 混合内容只转换数字部分
            return code.replace(/\d/g, d => chineseNumbers[d] || d);
        }

        // 使用 setTimeout 将语音播报异步化，减少主线程阻塞
        function speakCode(text, force = false, onEndCallback = null) {
            if (!force && (!isSpeechEnabled || !('speechSynthesis' in window))) {
                if (onEndCallback) onEndCallback();
                return;
            }
            
            // 关键：使用 setTimeout 异步化语音播报
            setTimeout(() => {
                window.speechSynthesis.cancel();
                
                let speechText = fixSpeechForCode(text);
                const utterance = new SpeechSynthesisUtterance(speechText);
                utterance.lang = 'zh-CN';
                utterance.rate = parseFloat(speechRateSlider.value);
                
                utterance.onstart = () => { readingStatus.style.display = 'block'; };
                utterance.onend = () => { 
                    readingStatus.style.display = 'none';
                    if (onEndCallback) setTimeout(onEndCallback, 0); // 也异步化回调
                };
                
                utterance.onerror = (event) => {
                    console.error('语音播报错误:', event.error);
                    readingStatus.style.display = 'none';
                    if (onEndCallback) setTimeout(onEndCallback, 0);
                };
                
                window.speechSynthesis.speak(utterance);
            }, 0);
        }

        // --- Fullscreen Logic ---
        function initFullscreen() {
            const fullscreenButton = document.createElement('button');
            fullscreenButton.textContent = '全屏';
            Object.assign(fullscreenButton.style, { position: 'fixed', top: '10px', left: '50%', transform: 'translateX(-50%)', zIndex: '25' });
            document.body.appendChild(fullscreenButton);
            fullscreenButton.addEventListener('click', () => {
                if (!document.fullscreenElement) document.documentElement.requestFullscreen();
                else if (document.exitFullscreen) document.exitFullscreen();
            });
            document.addEventListener('fullscreenchange', () => {
                fullscreenButton.textContent = document.fullscreenElement ? '退出全屏' : '全屏';
            });
        }

        // --- 紧急系统重置函数 ---
        function forceSystemReset() {
            console.warn("执行紧急系统重置...");

            try {
                // 强制重置所有状态
                codeQueue = [];
                isDisplaying = false;
                isPolling = false;
                currentDisplayingCode = null;
                consecutivePollFailures = 0;
                connectionState = 'unknown';

                // 清除所有定时器
                if (currentDisplayTimer) clearTimeout(currentDisplayTimer);
                if (countdownInterval) clearInterval(countdownInterval);
                if (pollingInterval) clearInterval(pollingInterval);
                if (screensaverInterval) clearInterval(screensaverInterval);
                if (healthCheckInterval) clearInterval(healthCheckInterval);

                // 取消所有语音
                if (window.speechSynthesis) {
                    window.speechSynthesis.cancel();
                }

                // 隐藏所有显示元素
                if (codeDisplay) {
                    codeDisplay.style.display = 'none';
                    codeDisplay.style.visibility = 'hidden';
                }
                if (countdownTimer) {
                    countdownTimer.style.display = 'none';
                }
                if (document.getElementById('screensaver')) {
                    document.getElementById('screensaver').style.display = 'none';
                }

                // 更新UI
                updateQueueCounter();

                // 重启轮询
                if (startPolling) {
                    setTimeout(async () => {
                        try {
                            await startPolling();
                        } catch (e) {
                            console.error("重启轮询失败:", e);
                        }
                    }, 1000);
                }

                console.log("系统已强制重置完成");
                return true;

            } catch (error) {
                console.error("系统重置过程中出错:", error);
                return false;
            }
        }

        // --- Event Listeners ---
        displayTimeSlider.addEventListener('input', (e) => { displayTimeValue.textContent = e.target.value; });
        speechRateSlider.addEventListener('input', (e) => { speechRateValue.textContent = e.target.value; });
        fontSizeSlider.addEventListener('input', (e) => { 
            fontSizeValue.textContent = e.target.value;
            codeDisplay.style.fontSize = e.target.value + 'vw';
        });
        colorButtons.forEach(button => {
            button.addEventListener('click', () => {
                colorButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                codeDisplay.style.color = button.dataset.color;
                // 同时更新屏保背景
                updateScreensaverBackground(button.dataset.color);
            });
        });
        skipButton.addEventListener('click', hideCode);
        clearQueueButton.addEventListener('click', clearQueue);
        activateAudioButton.addEventListener('click', () => {
            if (isSpeechEnabled) {
                isSpeechEnabled = false;
                activateAudioButton.textContent = '启用语音';
                activateAudioButton.style.backgroundColor = '#007bff';
                speakCode('语音功能已禁用', true);
            } else {
                isSpeechEnabled = true;
                activateAudioButton.textContent = '语音已启用';
                activateAudioButton.style.backgroundColor = '#28a745';
                speakCode('语音功能已启用');
            }
        });
        nodeStatus.addEventListener('click', () => {
            nodeDetailsVisible = !nodeDetailsVisible;
            nodeDetails.style.display = nodeDetailsVisible ? 'block' : 'none';
        });
        document.getElementById('whiteboard').addEventListener('click', () => {
            controls.style.display = controls.style.display === 'none' ? 'block' : 'none';
        });

        // 在屏保模式下也需要支持点击切换控制栏显示/隐藏
        document.getElementById('screensaver').addEventListener('click', () => {
            controls.style.display = controls.style.display === 'none' ? 'block' : 'none';
        });

        // --- 屏保功能 ---
        function updateScreensaver() {
            const now = new Date();

            // 格式化时间显示 (HH:MM:SS)
            const timeString = now.toTimeString().slice(0, 8);

            // 格式化日期显示 (YYYY年MM月DD日 星期X)
            const year = now.getFullYear();
            const month = now.getMonth() + 1;
            const date = now.getDate();
            const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
            const day = weekdays[now.getDay()];

            const dateString = `${year}年${month}月${date}日 星期${day}`;

            // 更新显示
            document.getElementById('timeDisplay').textContent = timeString;
            document.getElementById('dateDisplay').textContent = dateString;

            // 获取天气信息（每30分钟更新一次）
            if (now.getMinutes() % 30 === 0 && now.getSeconds() === 0) {
                fetchWeather();
            }
        }

        function showScreensaver() {
            if (isScreensaverActive) return;

            isScreensaverActive = true;
            document.getElementById('whiteboard').style.display = 'none';
            document.getElementById('screensaver').style.display = 'flex';
            // 在屏保模式下保持控制栏的显示状态逻辑
            // 不再强制隐藏控制栏，让它保持原有的显示状态

            // 立即更新一次时间显示和天气信息
            updateScreensaver();
            fetchWeather();

            // 每秒更新时间显示
            screensaverInterval = setInterval(updateScreensaver, 1000);
        }

        function hideScreensaver() {
            if (!isScreensaverActive) return;

            isScreensaverActive = false;
            document.getElementById('screensaver').style.display = 'none';
            document.getElementById('whiteboard').style.display = 'flex';
            // 不再强制显示控制栏，让它保持原有的显示状态

            // 清除时间更新定时器
            if (screensaverInterval) {
                clearInterval(screensaverInterval);
                screensaverInterval = null;
            }
        }

        // 检查是否应该显示屏保
        function checkScreensaver() {
            // 如果正在显示消息或队列中有消息，则不显示屏保
            if (isDisplaying || codeQueue.length > 0) {
                hideScreensaver();
                return;
            }

            // 如果没有消息且队列为空，则显示屏保
            showScreensaver();
        }

        // 根据字体颜色更新屏保背景
        function updateScreensaverBackground(color) {
            const screensaver = document.getElementById('screensaver');
            let gradient;

            // 根据选择的颜色创建相应的渐变背景，优化亮色主题
            switch(color) {
                case '#000000': // 黑色
                    gradient = 'linear-gradient(135deg, #1a1a1a, #000000, #1a1a1a)';
                    break;
                case '#FF0000': // 红色 - 优化：降低亮度，增加深色层次
                    gradient = 'linear-gradient(135deg, #4a0000, #8b0000, #4a0000)';
                    break;
                case '#0000FF': // 蓝色 - 优化：降低亮度，增加深色层次
                    gradient = 'linear-gradient(135deg, #00004a, #00008b, #00004a)';
                    break;
                case '#00FF00': // 绿色 - 优化：降低亮度，增加深色层次
                    gradient = 'linear-gradient(135deg, #004a00, #008b00, #004a00)';
                    break;
                case '#FFFF00': // 黄色 - 优化：降低亮度，增加深色层次
                    gradient = 'linear-gradient(135deg, #4a4a00, #8b8b00, #4a4a00)';
                    break;
                case '#FF00FF': // 紫色 - 优化：降低亮度，增加深色层次
                    gradient = 'linear-gradient(135deg, #4a004a, #8b008b, #4a004a)';
                    break;
                case '#00FFFF': // 青色 - 优化：降低亮度，增加深色层次
                    gradient = 'linear-gradient(135deg, #004a4a, #008b8b, #004a4a)';
                    break;
                case '#FFA500': // 橙色 - 优化：降低亮度，增加深色层次
                    gradient = 'linear-gradient(135deg, #8b4500, #cc6600, #8b4500)';
                    break;
                case '#800080': // 深紫色 - 保持原样，已经舒适
                    gradient = 'linear-gradient(135deg, #400040, #800080, #400040)';
                    break;
                case '#FFC0CB': // 粉色 - 保持原样，已经舒适
                    gradient = 'linear-gradient(135deg, #ff69b4, #ffc0cb, #ff69b4)';
                    break;
                case '#A52A2A': // 棕色 - 保持原样，已经舒适
                    gradient = 'linear-gradient(135deg, #521515, #a52a2a, #521515)';
                    break;
                case '#808080': // 灰色 - 保持原样，已经舒适
                    gradient = 'linear-gradient(135deg, #404040, #808080, #404040)';
                    break;
                default:
                    gradient = 'linear-gradient(135deg, #1a2a6c, #b21f1f, #1a2a6c)'; // 默认渐变
            }

            screensaver.style.background = gradient;
        }

        // 获取天气信息
        async function fetchWeather() {
            const apiKey = 'f61ff822b07a8a5499a27cc227c13d33'; // 高德天气API密钥
            const city = '上海'; // 城市名
            const adcode = '310113'; // 上海市宝山区的adcode
            const weatherUrl = `https://restapi.amap.com/v3/weather/weatherInfo?city=${adcode}&key=${apiKey}&extensions=all`;

            try {
                const response = await fetch(weatherUrl);
                const data = await response.json();

                // 调试信息：查看API返回的数据结构
                console.log('天气API返回数据:', data);

                if (data.status === '1' && data.forecasts && data.forecasts.length > 0) {
                    const forecasts = data.forecasts[0].casts;

                    // 今天天气
                    if (forecasts.length > 0) {
                        const today = forecasts[0];
                        const todayWeather = document.getElementById('todayWeather');
                        // 更新天气信息，保持HTML结构
                        todayWeather.innerHTML = `
                            <div style="font-size: 1em;">上海市宝山区 今日天气:</div>
                            <div style="font-size: 1.5em; margin-top: 5px;">${today.dayweather}</div>
                            <div style="font-size: 1.5em;">${today.nighttemp}°C ~ ${today.daytemp}°C</div>
                        `;
                    }

                    // 明天天气预报
                    if (forecasts.length > 1) {
                        const tomorrow = forecasts[1];
                        const tomorrowWeather = document.getElementById('tomorrowWeather');
                        // 更新天气信息，保持HTML结构
                        tomorrowWeather.innerHTML = `
                            <div style="font-size: 1em;">上海市宝山区 明日预报:</div>
                            <div style="font-size: 1.5em; margin-top: 5px;">${tomorrow.dayweather}</div>
                            <div style="font-size: 1.5em;">${tomorrow.nighttemp}°C ~ ${tomorrow.daytemp}°C</div>
                        `;
                    }
                } else {
                    console.error('天气数据获取失败:', data);
                    document.getElementById('todayWeather').innerHTML = `
                        <div style="font-size: 1em;">上海市宝山区 今日天气:</div>
                        <div style="font-size: 1.5em; margin-top: 5px;">获取失败</div>
                        <div style="font-size: 1.5em;">--°C ~ --°C</div>
                    `;
                    document.getElementById('tomorrowWeather').innerHTML = `
                        <div style="font-size: 1em;">上海市宝山区 明日预报:</div>
                        <div style="font-size: 1.5em; margin-top: 5px;">获取失败</div>
                        <div style="font-size: 1.5em;">--°C ~ --°C</div>
                    `;
                }
            } catch (error) {
                console.error('获取天气信息出错:', error);
                document.getElementById('todayWeather').innerHTML = `
                    <div style="font-size: 1em;">上海市宝山区 今日天气:</div>
                    <div style="font-size: 1.5em; margin-top: 5px;">获取失败</div>
                    <div style="font-size: 1.5em;">--°C ~ --°C</div>
                `;
                document.getElementById('tomorrowWeather').innerHTML = `
                    <div style="font-size: 1em;">上海市宝山区 明日预报:</div>
                    <div style="font-size: 1.5em; margin-top: 5px;">获取失败</div>
                    <div style="font-size: 1.5em;">--°C ~ --°C</div>
                `;
            }
        }

        // --- Initialization ---
        document.addEventListener('DOMContentLoaded', async () => {
            console.log('轮询版本界面初始化...');

            // 启动屏保检查机制
            setInterval(checkScreensaver, 5000); // 每5秒检查一次是否应该显示屏保

            // 初始化屏保背景与当前选中的字体颜色一致
            const activeColorButton = document.querySelector('.color-btn.active');
            if (activeColorButton) {
                updateScreensaverBackground(activeColorButton.dataset.color);
            }

            // 启动连接状态监控
            setInterval(() => {
                const now = Date.now();
                const timeSinceLastPoll = now - lastPollTime;

                // 如果超过60秒没有成功轮询，标记为停滞
                if (lastPollTime > 0 && timeSinceLastPoll > 60000) {
                    updateConnectionState('stale');
                }
            }, 30000); // 每30秒检查一次

            // 启动系统健康检查 - 防止系统卡住。实际上却成为了bug的来源！
            setInterval(() => {
/* Bug的来源！
                const now = Date.now();
                // 如果系统显示状态异常超过30秒，强制重置
                if (isDisplaying && codeQueue.length > 0) {
                    // 检查是否卡住
                    if (typeof lastDisplayStartTime === 'undefined') {
                        lastDisplayStartTime = now;
                    } else if (now - lastDisplayStartTime > 30000) {
                        console.warn("检测到系统可能卡住，执行自动恢复...");
                        forceSystemReset();
                    }
                }
*/ 

                // 如果队列中有消息但未显示，尝试处理
                if (!isDisplaying && codeQueue.length > 0) {
                    console.log("检测到未处理的队列消息，尝试处理...");
                    processCodeQueue();
                }
            }, 10000); // 每10秒检查一次

            // 延迟启动轮询，确保页面完全加载
            setTimeout(async () => {
                try {
                    await fetch('events.php')
                        .then(response => response.json())
                        .then(data => console.log('轮询系统测试:', data))
                        .catch(error => console.error('轮询系统测试错误:', error));

                    initFullscreen();
                    await startPolling();
                    startSmartHealthCheck(); // 使用智能健康检查
                } catch (error) {
                    console.error('启动轮询系统失败:', error);
                }
            }, 1000); // 延迟1秒启动
        });
    </script>
</body>
</html>