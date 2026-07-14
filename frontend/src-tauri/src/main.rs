#![cfg_attr(
  all(not(debug_assertions), target_os = "windows"),
  windows_subsystem = "windows"
)]

use tauri::api::process::Command;
use tauri::Manager;

fn main() {
  tauri::Builder::default()
    .setup(|app| {
      let mut envs = std::collections::HashMap::new();
      envs.insert("FRP_DESKTOP".to_string(), "true".to_string());

      // 启动 FastAPI python 侧边二进制服务进程，并自动传入 FRP_DESKTOP=true
      let (mut rx, child) = Command::new_sidecar("frp-backend")
        .expect("Failed to create sidecar command")
        .envs(envs)
        .spawn()
        .expect("Failed to spawn sidecar process");

      // 在独立线程接收 stdout/stderr 日志，避免进程管线阻塞
      tauri::async_runtime::spawn(async move {
        while let Some(_event) = rx.recv().await {
          // 可在这里做后台日志流审计
        }
      });

      // 注册应用关闭钩子：在窗口关闭/程序退出时，绝对强杀 Python 进程以释放端口
      let child_mutex = std::sync::Arc::new(std::sync::Mutex::new(Some(child)));
      let child_clone = child_mutex.clone();
      app.listen_global("tauri://close-requested", move |_| {
        if let Ok(mut guard) = child_clone.lock() {
          if let Some(c) = guard.take() {
            let _ = c.kill(); // 终止侧边进程
          }
        }
      });

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
