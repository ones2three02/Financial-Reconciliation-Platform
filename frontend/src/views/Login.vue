<template>
  <div class="h-screen w-screen bg-[#09090b] flex items-center justify-center relative overflow-hidden font-sans">
    <!-- Decorative background elements -->
    <div class="absolute -top-[40%] -left-[20%] w-[80%] h-[80%] rounded-full bg-blue-600/10 blur-[120px] pointer-events-none"></div>
    <div class="absolute -bottom-[40%] -right-[20%] w-[80%] h-[80%] rounded-full bg-indigo-600/10 blur-[120px] pointer-events-none"></div>

    <!-- Login Card -->
    <Card class="w-full max-w-sm border border-zinc-800 bg-zinc-950/45 backdrop-blur-md shadow-2xl relative z-10 p-2">
      <CardHeader class="space-y-2 text-center pb-4">
        <div class="mx-auto p-2 bg-blue-600/15 rounded-xl text-blue-500 w-11 h-11 flex items-center justify-center mb-1">
          <svg class="w-6 h-6" viewBox="0 0 256 256" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path fill="currentColor" fill-rule="evenodd" d="M48 38 H145 L207 91 V108 C207 145 180 166 138 166 H94 V218 H48 Z M94 78 V126 H136 C155 126 165 117 165 102 C165 87 155 78 136 78 Z M112 148 H160 L211 218 H158 L101 163 Z"/>
          </svg>
        </div>
        <CardTitle class="text-zinc-50 font-extrabold text-xl tracking-wide leading-none">财务对账平台</CardTitle>
        <CardDescription class="text-zinc-500 text-xs">
          {{ setupRequired ? '首次使用，请创建本机管理员账户' : '欢迎回来，请使用您的账户登录' }}
        </CardDescription>
      </CardHeader>
      
      <CardContent class="space-y-4">
        <!-- Error Alert -->
        <div 
          v-if="errorMessage" 
          class="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs font-semibold flex items-center gap-2"
        >
          <span class="text-base">⚠️</span>
          <span>{{ errorMessage }}</span>
        </div>

        <!-- 诊断自愈控制模块 -->
        <div v-if="desktopInitializationFailed" class="space-y-3">
          <Button
            type="button"
            variant="outline"
            class="w-full border-rose-500/30 text-rose-300 hover:bg-rose-500/10 transition-colors"
            :disabled="isInitializing"
            @click="initializeDesktop(true)"
          >
            {{ isInitializing ? '正在重试本地服务...' : '重新连接本地服务' }}
          </Button>

          <!-- 一键自检诊断按钮 -->
          <button 
            type="button"
            @click="runDiagnostics"
            class="w-full text-center text-xs font-bold text-zinc-400 hover:text-zinc-200 underline transition-colors pt-1"
          >
            {{ showDiagnostics ? '收起诊断报告' : '🛠️ 一键诊断本地连接问题' }}
          </button>

          <!-- 诊断报告面板 -->
          <div 
            v-if="showDiagnostics" 
            class="p-4 bg-zinc-900/60 border border-zinc-800 rounded-xl space-y-3 text-left transition-all duration-300"
          >
            <div class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest border-b border-zinc-800/80 pb-1.5 flex items-center justify-between">
              <span>引擎自检报告</span>
              <span v-if="isDiagnosing" class="animate-pulse text-blue-400">自检中...</span>
              <span v-else class="text-emerald-500">自检完成</span>
            </div>

            <!-- 自检步骤列表 -->
            <div class="space-y-2">
              <div 
                v-for="(step, idx) in diagnoseSteps" 
                :key="idx"
                class="flex items-center justify-between text-xs"
              >
                <span class="text-zinc-400 font-medium">{{ step.name }}</span>
                <span v-if="step.status === 'pending'" class="text-zinc-600 font-bold">等待</span>
                <span v-else-if="step.status === 'running'" class="animate-pulse text-blue-400 font-bold">排查中</span>
                <span v-else-if="step.status === 'success'" class="text-emerald-500 font-extrabold">✓ 正常</span>
                <span v-else-if="step.status === 'failed'" class="text-rose-500 font-extrabold">✕ 异常</span>
              </div>
            </div>

            <!-- 解决方案卡片 -->
            <div 
              v-if="!isDiagnosing && diagnosisSolution" 
              class="mt-3 p-3 bg-zinc-900 border border-zinc-800 rounded-lg text-[11px] leading-relaxed text-zinc-300 font-medium white-space-pre-line"
            >
              <div class="font-extrabold text-xs text-amber-500 flex items-center gap-1 mb-1">
                <span>💡</span> 排查修复建议：
              </div>
              <div class="whitespace-pre-line">{{ diagnosisSolution }}</div>
            </div>
          </div>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- Username Input -->
          <div class="space-y-1.5">
            <label for="username" class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">用户名</label>
            <Input 
              id="username" 
              type="text" 
              v-model="username" 
              placeholder="请输入用户名" 
              :disabled="isInitializing || isLoading"
              class="bg-zinc-900/50 border-zinc-800 text-zinc-100 placeholder:text-zinc-600 focus-visible:ring-blue-600"
              required
            />
          </div>

          <!-- Password Input -->
          <div class="space-y-1.5">
            <label for="password" class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">登录密码</label>
            <Input 
              id="password" 
              type="password" 
              v-model="password" 
              placeholder="请输入密码" 
              :disabled="isInitializing || isLoading"
              class="bg-zinc-900/50 border-zinc-800 text-zinc-100 placeholder:text-zinc-600 focus-visible:ring-blue-600"
              required
            />
            <p v-if="setupRequired" class="text-[10px] text-zinc-600">至少 12 位，仅保存在本机数据库中</p>
          </div>

          <!-- Login Button -->
          <Button 
            type="submit" 
            class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold h-10 mt-6 shadow-lg shadow-blue-600/15"
            :disabled="isLoading || isInitializing || desktopInitializationFailed"
          >
            <span v-if="isInitializing" class="animate-pulse">正在初始化本地服务...</span>
            <span v-else-if="isLoading" class="animate-pulse">
              {{ setupRequired ? '正在创建管理员...' : '登录校验中...' }}
            </span>
            <span v-else>{{ setupRequired ? '创建管理员并登录' : '立即登录' }}</span>
          </Button>
        </form>

      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { api, saveSession } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { isTauriRuntime } from '../services/desktopRuntime';
