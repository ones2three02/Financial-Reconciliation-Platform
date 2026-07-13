import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '../views/Dashboard.vue';
import ImportCenter from '../views/ImportCenter.vue';
import ReconciliationList from '../views/ReconciliationList.vue';
import MappingSettings from '../views/MappingSettings.vue';
import StoreSettings from '../views/StoreSettings.vue';

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
  },
  {
    path: '/import',
    name: 'ImportCenter',
    component: ImportCenter,
  },
  {
    path: '/reconciliation',
    name: 'ReconciliationList',
    component: ReconciliationList,
  },
  {
    path: '/settings/mappings',
    name: 'MappingSettings',
    component: MappingSettings,
  },
  {
    path: '/settings/stores',
    name: 'StoreSettings',
    component: StoreSettings,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
