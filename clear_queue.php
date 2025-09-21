<?php
// clear_queue.php - 清空消息队列API (更新为使用messages.json)
header("Access-Control-Allow-Origin: *");
header('Content-Type: application/json');

// 关闭错误显示
ini_set('display_errors', 0);
error_reporting(0);

// 消息文件
$messages_file = 'messages.json';

try {
    $success = true;
    $errors = [];
    
    // 清空 messages.json (重置为空状态)
    $empty_data = [
        'messages' => [],
        'last_id' => 0,
        'created' => date('Y-m-d\TH:i:s\Z'),
        'version' => '1.0'
    ];
    
    $result = file_put_contents($messages_file, json_encode($empty_data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    if ($result === false) {
        $success = false;
        $errors[] = '无法清空 messages.json';
    }
    
    if ($success) {
        echo json_encode(array(
            'success' => true,
            'message' => '消息队列已清空'
        ));
    } else {
        echo json_encode(array(
            'success' => false,
            'error' => implode(', ', $errors)
        ));
    }
} catch (Exception $e) {
    echo json_encode(array(
        'success' => false,
        'error' => '清空消息队列时发生错误: ' . $e->getMessage()
    ));
}
?>