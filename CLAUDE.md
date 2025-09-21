# CLAUDE.md - 工作指导（优化版）

## 🖥️ 系统环境信息 - 最高优先级
═══════════════════════════════════
**操作系统**：Windows 11/10
**终端环境**：PowerShell / Command Prompt
**路径分隔符**：反斜杠 (\)
**命令优先级**：Windows > Linux/Mac

### Windows 强制规则：
- 目录操作：使用 `cd` + 反斜杠路径
- 文件列表：使用 `dir` 而非 `ls`
- 文件删除：使用 `del` 或 `Remove-Item`（失败则切换）
- 路径检查：使用 `if exist` 而非 `[ -d ]`
- 环境变量：使用 `%VARIABLE%` 而非 `$VARIABLE`
- 脚本执行：优先 `.bat` / `.ps1` 而非 `.sh`

### 禁止行为：
- ❌ 使用 Linux 路径格式（/path/to/file）
- ❌ 使用 sudo、chmod、chown 等 Linux 命令
- ❌ 假设存在 Linux 工具链

## ⚠️ 核心约束 - 违反=任务失败
═══════════════════════════════════
1. **必须使用中文回复**
2. **强制 Windows 环境**：所有命令和路径必须符合 Windows 标准
3. **强制任务状态重置**：每次新指令必须清空之前任务状态
4. **强制执行失败限制**：超过限制立即停止并报告
5. **强制任务完成验证**：任务完成后必须自动进行全面验证
6. **强制清理临时文件**：任务结束必须清理所有测试和临时文件
7. **🚨 绝对禁止随意删除代码**：严格遵守代码保护协议

## 🔒 代码保护协议 - 最高优先级
═══════════════════════════════════

### 删除代码红线
**绝对禁止**：
- ❌ 删除超过5行的连续代码
- ❌ 删除任何函数、类、方法的完整定义
- ❌ 删除任何配置块、数组定义、数据结构
- ❌ 为了"简化"或"重构"而删除现有功能

**允许操作**：
- ✅ 修改1-5行的具体错误代码
- ✅ 添加新的代码行
- ✅ 修改变量名、参数值
- ✅ 修复语法错误、逻辑错误

### 代码修改前强制检查清单
```
[ ] 已下载并分析完整的原文件
[ ] 已理解文件的整体结构和功能
[ ] 已定位到具体的错误位置（精确到行）
[ ] 确认修改范围不超过10行代码
[ ] 确认不会删除任何现有功能
[ ] 已准备好原文件备份
```

### 紧急停止条件
发现以下情况立即停止：
- 🚨 准备删除超过5行代码
- 🚨 准备删除完整函数/类/方法
- 🚨 无法准确定位错误原因
- 🚨 修改会影响多个功能模块

### 备份策略
```python
# 修改任何文件前必须执行
import shutil
from datetime import datetime

def create_backup(original_file):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{original_file}_backup_{timestamp}"
    shutil.copy2(original_file, backup_file)
    print(f"[备份创建] {original_file} → {backup_file}")
    return backup_file
```

## 🔄 任务状态管理
═══════════════════════════════════

### 任务开始协议
1. **状态重置**：清除之前任务的所有上下文
2. **目标确认**：明确本次任务目标
3. **计数器初始化**：失败计数=0/5
4. **代码保护激活**：确认备份策略

### 任务结束协议
1. **自动验证**：无需用户指令，立即验证
2. **代码完整性检查**：确认原有功能完整
3. **清理文件**：删除所有测试和临时文件
4. **状态报告**：报告任务完成情况

## 🛡️ 死循环防护机制
═══════════════════════════════════

### 执行限制
- **总失败次数**：最多5次
- **单工具失败**：最多2次
- **MCP调用**：最多3次
- **相同错误**：重复2次立即停止

### 实时监控要求
每次响应必须包含：
```
[任务状态] 进行中/已完成/已失败
[失败计数] X/5
[当前操作] XXX
[代码保护] 激活/安全
```

### 强制停止触发
- 失败次数达到上限
- 检测到循环模式
- 权限/认证错误（不重试）
- 参数验证失败（不重试）

