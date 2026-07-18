<template>
  <div class="h-[calc(100vh-8rem)] flex flex-col gap-4 fade-in overflow-hidden">
    <!-- Top Tabs Selection -->
    <div id="store-tab-controls" class="flex border-b border-slate-200/80 gap-6">
      <button 
        @click="activeTab = 'stores'"
        class="pb-3 text-sm font-bold border-b-2 transition-all flex items-center gap-2 select-none"
        :class="activeTab === 'stores' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-700'"
      >
        <StoreIcon class="w-4.5 h-4.5" />
        <span>标准门店管理</span>
      </button>
      <button 
        @click="activeTab = 'aliases'"
        class="pb-3 text-sm font-bold border-b-2 transition-all flex items-center gap-2 select-none"
        :class="activeTab === 'aliases' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-700'"
      >
        <Link class="w-4.5 h-4.5" />
        <span>别名别称绑定</span>
      </button>
    </div>

    <!-- Tab 1: Standard Stores Management -->
    <div v-if="activeTab === 'stores'" class="flex-1 flex flex-col overflow-hidden min-h-0 fade-in">
      <Card id="store-list-card" class="shadow-sm border border-slate-200/80 flex-1 flex flex-col overflow-hidden min-h-0 bg-white">
        <CardHeader class="flex flex-row items-center justify-between flex-wrap gap-4 pb-4">
          <div>
            <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
              <StoreIcon class="h-4.5 w-4.5 text-blue-500" />
              <span>标准门店名录</span>
            </CardTitle>
            <CardDescription>配置集团下属的标准门店基本信息与联系人，用于生成统一对账报表</CardDescription>
          </div>
          <!-- Search & Add Actions -->
          <div class="flex items-center gap-3">
            <Input 
              v-model="storeSearchQuery" 
              placeholder="搜索名称/编码/区域..." 
              class="h-9 w-48 text-xs font-semibold rounded-lg"
            />
            <Button 
              @click="openAddModal"
              class="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-1.5 h-9 shrink-0"
            >
              <Plus class="w-4 h-4" />
              <span>新增标准门店</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent class="p-0 flex-1 flex flex-col overflow-hidden min-h-0">
          <div class="flex-1 overflow-auto min-h-0 border-t border-slate-100">
            <table class="w-full text-left border-collapse select-none">
              <thead>
                <tr class="sticky top-0 z-10 bg-slate-50 text-slate-400 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200/80 select-none">
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">门店编码</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">标准门店名称</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">所在区域</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">店长/负责人</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">联系电话</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4 text-center">状态</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4 text-center">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                <tr v-if="paginatedStores.length === 0">
                  <td colspan="7" class="p-12 text-center text-slate-400 font-medium">
                    <div class="flex flex-col items-center justify-center gap-2">
                      <FolderOpen class="w-8 h-8 text-slate-300" />
                      <span>暂无满足条件的标准门店记录</span>
                    </div>
                  </td>
                </tr>
                <tr v-for="s in paginatedStores" :key="s.id" class="hover:bg-slate-50/40 transition-colors">
                  <td class="p-4 font-mono font-bold text-slate-500"><div class="flex items-center gap-1.5 group/copy"><span v-if="s.code" class="select-text inline-block">{{ s.code?.trim() }}</span><span v-else class="select-none text-slate-300/80">—</span><button v-if="s.code" @click="copyText(s.code, s.id + '-code')" class="opacity-0 group-hover/copy:opacity-100 transition-opacity p-0.5 text-slate-400 hover:text-blue-600 rounded hover:bg-slate-100/80 shrink-0 flex items-center gap-1 scale-95" title="点击复制"><Check v-if="copiedId === s.id + '-code'" class="w-3 h-3 text-emerald-500" /><Copy v-else class="w-3 h-3" /><span v-if="copiedId === s.id + '-code'" class="text-[9px] text-emerald-500 font-bold">已复制</span></button></div></td>
                  <td class="p-4 font-extrabold text-slate-800"><div class="flex items-center gap-1.5 group/copy"><span class="select-text inline-block">{{ s.name?.trim() }}</span><button @click="copyText(s.name, s.id + '-name')" class="opacity-0 group-hover/copy:opacity-100 transition-opacity p-0.5 text-slate-400 hover:text-blue-600 rounded hover:bg-slate-100 shrink-0 flex items-center gap-1 scale-95" title="点击复制"><Check v-if="copiedId === s.id + '-name'" class="w-3 h-3 text-emerald-500" /><Copy v-else class="w-3 h-3" /><span v-if="copiedId === s.id + '-name'" class="text-[9px] text-emerald-500 font-bold">已复制</span></button></div></td>
                  <td class="p-4 font-medium text-slate-600"><span v-if="s.region" class="select-text inline-block">{{ s.region?.trim() }}</span><span v-else class="select-none text-slate-300/80">—</span></td>
                  <td class="p-4 font-medium text-slate-600"><span v-if="s.manager" class="select-text inline-block">{{ s.manager?.trim() }}</span><span v-else class="select-none text-slate-300/80">—</span></td>
                  <td class="p-4 font-mono text-slate-500"><span v-if="s.phone" class="select-text inline-block">{{ s.phone?.trim() }}</span><span v-else class="select-none text-slate-300/80">—</span></td>
                  <td class="p-4 text-center">
                    <button 
                      @click="openStoreStatusModal(s)"
                      class="px-2.5 py-1 rounded-full text-[10px] font-bold inline-flex items-center gap-1 transition-all select-none"
                      :class="s.is_active ? 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100' : 'bg-slate-100 text-slate-400 hover:bg-slate-200'"
                      title="点击切换状态"
                    >
                      <span class="w-1.5 h-1.5 rounded-full" :class="s.is_active ? 'bg-emerald-500' : 'bg-slate-400'"></span>
                      <span>{{ s.is_active ? '运营中' : '已停用' }}</span>
                    </button>
                  </td>
                  <td class="p-4 text-center">
                    <div class="flex items-center justify-center gap-2 select-none">
                      <Button 
                        @click="openEditModal(s)"
                        variant="ghost"
                        size="xs"
                        class="text-blue-600 hover:text-blue-800 hover:bg-blue-50 font-bold"
                      >
                        编辑
                      </Button>
                      <Button
                        @click="openStoreStatusModal(s)"
                        variant="ghost"
                        size="xs"
                        :class="s.is_active ? 'text-amber-600 hover:text-amber-800 hover:bg-amber-50 font-bold' : 'text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 font-bold'"
                      >
                        {{ s.is_active ? '停用' : '重新启用' }}
                      </Button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Stores Pagination Controls -->
          <div v-if="storeTotalPages > 1" class="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50/50 text-xs">
            <div class="text-slate-400 font-medium select-none">
              显示第 {{ (storeCurrentPage - 1) * storePageSize + 1 }} 至 {{ Math.min(storeCurrentPage * storePageSize, filteredStores.length) }} 家门店，共 {{ filteredStores.length }} 家
            </div>
            <div class="flex items-center gap-2">
              <Button 
                size="xs" 
                variant="outline" 
                :disabled="storeCurrentPage === 1" 
                @click="storeCurrentPage--"
                class="h-7 text-[11px] font-bold border-slate-200/80 hover:bg-slate-50"
              >
                上一页
              </Button>
              <span class="text-slate-600 font-bold px-2 select-none">第 {{ storeCurrentPage }} / {{ storeTotalPages }} 页</span>
              <Button 
                size="xs" 
                variant="outline" 
                :disabled="storeCurrentPage === storeTotalPages" 
                @click="storeCurrentPage++"
                class="h-7 text-[11px] font-bold border-slate-200/80 hover:bg-slate-50"
              >
                下一页
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Tab 2: Alias Standardization Mapping -->
    <div v-else-if="activeTab === 'aliases'" class="flex-1 flex flex-col overflow-hidden min-h-0 fade-in">
      <Card id="store-alias-card" class="shadow-sm border border-slate-200/80 flex-1 flex flex-col overflow-hidden min-h-0 bg-white">
        <CardHeader class="flex flex-row items-center justify-between flex-wrap gap-4 pb-4">
          <div>
            <CardTitle class="flex items-center gap-2.5 text-base font-bold text-slate-800">
              <Link class="h-4.5 w-4.5 text-blue-500" />
              <span>门店别名标准化</span>
            </CardTitle>
            <CardDescription>关联三方交易渠道 Excel 中的非标准别名到财务汇总标准店名</CardDescription>
          </div>

          <!-- Filters -->
          <div class="flex items-center gap-4 flex-wrap shrink-0">
            <!-- Search Query Input -->
            <Input 
              v-model="aliasSearchQuery" 
              placeholder="搜索渠道原始店名..." 
              class="h-9 w-44 text-xs font-semibold rounded-lg"
            />
            
            <!-- Tab Filters -->
            <div class="flex items-center gap-1 bg-slate-100/80 p-1 rounded-xl">
              <button 
                @click="aliasFilter = 'pending'"
                :class="[
                  'px-3.5 py-1.5 text-[11px] font-extrabold rounded-lg transition-all flex items-center gap-1.5',
                  aliasFilter === 'pending' ? 'bg-white text-slate-800 shadow-sm border border-slate-200/10' : 'text-slate-500 hover:text-slate-800'
                ]"
              >
                待匹配
                <span class="px-1.5 py-0.5 rounded-full text-[9px] font-mono" :class="aliasFilter === 'pending' ? 'bg-amber-100 text-amber-700' : 'bg-slate-200 text-slate-500'">
                  {{ aliasCounts.pending }}
                </span>
              </button>
              <button 
                @click="aliasFilter = 'mapped'"
                :class="[
                  'px-3.5 py-1.5 text-[11px] font-extrabold rounded-lg transition-all flex items-center gap-1.5',
                  aliasFilter === 'mapped' ? 'bg-white text-slate-800 shadow-sm border border-slate-200/10' : 'text-slate-500 hover:text-slate-800'
                ]"
              >
                已绑定映射
                <span class="px-1.5 py-0.5 rounded-full text-[9px] font-mono" :class="aliasFilter === 'mapped' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-500'">
                  {{ aliasCounts.mapped }}
                </span>
              </button>
              <button 
                @click="aliasFilter = ''"
                :class="[
                  'px-3.5 py-1.5 text-[11px] font-extrabold rounded-lg transition-all flex items-center gap-1.5',
                  aliasFilter === '' ? 'bg-white text-slate-800 shadow-sm border border-slate-200/10' : 'text-slate-500 hover:text-slate-800'
                ]"
              >
                全部别名
                <span class="px-1.5 py-0.5 rounded-full text-[9px] font-mono" :class="aliasFilter === '' ? 'bg-slate-100 text-slate-700' : 'bg-slate-200 text-slate-500'">
                  {{ aliasCounts.total }}
                </span>
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent class="p-0 flex-1 flex flex-col overflow-hidden min-h-0">
          <!-- Alias Mapping Table -->
          <div class="flex-1 overflow-auto min-h-0 border-t border-slate-100">
            <table class="w-full text-left border-collapse select-none">
              <thead>
                <tr class="sticky top-0 z-10 bg-slate-50 text-slate-400 text-[10px] font-bold uppercase tracking-wider border-b border-slate-200/80 select-none">
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">Excel 中的原始店名</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4">对应标准门店</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4 text-center">状态</th>
                  <th class="sticky top-0 z-10 bg-slate-50 p-4 text-center">更新操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                <tr v-if="paginatedAliases.length === 0">
                  <td colspan="4" class="p-8 text-center text-slate-400 font-medium">
                    <div class="flex flex-col items-center justify-center gap-2">
                      <FolderOpen class="w-8 h-8 text-slate-300" />
                      <span>无需要配置的原始别名记录</span>
                    </div>
                  </td>
                </tr>
                <tr 
                  v-for="a in paginatedAliases" 
                  :key="a.id"
                  class="hover:bg-slate-50/40 transition-colors"
                  :class="{'bg-amber-50/10': a.status === 'pending'}"
                >
                  <td class="p-4 font-bold text-slate-700"><div class="flex items-center gap-1.5 group/copy"><span class="select-text inline-block">{{ a.alias_name?.trim() }}</span><button @click="copyText(a.alias_name, a.id + '-alias')" class="opacity-0 group-hover/copy:opacity-100 transition-opacity p-0.5 text-slate-400 hover:text-blue-600 rounded hover:bg-slate-100 shrink-0 flex items-center gap-1 scale-95" title="点击复制"><Check v-if="copiedId === a.id + '-alias'" class="w-3 h-3 text-emerald-500" /><Copy v-else class="w-3 h-3" /><span v-if="copiedId === a.id + '-alias'" class="text-[9px] text-emerald-500 font-bold">已复制</span></button></div></td>
                  <td class="p-4">
                    <!-- Custom Select component -->
                    <Select
                      :model-value="a.store_id"
                      :options="storeOptions"
                      @update:model-value="openAliasBinding(a, $event)"
                      class="w-full max-w-[250px] h-8"
                    />
                  </td>
                  <td class="p-4 text-center">
                    <span 
                      class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold select-none"
                      :class="a.status === 'mapped' ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'"
                    >
                      <span class="w-1.5 h-1.5 rounded-full" :class="a.status === 'mapped' ? 'bg-emerald-500' : 'bg-amber-500'"></span>
                      <span>{{ a.status === 'mapped' ? '已绑定' : '待财务核认' }}</span>
                    </span>
                  </td>
                  <td class="p-4 text-center select-none">
                    <div class="flex items-center justify-center gap-2">
                      <Button 
                        v-if="a.status === 'pending'"
                        @click="a.store_id && openAliasBinding(a, a.store_id)"
                        size="xs"
                        :disabled="!a.store_id"
                        class="h-7 px-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium inline-flex items-center gap-1"
                      >
                        <CheckCircle2 class="w-3.5 h-3.5" />
                        <span>确认绑定</span>
                      </Button>
                      <span v-else class="text-xs text-slate-400 font-semibold inline-flex items-center gap-1">
                        <CheckCircle2 class="w-3.5 h-3.5 text-emerald-500" />
                        <span>已同步</span>
                      </span>

                      <Button
                        @click="triggerDeleteAlias(a)"
                        size="xs"
                        variant="outline"
                        class="h-7 px-2 border-slate-200 text-slate-500 hover:text-rose-600 hover:border-rose-100 hover:bg-rose-50"
                        title="删除别名绑定"
                      >
                        <Trash2 class="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Aliases Pagination Controls -->
          <div v-if="aliasTotalPages > 1" class="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50/50 text-xs">
            <div class="text-slate-400 font-medium select-none">
              显示第 {{ (aliasCurrentPage - 1) * aliasPageSize + 1 }} 至 {{ Math.min(aliasCurrentPage * aliasPageSize, filteredAliases.length) }} 条，共 {{ filteredAliases.length }} 条
            </div>
            <div class="flex items-center gap-2">
              <Button 
                size="xs" 
                variant="outline" 
                :disabled="aliasCurrentPage === 1" 
                @click="aliasCurrentPage--"
                class="h-7 text-[11px] font-bold border-slate-200/80 hover:bg-slate-50"
              >
                上一页
              </Button>
              <span class="text-slate-600 font-bold px-2 select-none">第 {{ aliasCurrentPage }} / {{ aliasTotalPages }} 页</span>
              <Button 
                size="xs" 
                variant="outline" 
                :disabled="aliasCurrentPage === aliasTotalPages" 
                @click="aliasCurrentPage++"
                class="h-7 text-[11px] font-bold border-slate-200/80 hover:bg-slate-50"
              >
                下一页
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Store Add/Edit Modal Dialog -->
    <Teleport to="body">
      <div 
        v-if="showEditModal" 
        class="fixed inset-0 bg-zinc-950/40 backdrop-blur-sm z-50 flex items-center justify-center p-4 fade-in"
        @click.self="showEditModal = false"
      >
        <Card class="w-full max-w-md shadow-2xl border border-slate-200/80 overflow-hidden bg-white">
          <CardHeader class="bg-slate-50/50 border-b border-slate-200/60 pb-4">
            <div class="flex items-center justify-between">
              <div>
                <CardTitle class="text-base font-bold text-slate-800">
                  {{ formStore.id ? '编辑标准门店信息' : '新增标准门店' }}
                </CardTitle>
                <CardDescription class="text-xs text-slate-400">
                  {{ formStore.id ? '更新标准名录下的门店配置基本资料' : '在名录中录入一家全新的标准门店' }}
                </CardDescription>
              </div>
              <button @click="showEditModal = false" class="text-slate-400 hover:text-slate-600 text-lg font-bold">×</button>
            </div>
          </CardHeader>
          
          <CardContent class="p-6 space-y-4">
            <!-- Store Name -->
            <div class="flex flex-col gap-1.5">
              <label for="store-name" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">标准门店名称 (必填)</label>
              <Input 
                id="store-name"
                v-model="formStore.name" 
                placeholder="例如: 钟祥店"
                class="h-9 text-xs"
                required
              />
            </div>

            <!-- Store Code -->
            <div class="flex flex-col gap-1.5">
              <label for="store-code" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">门店财务编码</label>
              <Input 
                id="store-code"
                v-model="formStore.code" 
                placeholder="例如: MD013"
                class="h-9 text-xs"
              />
            </div>

            <!-- Region -->
            <div class="flex flex-col gap-1.5">
              <label for="store-region" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">所在运营区域</label>
              <Input 
                id="store-region"
                v-model="formStore.region" 
                placeholder="例如: 荆州地区"
                class="h-9 text-xs"
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <!-- Manager -->
              <div class="flex flex-col gap-1.5">
                <label for="store-manager" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">店长负责人</label>
                <Input 
                  id="store-manager"
                  v-model="formStore.manager" 
                  placeholder="店长姓名"
                  class="h-9 text-xs"
                />
              </div>

              <!-- Phone -->
              <div class="flex flex-col gap-1.5">
                <label for="store-phone" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">联系电话</label>
                <Input 
                  id="store-phone"
                  v-model="formStore.phone" 
                  placeholder="手机号码"
                  class="h-9 text-xs"
                />
              </div>
            </div>

            <!-- Active status toggle -->
            <div v-if="formStore.id === null" class="flex items-center gap-2 pt-2">
              <input 
                id="store-active-cb"
                type="checkbox" 
                v-model="formStore.is_active" 
                class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
              />
              <label for="store-active-cb" class="text-xs font-bold text-slate-700 cursor-pointer">
                启用此门店运营状态
              </label>
            </div>
          </CardContent>

          <CardFooter class="bg-slate-50/50 border-t border-slate-200/60 p-4 flex justify-end gap-3">
            <Button 
              @click="showEditModal = false"
              variant="outline"
              size="sm"
              class="h-8 text-xs font-semibold"
            >
              取消
            </Button>
            <Button 
              @click="submitForm"
              size="sm"
              class="h-8 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-md shadow-blue-500/10 flex items-center gap-1.5"
            >
              <Save class="w-3.5 h-3.5" />
              <span>保存门店</span>
            </Button>
          </CardFooter>
        </Card>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="statusStore" class="fixed inset-0 bg-zinc-950/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" @click.self="closeStoreStatusModal">
        <Card class="w-full max-w-md bg-white shadow-2xl">
          <CardHeader>
            <CardTitle class="text-base">{{ statusStore.is_active ? '停用标准门店' : '重新启用标准门店' }}</CardTitle>
            <CardDescription v-if="statusStore.is_active">停用“{{ statusStore.name }}”后，该门店不会参加后续新对账；若当前未关账批次仍有数据，后端会拒绝停用。</CardDescription>
            <CardDescription v-else>重新启用“{{ statusStore.name }}”后，该门店将重新参加后续对账。</CardDescription>
          </CardHeader>
          <CardContent>
            <textarea v-model="storeStatusReason" rows="4" maxlength="500" class="w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-amber-500" :placeholder="statusStore.is_active ? '请输入停用原因，例如：门店已停止营业' : '请输入重新启用原因'"></textarea>
          </CardContent>
          <CardFooter class="justify-end gap-3"><Button variant="outline" @click="closeStoreStatusModal">取消</Button><Button :class="statusStore.is_active ? 'bg-amber-600 text-white hover:bg-amber-700' : 'bg-emerald-600 text-white hover:bg-emerald-700'" :disabled="!storeStatusReason.trim()" @click="submitStoreStatusChange">{{ statusStore.is_active ? '确认停用' : '确认重新启用' }}</Button></CardFooter>
        </Card>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="bindingAlias && bindingStore" class="fixed inset-0 bg-zinc-950/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" @click.self="closeAliasBinding">
        <Card class="w-full max-w-md bg-white shadow-2xl">
          <CardHeader><CardTitle class="text-base">确认门店别名绑定</CardTitle><CardDescription>系统不会自行匹配门店，请核对来源原始名称和标准门店后确认。</CardDescription></CardHeader>
          <CardContent class="space-y-4 text-sm">
            <div class="grid grid-cols-[90px_1fr] gap-2 rounded-xl bg-slate-50 p-4">
              <span class="text-slate-500">原始别名</span><strong>{{ bindingAlias.alias_name }}</strong>
              <span class="text-slate-500">原绑定</span><strong>{{ bindingAlias.store?.name || '尚未绑定' }}</strong>
              <span class="text-slate-500">新绑定</span><strong class="text-blue-700">{{ bindingStore.name }}</strong>
            </div>
            <textarea v-if="isAliasRebind" v-model="aliasBindingReason" rows="4" maxlength="500" class="w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-blue-500" placeholder="重新绑定必须填写原因，例如：原门店选择错误"></textarea>
          </CardContent>
          <CardFooter class="justify-end gap-3"><Button variant="outline" @click="closeAliasBinding">取消</Button><Button :disabled="isAliasRebind && !aliasBindingReason.trim()" @click="submitAliasBinding">确认绑定</Button></CardFooter>
        </Card>
      </div>

      <!-- 别名删除确认弹窗 (高颜值自定义弹窗) -->
      <div v-if="deleteConfirmAlias" class="fixed inset-0 bg-zinc-950/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" @click.self="cancelDeleteAlias">
        <div class="w-full max-w-sm rounded-2xl border border-slate-100 bg-white p-6 shadow-xl animate-in fade-in zoom-in-95 duration-150">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-full bg-rose-50 flex items-center justify-center text-rose-600 shrink-0">
              <Trash2 class="w-5 h-5" />
            </div>
            <h3 class="text-sm font-bold text-slate-800">删除别名</h3>
          </div>
          <p class="text-xs text-slate-500 mb-6 leading-relaxed">
            确定要永久删除原始别名记录 <strong class="text-slate-800">“{{ deleteConfirmAlias.alias_name }}”</strong> 吗？
            <br/><span class="text-rose-600 font-semibold">删除后该记录将不复存在。</span>如果它是数据提取中的无效名称（例如注释或错位行），应当予以清除。下次导入新文件时，若重新识别到该列，会再次提示。
          </p>
          <div class="flex justify-end gap-2 text-xs">
            <Button variant="outline" size="sm" class="h-8 px-4" @click="cancelDeleteAlias">取消</Button>
            <Button size="sm" class="h-8 px-4 bg-rose-600 text-white hover:bg-rose-700 shadow-sm shadow-rose-500/10" @click="confirmDeleteAlias">确认删除</Button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { api } from '../services/api';
