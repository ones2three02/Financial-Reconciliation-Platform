import { ref, reactive } from 'vue';

export interface DownloadItem {
  id: string;
  filename: string;
  filePath: string;
  status: 'downloading' | 'completed' | 'failed';
  timestamp: Date;
  errorMessage?: string;
}

export const downloadHistory = ref<DownloadItem[]>([]);

// Helper to determine if we are in Tauri runtime
const isTauri = (): boolean => {
  return typeof window !== 'undefined' && window.__TAURI__ !== undefined;
};

export const addDownload = (filename: string, filePath: string, status: DownloadItem['status']) => {
  const item = reactive<DownloadItem>({
    id: Math.random().toString(36).substring(2, 9),
    filename,
    filePath,
    status,
    timestamp: new Date()
  });
  downloadHistory.value.unshift(item);
  if (downloadHistory.value.length > 10) {
    downloadHistory.value.pop();
  }
  return item;
};

export const startDownload = async (filename: string, blob: Blob): Promise<DownloadItem> => {
  if (isTauri()) {
    const tauri = (window as any).__TAURI__;
    
    // Create temporary item
    const item = addDownload(filename, '正在选择保存路径...', 'downloading');
    
    try {
      // 1. Open save dialog
      const path = await tauri.dialog.save({
        defaultPath: filename,
        filters: [{ name: 'Excel Spreadsheets', extensions: ['xlsx'] }]
      });
      
      // If user canceled the save dialog
      if (!path) {
        item.status = 'failed';
        item.errorMessage = '用户取消保存';
        item.filePath = '未选择保存路径';
        return item;
      }
      
      item.filePath = path;
      
      // 2. Read blob as ArrayBuffer and write binary file
      const buffer = await blob.arrayBuffer();
      const uint8Array = new Uint8Array(buffer);
      await tauri.fs.writeBinaryFile(path, uint8Array);
      
      item.status = 'completed';
      return item;
    } catch (err: any) {
      item.status = 'failed';
      item.errorMessage = err.message || String(err);
      return item;
    }
  } else {
    // Regular web browser download fallback
    const item = addDownload(filename, '浏览器默认下载目录', 'downloading');
    try {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      item.status = 'completed';
      return item;
    } catch (err: any) {
      item.status = 'failed';
      item.errorMessage = err.message || String(err);
      return item;
    }
  }
};

export const openFile = async (filePath: string) => {
  if (isTauri()) {
    try {
      const tauri = (window as any).__TAURI__;
      await tauri.shell.open(filePath);
    } catch (e) {
      console.error('Failed to open file:', e);
    }
  }
};

export const openFolder = async (filePath: string) => {
  if (isTauri()) {
    try {
      const tauri = (window as any).__TAURI__;
      // Extract parent directory path
      // Handle both forward and backward slashes (Windows/macOS)
      const lastSlash = Math.max(filePath.lastIndexOf('/'), filePath.lastIndexOf('\\'));
      if (lastSlash !== -1) {
        const parentPath = filePath.substring(0, lastSlash);
        await tauri.shell.open(parentPath);
      }
    } catch (e) {
      console.error('Failed to open folder:', e);
    }
  }
};
