<?php
// events.php - 轮询版本的事件系统 (使用messages.json存储)
header("Access-Control-Allow-Origin: *");
header('Content-Type: application/json');

$messages_file = 'messages.json';
$last_id = isset($_GET['last_id']) ? intval($_GET['last_id']) : 0;

// 读取消息存储
function readMessages() {
    global $messages_file;
    if (!file_exists($messages_file)) {
        return ['messages' => [], 'last_id' => 0];
    }
    
    $content = file_get_contents($messages_file);
    $data = json_decode($content, true);
    
    if (!$data || !isset($data['messages'])) {
        return ['messages' => [], 'last_id' => 0];
    }
    
    return $data;
}

// 写入消息存储
function writeMessages($data) {
    global $messages_file;
    return file_put_contents($messages_file, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
}

// 添加新消息
function addMessage($code, $timestamp, $node_id = 'unknown') {
    $data = readMessages();
    
    $newMessage = [
        'code' => $code,
        'hasCode' => is_numeric($code),
        'timestamp' => $timestamp,
        'time' => date('Y-m-d H:i:s', $timestamp),
        'node_id' => $node_id,
        'id' => ++$data['last_id']
    ];
    
    $data['messages'][] = $newMessage;
    
    // 保持最近1000条消息
    if (count($data['messages']) > 1000) {
        $data['messages'] = array_slice($data['messages'], -1000);
    }
    
    writeMessages($data);
    return $newMessage;
}

// 获取新消息
function getNewMessages($last_id) {
    $data = readMessages();
    $newMessages = [];
    
    foreach ($data['messages'] as $message) {
        if ($message['id'] > $last_id) {
            $newMessages[] = $message;
        }
    }
    
    return [
        'messages' => $newMessages,
        'last_id' => $data['last_id']
    ];
}

// 如果是POST请求，添加新消息
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $rawInput = file_get_contents('php://input');
    $input = json_decode($rawInput, true);
    
    if ($input && isset($input['code']) && isset($input['timestamp'])) {
        $node_id = isset($input['node_id']) ? $input['node_id'] : 'unknown';
        $newMessage = addMessage($input['code'], $input['timestamp'], $node_id);
        
        echo json_encode([
            'success' => true,
            'message' => 'Message added',
            'message_id' => $newMessage['id']
        ]);
    } else {
        echo json_encode(['success' => false, 'error' => 'Invalid input']);
    }
    exit;
}

// GET请求：获取新消息
$response = getNewMessages($last_id);

echo json_encode($response);
?>