import type { Store, StoreAlias } from '../services/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Store as StoreIcon, Link, Plus, CheckCircle2, FolderOpen, Save, Copy, Check, Trash2 } from 'lucide-vue-next';

// Tab state
const activeTab = ref('stores'); // 'stores' or 'aliases'

import { isTourActive, currentStepIndex } from '../services/tour';
watch([isTourActive, currentStepIndex], () => {
  if (isTourActive.value) {
    if (currentStepIndex.value === 2) {
      activeTab.value = 'aliases';
    } else if (currentStepIndex.value === 1) {
      activeTab.value = 'stores';
    }
  }
});

// Data states
const stores = ref<Store[]>([]);
const aliases = ref<StoreAlias[]>([]);

const statusStore = ref<Store | null>(null);
const storeStatusReason = ref('');
const bindingAlias = ref<StoreAlias | null>(null);
const bindingStore = ref<Store | null>(null);
const aliasBindingReason = ref('');

// Alias filtering states
const aliasFilter = ref('pending');

// Search & Pagination states for Standard Stores
const storeSearchQuery = ref('');
const storeCurrentPage = ref(1);
const storePageSize = ref(10);

// Search & Pagination states for Aliases
const aliasSearchQuery = ref('');
const aliasCurrentPage = ref(1);
const aliasPageSize = ref(10);

