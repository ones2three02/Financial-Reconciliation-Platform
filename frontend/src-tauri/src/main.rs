#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use rand::rngs::OsRng;
use rand::RngCore;
use serde::Serialize;
use std::io;
use std::net::{IpAddr, Ipv4Addr, SocketAddr, TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};
use tauri::{CustomMenuItem, Manager, State, SystemTray, SystemTrayEvent, SystemTrayMenu, WindowEvent};

#[derive(Clone, Serialize)]
struct DesktopBackendConfig {
    api_base_url: String,
    token: String,
}

impl DesktopBackendConfig {
    fn new(port: u16, token: String) -> Self {
        Self {
            api_base_url: format!("http://127.0.0.1:{port}/api/v1"),
            token,
        }
    }
}

struct BackendChild(Option<tauri::api::process::CommandChild>);

impl BackendChild {
    fn terminate(&mut self) {
        if let Some(child) = self.0.take() {
            let _ = child.kill();
        }
    }
}

impl Drop for BackendChild {
    fn drop(&mut self) {
        self.terminate();
    }
}

struct BackendRuntime {
    config: DesktopBackendConfig,
    port: u16,
    child: Mutex<BackendChild>,
}

impl BackendRuntime {
    fn terminate(&self) {
        if let Ok(mut child) = self.child.lock() {
            child.terminate();
        }
    }
}

#[tauri::command]
async fn desktop_backend_config(
    runtime: State<'_, BackendRuntime>,
) -> Result<DesktopBackendConfig, String> {
    wait_for_backend(runtime.port, Duration::from_secs(90)).map_err(|error| error.to_string())?;
    Ok(runtime.config.clone())
}

fn generate_launch_token() -> String {
    let mut bytes = [0_u8; 32];
    OsRng.fill_bytes(&mut bytes);
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn select_backend_port() -> io::Result<u16> {
    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0))?;
    listener.local_addr().map(|address| address.port())
}

fn find_project_root(start: &Path) -> Option<PathBuf> {
    start
        .ancestors()
        .find(|path| path.join("backend").join("run.py").is_file())
        .map(Path::to_path_buf)
}

fn spawn_backend(app: &tauri::App, port: u16, token: &str) -> io::Result<BackendChild> {
    if cfg!(debug_assertions) {
        let current_dir = std::env::current_dir()?;
        if let Some(root) = find_project_root(&current_dir) {
            let venv_python = if cfg!(target_os = "windows") {
                root.join("venv").join("Scripts").join("python.exe")
            } else {
                root.join("venv").join("bin").join("python")
            };
            let run_py = root.join("backend").join("run.py");
            if venv_python.is_file() {
                let mut env_map = std::collections::HashMap::new();
                env_map.insert("FRP_DESKTOP".to_string(), "true".to_string());
                env_map.insert("FRP_PORT".to_string(), port.to_string());
                env_map.insert("FRP_DESKTOP_TOKEN".to_string(), token.to_string());

                let (_, child) = tauri::api::process::Command::new(venv_python.to_string_lossy().to_string())
                    .args([run_py.to_string_lossy().to_string()])
                    .current_dir(root)
                    .envs(env_map)
                    .spawn()
                    .map_err(|e| io::Error::new(io::ErrorKind::Other, format!("启动 Python 调试服务失败: {e}")))?;
                return Ok(BackendChild(Some(child)));
            }
        }
    }

    // 打包模式下，从资源（Resources）中寻找解压好的 Python 离线服务文件夹，实现零解压零扫描秒开
    let resource_path = app
        .path_resolver()
        .resource_dir()
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "未找到程序资源目录"))?
        .join("resources")
        .join("frp-backend-dir");

    let exe_name = if cfg!(target_os = "windows") {
        "frp-backend-dir.exe"
    } else {
        "frp-backend-dir"
    };
    let backend_bin = resource_path.join(exe_name);
    if !backend_bin.is_file() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!("未找到桌面后端离线服务: {}", backend_bin.display()),
        ));
    }

    let mut env_map = std::collections::HashMap::new();
    env_map.insert("FRP_DESKTOP".to_string(), "true".to_string());
    env_map.insert("FRP_PORT".to_string(), port.to_string());
    env_map.insert("FRP_DESKTOP_TOKEN".to_string(), token.to_string());

    let (_, child) = tauri::api::process::Command::new(backend_bin.to_string_lossy().to_string())
        .current_dir(resource_path) // 在该目录运行，确保依赖的 dll / dylib 正确解析
        .envs(env_map)
        .spawn()
        .map_err(|e| io::Error::new(io::ErrorKind::Other, format!("启动桌面后端离线服务失败: {e}")))?;

    Ok(BackendChild(Some(child)))
}

fn wait_for_backend(port: u16, timeout: Duration) -> io::Result<()> {
    let address = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), port);
    let started_at = Instant::now();
    while started_at.elapsed() < timeout {
        if TcpStream::connect_timeout(&address, Duration::from_secs(1)).is_ok() {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(200));
    }
    Err(io::Error::new(
        io::ErrorKind::TimedOut,
        format!("桌面后端未能在 {} 秒内启动", timeout.as_secs()),
    ))
}

fn main() {
    let quit = CustomMenuItem::new("quit".to_string(), "退出对账平台");
    let show = CustomMenuItem::new("show".to_string(), "显示主窗口");
    let tray_menu = SystemTrayMenu::new()
        .add_item(show)
        .add_native_item(tauri::SystemTrayMenuItem::Separator)
        .add_item(quit);
    let system_tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
        .system_tray(system_tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => {
                match id.as_str() {
                    "quit" => {
                        if let Some(runtime) = app.try_state::<BackendRuntime>() {
                            runtime.terminate();
                        }
                        std::process::exit(0);
                    }
                    "show" => {
                        let window = app.get_window("main").unwrap();
                        window.show().unwrap();
                        window.set_focus().unwrap();
                    }
                    _ => {}
                }
            }
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![desktop_backend_config])
        .setup(|app| {
            let port = select_backend_port()?;
            let token = generate_launch_token();
            let child = spawn_backend(app, port, &token)?;
            app.manage(BackendRuntime {
                config: DesktopBackendConfig::new(port, token),
                port,
                child: Mutex::new(child),
            });
            Ok(())
        })
        .on_window_event(|event| {
            if let WindowEvent::CloseRequested { api, .. } = event.event() {
                api.prevent_close();
                event.window().hide().unwrap();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn desktop_backend_config_uses_dynamic_loopback_port() {
        let config = DesktopBackendConfig::new(43123, "a".repeat(64));

        assert_eq!(config.api_base_url, "http://127.0.0.1:43123/api/v1");
        assert_eq!(config.token.len(), 64);
    }

    #[test]
    fn launch_tokens_are_random_hex_values() {
        let first = generate_launch_token();
        let second = generate_launch_token();

        assert_eq!(first.len(), 64);
        assert!(first.chars().all(|character| character.is_ascii_hexdigit()));
        assert_ne!(first, second);
    }

    #[test]
    fn selected_backend_port_is_available_for_binding() {
        let port = select_backend_port().expect("select backend port");
        let listener = TcpListener::bind(("127.0.0.1", port));

        assert!(listener.is_ok());
    }
}
