import { createRouter, createWebHistory } from "vue-router"
import Dashboard from "../pages/dashboard.vue"

const routes = [
  { path: "/", redirect: "/dashboard/overview" },
  { path: "/dashboard/:tab?", name: "dashboard", component: Dashboard },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