// Modal Form states
const showEditModal = ref(false);
const formStore = ref({
  id: null as number | null,
  name: '',
  code: '',
  region: '',
  manager: '',
  phone: '',
  is_active: true
});

const copiedId = ref('');
const copyText = async (text: string, id: string) => {
  try {
    await navigator.clipboard.writeText(text);
    copiedId.value = id;
    setTimeout(() => {
      if (copiedId.value === id) {
        copiedId.value = '';
      }
    }, 1500);
  } catch (err) {
    console.error('Failed to copy text: ', err);
  }
};

const aliasCounts = computed(() => {
  const pending = aliases.value.filter(a => a.status === 'pending').length;
  const mapped = aliases.value.filter(a => a.status === 'mapped').length;
  const total = aliases.value.length;
  return { pending, mapped, total };
});

const storeOptions = computed(() => {
  return [
    { value: null, label: '-- 请选择标准店名 (待认领) --' },
    ...stores.value.map(s => ({ value: s.id, label: s.name }))
  ];
});
const isAliasRebind = computed(() => Boolean(
  bindingAlias.value?.store_id
  && bindingStore.value
  && bindingAlias.value.store_id !== bindingStore.value.id,
));

// Standard Stores computed filtered and paginated
const filteredStores = computed(() => {
  if (!storeSearchQuery.value.trim()) return stores.value;
  const q = storeSearchQuery.value.toLowerCase().trim();
  return stores.value.filter(s => 
    s.name.toLowerCase().includes(q) ||
    (s.code && s.code.toLowerCase().includes(q)) ||
    (s.region && s.region.toLowerCase().includes(q)) ||
    (s.manager && s.manager.toLowerCase().includes(q)) ||
    (s.phone && s.phone.toLowerCase().includes(q))
  );
});

