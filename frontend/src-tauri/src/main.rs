#![cfg_attr(
  all(not(debug_assertions), target_os = "windows"),
  windows_subsystem = "windows"
)]

use tauri::api::process::Command;
use tauri::Manager;

enum BackendChild {
  Sidecar(tauri::api::process::CommandChild),
  Standard(std::process::Child),
}

impl BackendChild {
  fn kill(self) {
    match self {
      BackendChild::Sidecar(c) => {
        let _ = c.kill();
      }
      BackendChild::Standard(mut c) => {
        let _ = c.kill();
      }
    }
  }
}

fn main() {
  tauri::Builder::default()
    .setup(|app| {
      let mut envs = std::collections::HashMap::new();
      envs.insert("FRP_DESKTOP".to_string(), "true".to_string());

      let mut root_dir = std::env::current_dir().unwrap();
      while !root_dir.join("backend").exists() {
        if let Some(parent) = root_dir.parent() {
          root_dir = parent.to_path_buf();
        } else {
          break;
        }
      }

      let venv_python = if cfg!(target_os = "windows") {
        root_dir.join("venv").join("Scripts").join("python.exe")
      } else {
        root_dir.join("venv").join("bin").join("python")
      };
      let run_py = root_dir.join("backend").join("run.py");

      let child = if venv_python.exists() && run_py.exists() {
        println!("检测到本地开发环境，将直接通过 venv python 运行后台服务: {:?}", venv_python);
        let c = std::process::Command::new(venv_python)
          .arg(run_py)
          .envs(&envs)
          .spawn()
          .expect("Failed to spawn dev python backend");
        BackendChild::Standard(c)
      } else {
        println!("未检测到本地开发环境，启动 PyInstaller 侧边栏服务进程...");
        let (mut rx, c) = Command::new_sidecar("frp-backend")
          .expect("Failed to create sidecar command")
          .envs(envs)
          .spawn()
          .expect("Failed to spawn sidecar process");

        // 在独立线程接收 stdout/stderr 日志，直接打印到终端控制台，便于调试后台错误
        tauri::async_runtime::spawn(async move {
          while let Some(event) = rx.recv().await {
            match event {
              tauri::api::process::CommandEvent::Stdout(line) => {
                println!("[Backend Stdout] {}", line);
              }
              tauri::api::process::CommandEvent::Stderr(line) => {
                eprintln!("[Backend Stderr] {}", line);
              }
              _ => {}
            }
          }
        });
        BackendChild::Sidecar(c)
      };

      // 注册应用关闭钩子：在窗口关闭/程序退出时，绝对强杀 Python 进程以释放端口
      let child_mutex = std::sync::Arc::new(std::sync::Mutex::new(Some(child)));
      let child_clone = child_mutex.clone();
      app.listen_global("tauri://close-requested", move |_| {
        if let Ok(mut guard) = child_clone.lock() {
          if let Some(c) = guard.take() {
            c.kill(); // 终止后台进程
          }
        }
      });

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
