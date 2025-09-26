#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SFTP文件管理器
用于连接到服务器并执行文件操作（上传、下载、删除、列出文件等）
"""

import paramiko
import os
import sys
import argparse
from datetime import datetime

# 服务器连接凭据（从CLAUDE.md中获取）
SFTP_CONFIG = {
    'server': '2a09:8280:1::92:6611:0',
    'port': 22,
    'username': 'root',
    'password': 'Solemn520!',
    'root_dir': '/wwwroot/'
}

def connect_sftp():
    """
    连接到SFTP服务器
    返回: (ssh_client, sftp_client)
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=SFTP_CONFIG['server'],
            port=SFTP_CONFIG['port'],
            username=SFTP_CONFIG['username'],
            password=SFTP_CONFIG['password'],
            timeout=30
        )

        sftp = ssh.open_sftp()
        print("[OK] SFTP连接成功!")
        return ssh, sftp
    except Exception as e:
        print(f"[错误] SFTP连接失败: {str(e)}")
        return None, None

def upload_file(local_path, remote_filename=None):
    """
    上传文件到服务器
    参数:
        local_path: 本地文件路径
        remote_filename: 远程文件名（可选，默认使用本地文件名）
    """
    ssh, sftp = connect_sftp()
    if not sftp:
        return False

    try:
        if not remote_filename:
            remote_filename = os.path.basename(local_path)

        remote_path = f"{SFTP_CONFIG['root_dir']}{remote_filename}"
        sftp.put(local_path, remote_path)
        print(f"[成功] 文件已上传到 {remote_path}")
        return True
    except Exception as e:
        print(f"[错误] 文件上传失败: {str(e)}")
        return False
    finally:
        sftp.close()
        ssh.close()

def download_file(remote_filename, local_path=None):
    """
    从服务器下载文件
    参数:
        remote_filename: 远程文件名
        local_path: 本地保存路径（可选，默认使用远程文件名）
    """
    ssh, sftp = connect_sftp()
    if not sftp:
        return False

    try:
        if not local_path:
            local_path = remote_filename

        remote_path = f"{SFTP_CONFIG['root_dir']}{remote_filename}"
        sftp.get(remote_path, local_path)
        print(f"[成功] 文件已下载到 {local_path}")
        return True
    except Exception as e:
        print(f"[错误] 文件下载失败: {str(e)}")
        return False
    finally:
        sftp.close()
        ssh.close()

def delete_file(remote_filename):
    """
    删除服务器上的文件
    参数:
        remote_filename: 远程文件名
    """
    ssh, sftp = connect_sftp()
    if not sftp:
        return False

    try:
        remote_path = f"{SFTP_CONFIG['root_dir']}{remote_filename}"
        sftp.remove(remote_path)
        print(f"[成功] 文件已删除 {remote_path}")
        return True
    except Exception as e:
        print(f"[错误] 文件删除失败: {str(e)}")
        return False
    finally:
        sftp.close()
        ssh.close()

def list_files():
    """
    列出服务器根目录下的文件
    """
    ssh, sftp = connect_sftp()
    if not sftp:
        return False

    try:
        items = sftp.listdir_attr(SFTP_CONFIG['root_dir'])
        print(f"[信息] 服务器目录 {SFTP_CONFIG['root_dir']} 中的文件:")
        for item in items:
            timestamp = datetime.fromtimestamp(item.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  {item.filename:<30} {item.st_size:>10} bytes  {timestamp}")
        return True
    except Exception as e:
        print(f"[错误] 列出文件失败: {str(e)}")
        return False
    finally:
        sftp.close()
        ssh.close()

def backup_file(remote_filename):
    """
    备份服务器上的文件
    参数:
        remote_filename: 远程文件名
    """
    ssh, sftp = connect_sftp()
    if not sftp:
        return False

    try:
        # 检查文件是否存在
        remote_path = f"{SFTP_CONFIG['root_dir']}{remote_filename}"
        sftp.stat(remote_path)  # 如果文件不存在会抛出异常

        # 创建备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{remote_filename}.backup_{timestamp}"
        backup_path = f"{SFTP_CONFIG['root_dir']}{backup_filename}"

        # 复制文件（先下载再上传）
        temp_local = f"temp_{remote_filename}"
        sftp.get(remote_path, temp_local)
        sftp.put(temp_local, backup_path)
        os.remove(temp_local)  # 删除临时本地文件

        print(f"[成功] 文件已备份为 {backup_path}")
        return True
    except FileNotFoundError:
        print(f"[错误] 文件不存在: {remote_path}")
        return False
    except Exception as e:
        print(f"[错误] 文件备份失败: {str(e)}")
        # 清理可能创建的临时文件
        if os.path.exists(f"temp_{remote_filename}"):
            os.remove(f"temp_{remote_filename}")
        return False
    finally:
        sftp.close()
        ssh.close()

def main():
    """
    主函数，处理命令行参数
    """
    parser = argparse.ArgumentParser(description='SFTP文件管理器')
    parser.add_argument('action', choices=['upload', 'download', 'delete', 'list', 'backup'],
                       help='操作类型: upload(上传), download(下载), delete(删除), list(列出), backup(备份)')
    parser.add_argument('--local', '-l', help='本地文件路径')
    parser.add_argument('--remote', '-r', help='远程文件名')

    args = parser.parse_args()

    if args.action == 'upload':
        if not args.local:
            print("[错误] 上传操作需要指定本地文件路径 (--local)")
            return False
        return upload_file(args.local, args.remote)

    elif args.action == 'download':
        if not args.remote:
            print("[错误] 下载操作需要指定远程文件名 (--remote)")
            return False
        return download_file(args.remote, args.local)

    elif args.action == 'delete':
        if not args.remote:
            print("[错误] 删除操作需要指定远程文件名 (--remote)")
            return False
        return delete_file(args.remote)

    elif args.action == 'list':
        return list_files()

    elif args.action == 'backup':
        if not args.remote:
            print("[错误] 备份操作需要指定远程文件名 (--remote)")
            return False
        return backup_file(args.remote)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)