<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>发送Code测试</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
        }
        input[type="text"] {
            width: 100%;
            padding: 8px;
            font-size: 16px;
        }
        button {
            padding: 10px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .method-selector {
            margin-bottom: 15px;
        }
        .result-item {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #ccc;
        }
        .result-item.success {
            background-color: #d4edda;
            border-left-color: #28a745;
        }
        .result-item.error {
            background-color: #f8d7da;
            border-left-color: #dc3545;
        }
        .result-item small {
            color: #666;
            font-size: 12px;
        }
        .node-info {
            margin-top: 10px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <h1>发送Code测试</h1>
    
    <div id="nodeInfo" class="node-info">
        正在加载节点信息...
    </div>
    
    <div class="method-selector">
        <label>
            <input type="radio" name="method" value="get" checked> GET
        </label>
        <label>
            <input type="radio" name="method" value="post"> POST
        </label>
    </div>
    
    <div class="form-group">
        <label for="codeInput">输入要发送的Code:</label>
        <input type="text" id="codeInput" placeholder="例如: A123">
    </div>
    
    <button id="sendButton">发送</button>
    
    <div id="result" style="margin-top: 20px;"></div>
    
    <script>
        // 获取所有节点列表（硬编码版本）
        async function getAllNodes() {
            // 硬编码节点配置，两个节点互为备份
            const hardcodedNodes = {
                'zzsolo': 'https://zzsolo.fly.dev',
                'mnizz': 'https://mnizz.fly.dev'
            };
            return hardcodedNodes;
        }

        // 页面加载时显示节点信息
        async function loadNodeInfo() {
            const nodeInfoDiv = document.getElementById('nodeInfo');
            try {
                const nodes = await getAllNodes();
                const nodeCount = Object.keys(nodes).length;
                const localNode = window.location.hostname;
                
                let html = `<strong>节点信息:</strong> 本地节点 (${localNode}) + ${nodeCount} 个远程节点<br>`;
                html += '<strong>远程节点:</strong> ';
                
                if (nodeCount > 0) {
                    const nodeNames = Object.keys(nodes).join(', ');
                    html += nodeNames;
                } else {
                    html += '无';
                }
                
                nodeInfoDiv.innerHTML = html;
            } catch (error) {
                nodeInfoDiv.innerHTML = '<strong>节点信息:</strong> 加载失败';
            }
        }

        // 页面加载时执行
        window.addEventListener('load', loadNodeInfo);

        document.getElementById('sendButton').addEventListener('click', async function() {
            const sendButton = this;
            const code = document.getElementById('codeInput').value.trim();
            if (!code) {
                alert('请输入Code');
                return;
            }
            
            // 禁用按钮并显示发送状态
            sendButton.disabled = true;
            sendButton.textContent = '发送中...';
            sendButton.style.backgroundColor = '#cccccc';
            
            const method = document.querySelector('input[name="method"]:checked').value;
            const resultDiv = document.getElementById('result');
            
            // 获取所有节点
            try {
                const nodes = await getAllNodes();
                const results = [];
                
                // 发送到本地节点
                results.push(sendToNode('本地', './check.php', code, method));
                
                // 发送到远程节点
                for (const [nodeName, nodeUrl] of Object.entries(nodes)) {
                    results.push(sendToNode(nodeName, `${nodeUrl}/check.php`, code, method));
                }
                
                // 等待所有请求完成
                try {
                    const allResults = await Promise.allSettled(results);
                    displayResults(allResults, resultDiv);
                } catch (error) {
                    resultDiv.innerHTML = `<p>发送过程中出现错误: ${error.message}</p>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<p>获取节点信息失败: ${error.message}</p>`;
            } finally {
                // 恢复按钮状态
                sendButton.disabled = false;
                sendButton.textContent = '发送';
                sendButton.style.backgroundColor = '#4CAF50';
            }
        });

        async function sendToNode(nodeName, url, code, method) {
            try {
                let response;
                if (method === 'get') {
                    response = await fetch(`${url}?code=${encodeURIComponent(code)}`);
                } else {
                    const formData = new FormData();
                    formData.append('code', code);
                    response = await fetch(url, {
                        method: 'POST',
                        body: formData
                    });
                }
                
                const data = await response.json();
                return {
                    node: nodeName,
                    success: response.ok,
                    status: response.status,
                    data: data
                };
            } catch (error) {
                return {
                    node: nodeName,
                    success: false,
                    error: error.message
                };
            }
        }

        // 通过协调器广播消息（已禁用）
        // async function sendViaCoordinator(nodeName, code, method, expectedNodeCount) {
        //     try {
        //         // coordinator/submit.php需要JSON格式
        //         const messageData = {
        //             code: code,
        //             timestamp: Math.floor(Date.now() / 1000),
        //             source_node_id: 'zzsolo-whiteboard'
        //         };
        //         
        //         const response = await fetch('./coordinator/submit.php', {
        //             method: 'POST',
        //             headers: {
        //                 'Content-Type': 'application/json',
        //             },
        //             body: JSON.stringify(messageData)
        //         });
        //         
        //         const data = await response.json();
        //         return {
        //             node: `${nodeName} (预期${expectedNodeCount}个节点)`,
        //             success: response.ok,
        //             status: response.status,
        //             data: data
        //         };
        //     } catch (error) {
        //         return {
        //             node: `${nodeName} (预期${expectedNodeCount}个节点)`,
        //             success: false,
        //             error: error.message
        //         };
        //     }
        // }

        function displayResults(results, resultDiv) {
            let html = '<h3>发送结果:</h3>';
            
            results.forEach((result, index) => {
                if (result.status === 'fulfilled') {
                    const nodeResult = result.value;
                    const statusClass = nodeResult.success ? 'success' : 'error';
                    const statusText = nodeResult.success ? '? 成功' : '? 失败';
                    
                    html += `<div class="result-item ${statusClass}">`;
                    html += `<strong>${nodeResult.node}:</strong> ${statusText}`;
                    html += `<br><small>状态: ${nodeResult.status || 'N/A'}</small>`;
                    
                    if (nodeResult.data) {
                        html += `<br><small>响应: ${JSON.stringify(nodeResult.data)}</small>`;
                    }
                    
                    if (nodeResult.error) {
                        html += `<br><small>错误: ${nodeResult.error}</small>`;
                    }
                    
                    html += '</div>';
                } else {
                    html += `<div class="result-item error">`;
                    html += `<strong>节点 ${index + 1}:</strong> ? 请求失败`;
                    html += `<br><small>错误: ${result.reason.message}</small>`;
                    html += '</div>';
                }
            });
            
            resultDiv.innerHTML = html;
        }
    </script>
</body>
</html>
