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
use tauri::{Manager, State, WindowEvent};

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

struct BackendChild(Option<std::process::Child>);

impl BackendChild {
    fn terminate(&mut self) {
        if let Some(mut child) = self.0.take() {
            let _ = child.kill();
            let _ = child.wait();
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

fn packaged_sidecar_path() -> io::Result<PathBuf> {
    let executable = std::env::current_exe()?;
    let directory = executable
        .parent()
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "无法定位桌面程序目录"))?;
    let file_name = if cfg!(target_os = "windows") {
        "frp-backend.exe"
    } else {
        "frp-backend"
    };
    Ok(directory.join(file_name))
}

fn spawn_backend(port: u16, token: &str) -> io::Result<BackendChild> {
    let configure_command = |command: &mut std::process::Command| {
        command
            .env("FRP_DESKTOP", "true")
            .env("FRP_PORT", port.to_string())
            .env("FRP_DESKTOP_TOKEN", token);
    };

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
                let mut command = std::process::Command::new(venv_python);
                configure_command(&mut command);
                let child = command.arg(run_py).current_dir(root).spawn()?;
                return Ok(BackendChild(Some(child)));
            }
        }
    }

    let sidecar = packaged_sidecar_path()?;
    if !sidecar.is_file() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!("未找到桌面后端程序: {}", sidecar.display()),
        ));
    }
    let mut command = std::process::Command::new(sidecar);
    configure_command(&mut command);
    Ok(BackendChild(Some(command.spawn()?)))
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
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![desktop_backend_config])
        .setup(|app| {
            let port = select_backend_port()?;
            let token = generate_launch_token();
            let child = spawn_backend(port, &token)?;
            app.manage(BackendRuntime {
                config: DesktopBackendConfig::new(port, token),
                port,
                child: Mutex::new(child),
            });
            Ok(())
        })
        .on_window_event(|event| {
            if matches!(event.event(), WindowEvent::CloseRequested { .. }) {
                event.window().state::<BackendRuntime>().terminate();
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
