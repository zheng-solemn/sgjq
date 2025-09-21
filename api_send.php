<?php
// api_send.php - 标准消息API接口
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET');
header('Access-Control-Allow-Headers: Content-Type, X-Requested-With');

try {
    
    // 接受GET或POST请求
    $method = $_SERVER['REQUEST_METHOD'];
    $input = [];
    
    if ($method === 'POST') {
        $rawInput = file_get_contents('php://input');
        if (!empty($rawInput)) {
            // 优先尝试JSON格式
            $jsonData = json_decode($rawInput, true);
            if (json_last_error() === JSON_ERROR_NONE) {
                $input = $jsonData;
            } else {
                // 回退到表单数据
                $input = $_POST;
            }
        } else {
            $input = $_POST;
        }
    } else {
        $input = $_GET;
    }
    
    // 必要参数检查
    if (!isset($input['code']) || trim($input['code']) === '') {
        echo json_encode(['success' => false, 'error' => 'code参数不能为空'], JSON_UNESCAPED_UNICODE);
        exit;
    }
    
    $message = trim($input['code']);
    
    // 直接发送到本地check.php处理
    $localData = [
        'code' => $message,
        'timestamp' => time(),
        'source_node_id' => 'api_send'
    ];
    
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => 'https://zzsolo.fly.dev/check.php',
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($localData, JSON_UNESCAPED_UNICODE),
        CURLOPT_HTTPHEADER => ['Content-Type: application/json; charset=utf-8'],
        CURLOPT_TIMEOUT => 15,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_SSL_VERIFYPEER => false
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode == 200) {
        $data = json_decode($response, true);
        if (json_last_error() === JSON_ERROR_NONE) {
            echo json_encode([
                'success' => true,
                'message' => '消息已成功发送',
                'result' => $data,
                'timestamp' => time()
            ], JSON_UNESCAPED_UNICODE);
        } else {
            echo json_encode(['success' => true, 'message' => '消息发送成功，但响应解析错误'], JSON_UNESCAPED_UNICODE);
        }
    } else {
        echo json_encode(['success' => false, 'error' => "消息发送失败，HTTP状态码: $httpCode"], JSON_UNESCAPED_UNICODE);
    }
    
} catch (Exception $e) {
    echo json_encode(['success' => false, 'error' => '系统错误: ' . $e->getMessage()], JSON_UNESCAPED_UNICODE);
}
?>