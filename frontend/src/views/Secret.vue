<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchHome } from '@/api/public'
import PublicFooter from '@/components/public/PublicFooter.vue'
import { applySiteMeta } from '@/utils/meta'

const record = ref('')
const recordUrl = ref('')

const cards = [
  {
    title: 'I Miss you',
    caption: '初极狭，才通人',
    url: 'https://go.huangtang.link/',
  },
  {
    title: 'I Love You',
    caption: '复行数十步',
    url: 'https://2570527.xyz/',
  },
  {
    title: 'You are my sunshine girl',
    caption: '豁然开朗',
    url: 'https://go.huangtang.link/admin/dashboard',
  },
]

onMounted(async () => {
  try {
    const home = await fetchHome()
    record.value = home.config.site_record
    recordUrl.value = home.config.site_url
    applySiteMeta(home.config)
  } catch {
    // This page intentionally stays quiet when the backend is unavailable.
  }
})
</script>

<template>
  <div class="password-page">
    <header class="about-topbar">
      <router-link to="/" class="about-brand" aria-label="返回首页">
        <img src="/assets/images/logo_dark@2x.png" alt="桃花源" />
      </router-link>
      <nav class="about-nav">
        <router-link to="/">网站导航</router-link>
        <router-link to="/about">关于本站</router-link>
      </nav>
    </header>

    <main class="password-main">
      <p class="eyebrow">A QUIET CORNER</p>
      <h1>初极狭，才通人，复行数十步，豁然开朗</h1>

      <div class="password-grid">
        <a
          v-for="card in cards"
          :key="card.title"
          class="password-card"
          :href="card.url"
          target="_blank"
          rel="noopener noreferrer"
        >
          <span class="password-caption">{{ card.caption }}</span>
          <strong>{{ card.title }}</strong>
          <span class="password-arrow">↗</span>
        </a>
      </div>

      <PublicFooter :record="record" :record-url="recordUrl" />
    </main>
  </div>
</template>