const storeTotalPages = computed(() => Math.ceil(filteredStores.value.length / storePageSize.value) || 1);

const paginatedStores = computed(() => {
  const start = (storeCurrentPage.value - 1) * storePageSize.value;
  const end = start + storePageSize.value;
  return filteredStores.value.slice(start, end);
});

// Watch standard store search query
watch(storeSearchQuery, () => {
  storeCurrentPage.value = 1;
});

// Store Aliases computed filtered and paginated
const filteredAliases = computed(() => {
  let list = aliases.value;
  
  if (aliasFilter.value === 'pending') {
    list = list.filter(a => a.status === 'pending');
  } else if (aliasFilter.value === 'mapped') {
    list = list.filter(a => a.status === 'mapped');
  }
  
  if (aliasSearchQuery.value.trim()) {
    const q = aliasSearchQuery.value.toLowerCase().trim();
    list = list.filter(a => a.alias_name.toLowerCase().includes(q));
  }
  
  return list;
});

const aliasTotalPages = computed(() => Math.ceil(filteredAliases.value.length / aliasPageSize.value) || 1);

const paginatedAliases = computed(() => {
  const start = (aliasCurrentPage.value - 1) * aliasPageSize.value;
  const end = start + aliasPageSize.value;
  return filteredAliases.value.slice(start, end);
});

