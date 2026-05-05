import { createRouter, createWebHashHistory } from 'vue-router'
import routes from './routes'

export default createRouter({
  scrollBehavior: () => ({ left: 0, top: 0 }),
  routes,
  history: createWebHashHistory(process.env.VUE_ROUTER_BASE),
})