## 📝 测试文件管理
═══════════════════════════════════

### 命名规范（统一）
- **所有测试文件**：`test_[功能]_[时间戳].[扩展名]`
- **调试文件**：`debug_[功能]_[时间戳].log`
- **临时文件**：`temp_[用途]_[时间戳].[扩展名]`

### 测试文件生命周期
1. **生成阶段**：创建测试文件，明确目的
2. **使用阶段**：执行测试，获取结果
3. **清理阶段**：任务结束必须删除所有测试文件

### Windows 清理命令
```powershell
# PowerShell 清理命令
Remove-Item test_* -Force -ErrorAction SilentlyContinue
Remove-Item temp_* -Force -ErrorAction SilentlyContinue
Remove-Item debug_* -Force -ErrorAction SilentlyContinue
Remove-Item *.tmp -Force -ErrorAction SilentlyContinue
Remove-Item *.temp -Force -ErrorAction SilentlyContinue

# 或使用 CMD 命令
del /F /Q test_* 2>nul
del /F /Q temp_* 2>nul
del /F /Q debug_* 2>nul
del /F /Q *.tmp 2>nul
del /F /Q *.temp 2>nul
```

### 清理验证清单
```
[ ] 列出所有生成的测试文件
[ ] 删除本地所有 test_*
[ ] 删除本地所有 temp_*
[ ] 删除本地所有 debug_*
[ ] 删除服务器所有测试文件
[ ] 验证本地目录干净
[ ] 验证服务器目录干净
```

## 🔧 测试文件模板库
═══════════════════════════════════

### PHP环境信息获取
```php
<?php
// test_phpinfo_[timestamp].php
echo json_encode([
    'php_version' => phpversion(),
    'extensions' => get_loaded_extensions(),
    'memory_limit' => ini_get('memory_limit'),
    'max_execution_time' => ini_get('max_execution_time'),
    'server_info' => $_SERVER,
    'timestamp' => date('Y-m-d H:i:s')
]);
?>
```

### 服务器功能测试
```php
<?php
// test_server_[timestamp].php
$result = [
    'file_operations' => is_writable('./'),
    'curl_available' => function_exists('curl_init'),
    'json_support' => function_exists('json_encode'),
    'current_dir' => getcwd(),
    'permissions' => substr(sprintf('%o', fileperms('./')), -4)
];
echo json_encode($result, JSON_PRETTY_PRINT);
?>
```

## 🌐 SFTP服务器连接信息
═══════════════════════════════════

### 连接凭据
- **服务器地址**: `2a09:8280:1::92:6611:0` (IPv6)
- **端口**: 22
- **用户名**: root
- **密码**: Solemn520!
- **网站根目录**: `/wwwroot/`

### 统一SFTP管理脚本
为避免生成大量临时Python文件，项目使用统一的SFTP管理脚本 `sftp_manager.py` 来执行所有服务器文件操作。

**脚本功能**：
- 连接SFTP服务器
- 上传文件到服务器
- 从服务器下载文件
- 删除服务器上的文件
- 列出服务器目录中的文件
- 备份服务器上的文件

**使用方法**：
```bash
# 上传文件
python sftp_manager.py upload --local local_file.php --remote remote_file.php

# 下载文件
python sftp_manager.py download --remote remote_file.php --local local_file.php

# 删除文件
python sftp_manager.py delete --remote remote_file.php

# 列出文件
python sftp_manager.py list

# 备份文件
python sftp_manager.py backup --remote remote_file.php
```

### Python连接模板
```python
import paramiko

def connect_sftp():
    server = "2a09:8280:1::92:6611:0"
    username = "root"
    password = "Solemn520!"
    port = 22

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=server, port=port, username=username,
                password=password, timeout=30)

    sftp = ssh.open_sftp()
    print("[OK] SFTP连接成功!")
    return ssh, sftp
```

### 文件操作命令
```python
# 上传
sftp.put(local_path, f'/wwwroot/{remote_file}')

# 下载
sftp.get(f'/wwwroot/{remote_file}', local_path)

# 删除
sftp.remove(f'/wwwroot/{remote_file}')

# 列出文件
items = sftp.listdir_attr('/wwwroot')
```

