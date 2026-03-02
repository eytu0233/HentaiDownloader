#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
作者分類整理腳本
將下載目錄中的作品按 [作者名] 分類整理到對應的作者目錄中
"""

import os
import re
import shutil
import logging
import sys
from pathlib import Path
from datetime import datetime


def extract_author_name(dirname):
    """
    從目錄名稱中提取作者名
    格式：[作者名]作品名 -> 作者名

    Args:
        dirname: 目錄名稱

    Returns:
        作者名（不含方括號），如果沒有方括號則返回 None
    """
    # 匹配第一個方括號中的內容
    match = re.match(r'^\[([^\]]+)\]', dirname)
    if match:
        return match.group(1)
    return None


def get_all_subdirs(base_path, depth=1):
    """
    獲取指定路徑下的所有一級子目錄（只搜尋一層）

    Args:
        base_path: 基礎路徑
        depth: 搜尋深度，預設為 1（只搜尋一層）

    Returns:
        子目錄列表（完整路徑）
    """
    subdirs = []
    try:
        # 只搜尋一層，不遞迴
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                subdirs.append(item_path)
    except Exception as e:
        logging.error(f"讀取目錄失敗 {base_path}: {e}")
    return subdirs


def organize_by_author(download_path, dry_run=False):
    """
    按作者名整理下載目錄

    Args:
        download_path: 下載目錄路徑
        dry_run: 是否為測試運行（不實際移動文件）

    Returns:
        統計資訊字典
    """
    stats = {
        'total': 0,          # 總計處理的目錄數
        'organized': 0,      # 成功整理的目錄數
        'skipped': 0,        # 跳過的目錄數（沒有作者名）
        'deleted': 0,        # 刪除的重複目錄數
        'errors': 0          # 錯誤數
    }

    if not os.path.exists(download_path):
        logging.error(f"下載目錄不存在: {download_path}")
        return stats

    logging.info(f"開始整理目錄: {download_path}")
    logging.info(f"測試模式: {dry_run}")

    # 獲取所有子目錄
    subdirs = get_all_subdirs(download_path)
    stats['total'] = len(subdirs)

    logging.info(f"找到 {stats['total']} 個子目錄")

    # 按作者名分組
    author_works = {}  # {作者名: [作品目錄路徑列表]}

    for subdir_path in subdirs:
        dirname = os.path.basename(subdir_path)
        author_name = extract_author_name(dirname)

        if author_name:
            if author_name not in author_works:
                author_works[author_name] = []
            author_works[author_name].append(subdir_path)
            logging.debug(f"找到作品: [{author_name}] - {dirname}")
        else:
            logging.warning(f"跳過沒有作者名的目錄: {dirname}")
            stats['skipped'] += 1

    logging.info(f"找到 {len(author_works)} 位作者的作品")

    # 整理每位作者的作品
    for author_name, work_paths in author_works.items():
        author_dir = os.path.join(download_path, f"[{author_name}]")

        logging.info(f"\n處理作者: [{author_name}] ({len(work_paths)} 個作品)")

        # 創建作者目錄
        if not dry_run:
            try:
                if not os.path.exists(author_dir):
                    os.makedirs(author_dir)
                    logging.info(f"  創建作者目錄: {author_dir}")
            except Exception as e:
                logging.error(f"  創建目錄失敗 {author_dir}: {e}")
                stats['errors'] += 1
                continue
        else:
            logging.info(f"  [測試] 將創建作者目錄: {author_dir}")

        # 移動作品到作者目錄
        for work_path in work_paths:
            work_name = os.path.basename(work_path)
            target_path = os.path.join(author_dir, work_name)

            # 檢查目標位置是否已存在同名目錄
            if os.path.exists(target_path):
                if os.path.samefile(work_path, target_path):
                    # 源和目標是同一個目錄，跳過
                    logging.debug(f"  跳過（已在目標位置）: {work_name}")
                    continue
                else:
                    # 存在重複，刪除源目錄
                    logging.warning(f"  發現重複目錄，將刪除: {work_path}")
                    if not dry_run:
                        try:
                            shutil.rmtree(work_path)
                            logging.info(f"  已刪除重複目錄: {work_name}")
                            stats['deleted'] += 1
                        except Exception as e:
                            logging.error(f"  刪除失敗 {work_path}: {e}")
                            stats['errors'] += 1
                    else:
                        logging.info(f"  [測試] 將刪除重複目錄: {work_path}")
                        stats['deleted'] += 1
            else:
                # 移動目錄
                if not dry_run:
                    try:
                        shutil.move(work_path, target_path)
                        logging.info(f"  移動: {work_name}")
                        stats['organized'] += 1
                    except Exception as e:
                        logging.error(f"  移動失敗 {work_path} -> {target_path}: {e}")
                        stats['errors'] += 1
                else:
                    logging.info(f"  [測試] 將移動: {work_name} -> {author_dir}")
                    stats['organized'] += 1

    return stats


def merge_author_directories(source_path, target_path, dry_run=False):
    """
    合併兩個目錄中的作者分類
    將源目錄中的 [作者名] 目錄下的漫畫移動到目標目錄對應的 [作者名] 目錄

    Args:
        source_path: 源目錄路徑
        target_path: 目標目錄路徑
        dry_run: 是否為測試運行

    Returns:
        統計資訊字典
    """
    stats = {
        'source_authors': 0,      # 源目錄中的作者數
        'target_authors': 0,      # 目標目錄中的作者數
        'moved': 0,               # 移動的漫畫數
        'skipped_no_target': 0,   # 跳過（目標無對應作者）
        'skipped_duplicate': 0,   # 跳過（重複）
        'deleted_empty': 0,       # 刪除的空目錄數
        'errors': 0,              # 錯誤數
        'empty_unmatched_paths': []  # 無配對且為空的源作者目錄路徑
    }

    if not os.path.exists(source_path):
        logging.error(f"源目錄不存在: {source_path}")
        return stats

    if not os.path.exists(target_path):
        logging.error(f"目標目錄不存在: {target_path}")
        return stats

    logging.info(f"開始合併作者目錄")
    logging.info(f"源目錄: {source_path}")
    logging.info(f"目標目錄: {target_path}")
    logging.info(f"測試模式: {dry_run}")

    # 獲取源目錄中的所有作者目錄（只搜尋第一層）
    source_subdirs = get_all_subdirs(source_path)
    source_authors = {}  # {作者名: 作者目錄路徑}

    for subdir_path in source_subdirs:
        dirname = os.path.basename(subdir_path)
        author_name = extract_author_name(dirname)

        # 只處理格式為 [作者名] 的目錄（純作者目錄）
        if author_name and dirname == f"[{author_name}]":
            source_authors[author_name] = subdir_path
            logging.debug(f"源目錄找到作者: [{author_name}]")

    stats['source_authors'] = len(source_authors)
    logging.info(f"源目錄中找到 {stats['source_authors']} 個作者目錄")

    # 獲取目標目錄中的所有作者目錄（只搜尋第一層）
    target_subdirs = get_all_subdirs(target_path)
    target_authors = {}  # {作者名: 作者目錄路徑}

    for subdir_path in target_subdirs:
        dirname = os.path.basename(subdir_path)
        author_name = extract_author_name(dirname)

        if author_name and dirname == f"[{author_name}]":
            target_authors[author_name] = subdir_path
            logging.debug(f"目標目錄找到作者: [{author_name}]")

    stats['target_authors'] = len(target_authors)
    logging.info(f"目標目錄中找到 {stats['target_authors']} 個作者目錄")

    # 處理每個源作者目錄
    for author_name, source_author_path in source_authors.items():
        logging.info(f"\n處理作者: [{author_name}]")

        # 檢查目標目錄中是否有對應的作者目錄
        if author_name not in target_authors:
            stats['skipped_no_target'] += 1
            # 記錄無配對且為空的目錄，供後續詢問刪除
            if not os.listdir(source_author_path):
                logging.warning(f"  目標目錄中沒有 [{author_name}]，且為空目錄")
                stats['empty_unmatched_paths'].append(source_author_path)
            else:
                logging.warning(f"  目標目錄中沒有 [{author_name}]，跳過")
            continue

        target_author_path = target_authors[author_name]

        # 獲取源作者目錄下的所有漫畫目錄（只搜尋第一層）
        manga_dirs = get_all_subdirs(source_author_path)
        logging.info(f"  找到 {len(manga_dirs)} 個漫畫目錄")

        # 移動每個漫畫目錄
        for manga_path in manga_dirs:
            manga_name = os.path.basename(manga_path)
            target_manga_path = os.path.join(target_author_path, manga_name)

            # 檢查目標位置是否已存在同名目錄
            if os.path.exists(target_manga_path):
                logging.warning(f"  跳過（已存在）: {manga_name}")
                stats['skipped_duplicate'] += 1
                continue

            # 移動目錄
            if not dry_run:
                try:
                    shutil.move(manga_path, target_manga_path)
                    logging.info(f"  移動: {manga_name}")
                    stats['moved'] += 1
                except Exception as e:
                    logging.error(f"  移動失敗 {manga_path} -> {target_manga_path}: {e}")
                    stats['errors'] += 1
            else:
                logging.info(f"  [測試] 將移動: {manga_name}")
                stats['moved'] += 1

        # 移動完成後，刪除已空的源作者目錄
        if not dry_run:
            if os.path.exists(source_author_path) and not os.listdir(source_author_path):
                try:
                    os.rmdir(source_author_path)
                    logging.info(f"  已刪除空目錄: {source_author_path}")
                    stats['deleted_empty'] += 1
                except Exception as e:
                    logging.error(f"  刪除空目錄失敗 {source_author_path}: {e}")
                    stats['errors'] += 1
        else:
            remaining = get_all_subdirs(source_author_path)
            if not remaining:
                logging.info(f"  [測試] 將刪除空目錄: {source_author_path}")
                stats['deleted_empty'] += 1

    return stats


def delete_empty_dirs(base_path, dry_run=False):
    """
    刪除指定路徑底下的所有空目錄（只搜尋一層）

    Args:
        base_path: 目標路徑
        dry_run: 是否為測試運行

    Returns:
        (deleted, errors) 已刪除數量和錯誤數量
    """
    deleted = 0
    errors = 0

    subdirs = get_all_subdirs(base_path)
    empty_dirs = [p for p in subdirs if not os.listdir(p)]

    if not empty_dirs:
        logging.info("沒有發現空目錄")
        return deleted, errors

    logging.info(f"發現 {len(empty_dirs)} 個空目錄")
    for p in empty_dirs:
        if dry_run:
            logging.info(f"  [測試] 將刪除空目錄: {p}")
            deleted += 1
        else:
            try:
                os.rmdir(p)
                logging.info(f"  已刪除空目錄: {p}")
                deleted += 1
            except Exception as e:
                logging.error(f"  刪除失敗 {p}: {e}")
                errors += 1

    return deleted, errors


def print_stats(stats):
    """打印統計資訊"""
    print("\n" + "="*60)
    print("整理完成！統計資訊：")
    print("="*60)
    print(f"總計掃描目錄數: {stats['total']}")
    print(f"成功整理數量:   {stats['organized']}")
    print(f"刪除重複數量:   {stats['deleted']}")
    print(f"跳過數量:       {stats['skipped']}")
    print(f"錯誤數量:       {stats['errors']}")
    print("="*60)


def print_merge_stats(stats):
    """打印合併統計資訊"""
    print("\n" + "="*60)
    print("合併完成！統計資訊：")
    print("="*60)
    print(f"源目錄作者數:         {stats['source_authors']}")
    print(f"目標目錄作者數:       {stats['target_authors']}")
    print(f"成功移動漫畫數:       {stats['moved']}")
    print(f"刪除空目錄數:         {stats['deleted_empty']}")
    print(f"跳過（無對應作者）:   {stats['skipped_no_target']} (其中空目錄 {len(stats['empty_unmatched_paths'])} 個)")
    print(f"跳過（重複）:         {stats['skipped_duplicate']}")
    print(f"錯誤數量:             {stats['errors']}")
    print("="*60)


def main():
    """主函數"""
    # 創建日誌目錄
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日誌檔名（使用當前日期時間）
    log_filename = os.path.join(
        log_dir,
        f"organize_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
    )

    # 設置日誌（同時輸出到控制台和文件）
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )

    logging.info(f"日誌檔案: {log_filename}")

    # 預設下載目錄
    default_download_path = r"E:\video\合集\downloads"

    # 檢查執行模式
    merge_mode = "--merge" in sys.argv
    clean_mode = "--clean" in sys.argv

    # 檢查是否為測試模式
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if clean_mode:
        # 清除空目錄模式
        args = [arg for arg in sys.argv[1:] if arg not in ["--clean", "--dry-run", "-n"]]
        clean_path = args[0] if args else default_download_path

        print("="*60)
        print("清除空目錄")
        print("="*60)
        print(f"目標目錄: {clean_path}")
        print(f"測試模式: {'是' if dry_run else '否'}")
        print("="*60)

        subdirs = get_all_subdirs(clean_path)
        empty_dirs = [p for p in subdirs if not os.listdir(p)]

        if not empty_dirs:
            print("\n沒有發現空目錄，不需要清除。")
        else:
            print(f"\n發現 {len(empty_dirs)} 個空目錄：")
            for p in empty_dirs:
                print(f"  {p}")

            if not dry_run:
                response = input("\n確定要刪除以上空目錄？(yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("已取消操作")
                    print(f"\n日誌已保存到: {log_filename}")
                    return

            deleted, errors = delete_empty_dirs(clean_path, dry_run)
            print(f"\n{'[測試] ' if dry_run else ''}已刪除 {deleted} 個空目錄，失敗 {errors} 個。")

    elif merge_mode:
        # 合併模式
        print("="*60)
        print("作者目錄合併腳本")
        print("="*60)

        # 獲取源目錄和目標目錄
        if len(sys.argv) >= 4:
            # 命令行提供了路徑
            source_path = sys.argv[1] if sys.argv[1] != "--merge" else (sys.argv[2] if len(sys.argv) > 2 else None)
            target_path = sys.argv[2] if sys.argv[1] != "--merge" else (sys.argv[3] if len(sys.argv) > 3 else None)

            # 重新解析參數
            args = [arg for arg in sys.argv[1:] if arg not in ["--merge", "--dry-run", "-n"]]
            if len(args) >= 2:
                source_path = args[0]
                target_path = args[1]
            else:
                source_path = None
                target_path = None
        else:
            source_path = None
            target_path = None

        if not source_path:
            source_path = input("請輸入源目錄路徑: ").strip('"')
        if not target_path:
            target_path = input("請輸入目標目錄路徑: ").strip('"')

        print(f"源目錄: {source_path}")
        print(f"目標目錄: {target_path}")
        print(f"測試模式: {'是' if dry_run else '否'}")
        print("="*60)

        if not dry_run:
            response = input("\n確定要執行合併嗎？此操作將移動檔案！(yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("已取消操作")
                return

        # 執行合併
        stats = merge_author_directories(source_path, target_path, dry_run)

        # 打印統計
        print_merge_stats(stats)

        # 詢問是否刪除無配對的空目錄
        empty_paths = stats['empty_unmatched_paths']
        if empty_paths:
            print(f"\n發現 {len(empty_paths)} 個無配對的空目錄：")
            for p in empty_paths:
                print(f"  {p}")

            if dry_run:
                print("\n[測試模式] 若正式執行，將詢問是否刪除以上空目錄。")
            else:
                response = input("\n是否刪除以上無配對的空目錄？(yes/no): ")
                if response.lower() in ['yes', 'y']:
                    deleted = 0
                    for p in empty_paths:
                        try:
                            os.rmdir(p)
                            logging.info(f"已刪除空目錄: {p}")
                            deleted += 1
                        except Exception as e:
                            logging.error(f"刪除失敗 {p}: {e}")
                    print(f"已刪除 {deleted} 個空目錄。")
                else:
                    print("已跳過，不刪除空目錄。")

    else:
        # 整理模式
        # 檢查命令行參數
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            download_path = sys.argv[1]
        else:
            download_path = default_download_path

        print("="*60)
        print("作者分類整理腳本")
        print("="*60)
        print(f"目標目錄: {download_path}")
        print(f"測試模式: {'是' if dry_run else '否'}")
        print("="*60)

        if not dry_run:
            response = input("\n確定要執行整理嗎？此操作將移動和刪除檔案！(yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("已取消操作")
                return

        # 執行整理
        stats = organize_by_author(download_path, dry_run)

        # 打印統計
        print_stats(stats)

    if dry_run:
        print("\n這是測試運行，沒有實際修改任何文件。")
        print("如需實際執行，請移除 --dry-run 或 -n 參數。")

    # 提示日誌檔案位置
    print(f"\n日誌已保存到: {log_filename}")


if __name__ == "__main__":
    main()
