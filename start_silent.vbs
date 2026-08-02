' 静默启动选股工具
' 用法：双击运行，或者放到启动文件夹开机自动运行
' 无命令行窗口，后台静默运行

Set WshShell = CreateObject("WScript.Shell")

' Python路径（虚拟环境的stock_picker.exe，独特进程名）
pythonPath = "D:\tools\stock\stock_picker\.venv\Scripts\stock_picker.exe"

' 主程序路径
scriptPath = "D:\tools\stock\stock_picker\stock_picker\main.py"

' 工作目录
workDir = "D:\tools\stock\stock_picker\stock_picker"

' 运行（0 = 隐藏窗口）
WshShell.CurrentDirectory = workDir
WshShell.Run """" & pythonPath & """ """ & scriptPath & """", 0, False