// Watch alias search query or status filters
watch(aliasSearchQuery, () => {
  aliasCurrentPage.value = 1;
});

watch(aliasFilter, () => {
  aliasCurrentPage.value = 1;
});

const fetchStores = async () => {
  try {
    stores.value = await api.getStores();
  } catch (error) {
    console.error('Failed to load stores:', error);
  }
};

const fetchAliases = async () => {
  try {
    aliases.value = await api.getStoreAliases(undefined);
  } catch (error) {
    console.error('Failed to load aliases:', error);
  }
};

const openAddModal = () => {
  formStore.value = {
    id: null,
    name: '',
    code: '',
    region: '',
    manager: '',
    phone: '',
    is_active: true
  };
  showEditModal.value = true;
};

const openEditModal = (store: Store) => {
  formStore.value = {
    id: store.id,
    name: store.name,
    code: store.code || '',
    region: store.region || '',
    manager: store.manager || '',
    phone: store.phone || '',
    is_active: store.is_active
  };
  showEditModal.value = true;
};

const submitForm = async () => {
  if (!formStore.value.name.trim()) {
    alert('请输入门店名称！');
    return;
  }
  
  const payload = {
    name: formStore.value.name.trim(),
    code: formStore.value.code.trim() || undefined,
    region: formStore.value.region.trim() || undefined,
    manager: formStore.value.manager.trim() || undefined,
    phone: formStore.value.phone.trim() || undefined,
    ...(formStore.value.id === null ? { is_active: formStore.value.is_active } : {})
  };

  try {
    if (formStore.value.id === null) {
      await api.createStore(payload);
    } else {
      await api.updateStore(formStore.value.id, payload);
    }
    showEditModal.value = false;
    fetchStores();
    fetchAliases();
  } catch (err: any) {
    alert(err.response?.data?.detail || '保存门店失败！');
  }
};