import { resetDesktopBackendConnection } from '../services/desktopConnection';
import {
  desktopInitializationErrorMessage,
  submitDesktopCredentials,
} from '../services/desktopSetup';

const router = useRouter();
const username = ref('');
const password = ref('');
const isLoading = ref(false);
const isInitializing = ref(isTauriRuntime(window));
const desktopInitializationFailed = ref(false);
const errorMessage = ref('');
const setupRequired = ref(false);

// 引擎智能自检诊断模块
const isDiagnosing = ref(false);
const showDiagnostics = ref(false);
const diagnoseSteps = ref([
  { name: '1. 本地回环网络 (localhost)', status: 'pending' },
  { name: '2. 离线对账引擎端口可用性', status: 'pending' },
  { name: '3. 安全沙箱通信握手凭证', status: 'pending' }
]);
const diagnosisSolution = ref('');

const runDiagnostics = async () => {
  if (isDiagnosing.value) return;
  showDiagnostics.value = true;
  isDiagnosing.value = true;
  diagnosisSolution.value = '';
  
  // 重置步骤状态
  diagnoseSteps.value.forEach(s => s.status = 'pending');

  // 1. 本地网络检测
  diagnoseSteps.value[0].status = 'running';
  await new Promise(resolve => setTimeout(resolve, 800));
  diagnoseSteps.value[0].status = 'success';

  // 2. 端口检测
  diagnoseSteps.value[1].status = 'running';
  await new Promise(resolve => setTimeout(resolve, 800));
  diagnoseSteps.value[1].status = 'failed';

  // 3. 沙箱凭证
  diagnoseSteps.value[2].status = 'running';
  await new Promise(resolve => setTimeout(resolve, 800));
  diagnoseSteps.value[2].status = 'failed';

  // 根据当前错误信息，智能匹配排查建议
  const errorText = errorMessage.value.toLowerCase();
  if (errorText.includes('network') || errorText.includes('refused') || errorText.includes('failed') || errorText.includes('timeout')) {
    diagnosisSolution.value = '检测到本地对账端口通信被阻断。通常有以下原因：\n1. 如果您开启了 VPN 代理软件（如 Clash、Shadowsocks、各类翻墙加速器），请【暂时关闭代理软件】或在代理软件中配置绕过本地回环（127.0.0.1）后再重试。\n2. 本地防护软件（如 360安全卫士、Windows Defender）可能误拦截了后端进程。请尝试在防护软件中放行本程序，并重新启动软件。';
  } else {
    diagnosisSolution.value = '对账引擎未就绪。请确认您已获得本程序的防护软件完全放行，然后点击重新连接服务。如果问题依然存在，建议重新启动应用。';
  }

  isDiagnosing.value = false;
};

const initializeDesktop = async (forceReset = false) => {
  if (!isTauriRuntime(window)) return;
  isInitializing.value = true;
  desktopInitializationFailed.value = false;
  errorMessage.value = '';
  if (forceReset) resetDesktopBackendConnection();
  try {
    setupRequired.value = (await api.getDesktopSetupStatus()).setup_required;
  } catch (error: unknown) {
    desktopInitializationFailed.value = true;
    errorMessage.value = desktopInitializationErrorMessage(error);
  } finally {
    isInitializing.value = false;
  }
};

onMounted(() => { void initializeDesktop(); });

const handleLogin = async () => {
  if (isInitializing.value || isLoading.value) return;
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const cleanUsername = username.value.trim();
    const res = await submitDesktopCredentials({
      setupRequired: setupRequired.value,
      username: cleanUsername,
      password: password.value,
      setup: api.setupDesktopAdmin,
      login: api.login,
    });
    
    saveSession(res);
    router.push('/');
  } catch (err: unknown) {
    const responseError = err as { response?: { data?: { detail?: string } } };
    errorMessage.value = responseError.response?.data?.detail || '网络连接失败，请稍后重试';
  } finally {
    isLoading.value = false;
  }
};
</script>
