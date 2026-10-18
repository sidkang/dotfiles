function cleantf
    # 检查是否输入了路径
    if test (count $argv) -eq 0
        echo "请输入 TF 卡的挂载路径（例如: cleantf /Volumes/Untitled）"
        return 1
    end

    set -l target $argv[1]

    # 定义要删除的垃圾清单
    set -l junk_list \
        ".fseventsd" \
        ".Spotlight-V100" \
        ".Trashes" \
        "System Volume Information" \
        "._*" \
        ".DS_Store"

    echo "正在清理目录: $target ..."

    for item in $junk_list
        # 使用 find 命令处理带通配符的文件（如 ._*）和普通文件夹
        find "$target" -maxdepth 1 -name "$item" -exec rm -rf {} +
    end

    echo "✨ 清理完成！可以安全弹出磁盘了。"
end
