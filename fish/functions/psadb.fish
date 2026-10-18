function psadb
    # 截图并保存到临时目录
    adb shell screencap -p >~/.cache/tmp/psadb.png

    # 检查上一条命令是否执行成功
    if test $status -eq 0
        # 使用 AppleScript 将图片读入剪贴板
        osascript -e 'set the clipboard to (read (POSIX file "~/.cache/tmp/psadb.png") as «class PNGf»)'
        echo "📸 截图已成功写入剪贴板"
    else
        echo "❌ ADB 连接失败，请检查设备"
    end
end
