import { createRouter, createWebHistory } from 'vue-router';
import { getSession } from '../services/api';

const Dashboard = () => import('../views/Dashboard.vue');
const ImportCenter = () => import('../views/ImportCenter.vue');
const ReconciliationList = () => import('../views/ReconciliationList.vue');
const MappingSettings = () => import('../views/MappingSettings.vue');
const StoreSettings = () => import('../views/StoreSettings.vue');
const Login = () => import('../views/Login.vue');

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
    meta: { requiresAdmin: true },
  },
  {
    path: '/settings/stores',
    name: 'StoreSettings',
    component: StoreSettings,
    meta: { requiresAdmin: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const isAuthenticated = !!getSession().token;
  if (to.name !== 'Login' && !isAuthenticated) {
    next({ name: 'Login' });
  } else if (to.name === 'Login' && isAuthenticated) {
    next({ name: 'Dashboard' });
  } else if (to.meta.requiresAdmin && getSession().role !== 'admin') {
    next({ name: 'Dashboard' });
  } else {
    next();
  }
});

export default router;
