!macro NSIS_HOOK_PREINSTALL
    DetailPrint "正在停止已运行的对账平台进程以防文件占用..."
    nsExec::Exec 'taskkill /F /IM ReconFlow.exe'
    nsExec::Exec 'taskkill /F /IM 财务自动对账平台.exe'
    nsExec::Exec 'taskkill /F /IM frp-backend-dir.exe'
    Sleep 1500
!macroend

!macro NSIS_HOOK_PREUNINSTALL
    DetailPrint "正在停止已运行的对账平台进程以防文件占用..."
    nsExec::Exec 'taskkill /F /IM ReconFlow.exe'
    nsExec::Exec 'taskkill /F /IM 财务自动对账平台.exe'
    nsExec::Exec 'taskkill /F /IM frp-backend-dir.exe'
    Sleep 1500
!macroend
