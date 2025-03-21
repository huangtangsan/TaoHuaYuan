import './assets/css/fonts/linecons/css/linecons.css'
import './assets/css/fonts/fontawesome/css/font-awesome.min.css'
import './assets/css/bootstrap.css'
import './assets/css/xenon-core.css'
import './assets/css/xenon-components.css'
import './assets/css/xenon-skins.css'
import './assets/css/nav.css'

import router from './router'
import App from './App.vue'
import VueSmoothScroll from 'vue3-smooth-scroll';

import { createApp } from 'vue'

const app = createApp(App)

app.use(router)
app.use(VueSmoothScroll, {
    duration: 0, // 滚动持续时间，单位为毫秒
    offset: -20,   // 滚动偏移量，单位为像素
    easing: 'easeInOutCubic' // 滚动动画效果
  });

app.mount('#app')