## ✅ 自动验证协议
═══════════════════════════════════

### 验证触发
任务完成后，无需用户指令，必须立即自动执行验证

### 验证检查项
1. **功能验证**：修复的功能是否正常
2. **代码验证**：语法是否正确，逻辑是否合理
3. **完整性验证**：原有功能是否完全保持
4. **服务器验证**：文件上传是否成功（如涉及）

### 验证报告格式
```
[自动验证报告]
├── 验证结果：通过/失败/部分通过
├── 代码完整性：保持/受损
├── 问题发现：XXX（如有）
└── 最终状态：任务成功/需要补充修复
```

## 📊 响应格式要求
═══════════════════════════════════

### 标准响应格式
```
[任务状态] 进行中/已完成/已失败
[失败计数] X/5
[当前操作] XXX
[代码保护] 激活/安全
```

### 失败响应格式
```
[失败报告]
├── 失败原因：XXX
├── 已尝试次数：X/5
├── 代码影响：无/轻微/严重
└── 建议操作：XXX
```

### 代码修改响应格式
```
[代码修改记录]
├── 文件名：XXX
├── 修改类型：修复/添加/优化
├── 修改行数：增加X行，修改X行，删除X行
├── 备份状态：已创建
└── 功能影响：无/需要测试
```

## 📦 GitHub版本控制与自动备份
═══════════════════════════════════

### 仓库初始化
项目已配置为Git仓库，可与GitHub同步进行版本控制和备份。

### 自动备份脚本
使用 `backup.bat` 脚本实现一键自动备份：
```cmd
# 执行自动备份，使用默认提交信息
backup.bat

# 使用自定义提交信息
backup.bat "实现新功能：验证码识别优化"
```

### 手动备份命令
```bash
# 添加所有更改
git add .

# 提交更改
git commit -m "提交信息"

# 推送到GitHub
git push origin main
```

### GitHub配置步骤
1. 在GitHub上创建新仓库
2. 使用以下命令关联本地仓库：
   ```bash
   git remote add origin https://github.com/your-username/your-repo-name.git
   ```
3. 首次推送：
   ```bash
   git push -u origin main
   ```

## 🎯 执行优先级总结
═══════════════════════════════════
1. **代码保护** > 任务完成（宁可失败也不破坏代码）
2. **精确修复** > 大段重写（最小化修改范围）
3. **快速失败** > 无限重试（避免死循环）
4. **自动验证** > 等待确认（主动确保质量）
5. **彻底清理** > 遗留文件（保持环境整洁）

## 💡 核心原则
═══════════════════════════════════
**"精确修复，代码保护，智能重试，优雅失败，自动验证，彻底清理"**

- 收到指令 = 状态重置 + 立即开始
- 遇到困难 = 有限重试，快速失败
- 代码修改 = 严格保护，精确修复
- 任务完成 = 自动验证 + 自动清理
- 死循环检测 = 立即终止，避免浪费

## 📁 系统核心文件列表
═══════════════════════════════════

### 前端显示系统
- **index.php** - 全屏白板消息显示系统主文件，包含前端界面和轮询逻辑

### 后端处理核心
- **check.php** - 消息处理核心文件，包含AI驱动的消息内容分析和过滤机制

### 通信接口层
- **events.php** - 事件系统文件，处理前端轮询请求和消息队列
- **api_send.php** - API接口文件，提供RESTful API供外部系统发送消息
- **send.php** - 管理界面文件，提供可视化消息发送和管理功能

### 辅助功能模块
- **clear_queue.php** - 队列清理功能文件，用于清空消息队列

### 数据文件
- **check_log.txt** - 检查日志文件，记录系统处理日志
- **code_data.txt** - 验证码数据文件，存储提取的验证码信息
- **spamfilter.txt** - 垃圾信息过滤文件，包含垃圾信息过滤规则
- **messages.json** - 消息数据文件，存储待处理的消息队列

### 文档文件
- **CLAUDE.md** - Claude工作指导文件
- **GEMINI.md** - Gemini工作指导文件
- **SYSTEM_ANALYSIS.md** - 系统分析报告文件