const openStoreStatusModal = (store: Store) => {
  statusStore.value = store;
  storeStatusReason.value = '';
};

const closeStoreStatusModal = () => {
  statusStore.value = null;
  storeStatusReason.value = '';
};

const submitStoreStatusChange = async () => {
  if (!statusStore.value || !storeStatusReason.value.trim()) return;
  try {
    await api.updateStore(statusStore.value.id, {
      is_active: !statusStore.value.is_active,
      status_change_reason: storeStatusReason.value.trim(),
    });
    closeStoreStatusModal();
    await fetchStores();
    fetchAliases();
  } catch (error: any) {
    alert(error.response?.data?.detail || '修改门店状态失败！');
  }
};

const openAliasBinding = (alias: StoreAlias, storeId: number | null) => {
  if (storeId === null) {
    alert('请先选择明确的标准门店，系统不会自动匹配。');
    return;
  }
  const store = stores.value.find((item) => item.id === Number(storeId));
  if (!store) return;
  bindingAlias.value = alias;
  bindingStore.value = store;
  aliasBindingReason.value = '';
};

const closeAliasBinding = () => {
  bindingAlias.value = null;
  bindingStore.value = null;
  aliasBindingReason.value = '';
};

const submitAliasBinding = async () => {
  if (!bindingAlias.value || !bindingStore.value) return;
  if (isAliasRebind.value && !aliasBindingReason.value.trim()) return;
  try {
    await api.updateStoreAlias(bindingAlias.value.id, {
      store_id: bindingStore.value.id,
      reason: aliasBindingReason.value.trim() || undefined,
    });
    closeAliasBinding();
    await fetchAliases();
  } catch (error: any) {
    alert(error.response?.data?.detail || '绑定别名失败！');
  }
};

const deleteConfirmAlias = ref<StoreAlias | null>(null);

const triggerDeleteAlias = (alias: StoreAlias) => {
  deleteConfirmAlias.value = alias;
};

const cancelDeleteAlias = () => {
  deleteConfirmAlias.value = null;
};

const confirmDeleteAlias = async () => {
  if (!deleteConfirmAlias.value) return;
  try {
    await api.deleteStoreAlias(deleteConfirmAlias.value.id);
    deleteConfirmAlias.value = null;
    await fetchAliases();
  } catch (error: any) {
    alert(error.response?.data?.detail || '删除别名失败！');
  }
};

onMounted(() => {
  fetchStores();
  fetchAliases();
});
</script>
