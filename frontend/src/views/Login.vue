<template>
  <div class="h-screen w-screen bg-[#09090b] flex items-center justify-center relative overflow-hidden font-sans">
    <!-- Decorative background elements -->
    <div class="absolute -top-[40%] -left-[20%] w-[80%] h-[80%] rounded-full bg-blue-600/10 blur-[120px] pointer-events-none"></div>
    <div class="absolute -bottom-[40%] -right-[20%] w-[80%] h-[80%] rounded-full bg-indigo-600/10 blur-[120px] pointer-events-none"></div>

    <!-- Login Card -->
    <Card class="w-full max-w-sm border border-zinc-800 bg-zinc-950/45 backdrop-blur-md shadow-2xl relative z-10 p-2">
      <CardHeader class="space-y-2 text-center pb-4">
        <div class="mx-auto p-3 bg-blue-600/15 rounded-xl text-blue-500 w-11 h-11 flex items-center justify-center mb-1">
          <Activity class="w-6 h-6" />
        </div>
        <CardTitle class="text-zinc-50 font-extrabold text-xl tracking-wide leading-none">财务对账平台</CardTitle>
        <CardDescription class="text-zinc-500 text-xs">欢迎回来，请使用您的管理员账户登录</CardDescription>
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

        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- Username Input -->
          <div class="space-y-1.5">
            <label for="username" class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">用户名</label>
            <Input 
              id="username" 
              type="text" 
              v-model="username" 
              placeholder="请输入用户名" 
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
              class="bg-zinc-900/50 border-zinc-800 text-zinc-100 placeholder:text-zinc-600 focus-visible:ring-blue-600"
              required
            />
          </div>

          <!-- Login Button -->
          <Button 
            type="submit" 
            class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold h-10 mt-6 shadow-lg shadow-blue-600/15"
            :disabled="isLoading"
          >
            <span v-if="isLoading" class="animate-pulse">登录校验中...</span>
            <span v-else>立即登录</span>
          </Button>
        </form>

      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { api, saveSession } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Activity } from 'lucide-vue-next';

const router = useRouter();
const username = ref('');
const password = ref('');
const isLoading = ref(false);
const errorMessage = ref('');

const handleLogin = async () => {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const res = await api.login(username.value.trim(), password.value);
    
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
