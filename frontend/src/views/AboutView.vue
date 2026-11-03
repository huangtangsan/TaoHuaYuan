<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, onMounted, ref } from 'vue'

import { fetchAbout, fetchHome, type AboutData } from '@/api/public'
import PublicFooter from '@/components/public/PublicFooter.vue'
import { imgSrc } from '@/utils/img'
import { applySiteMeta } from '@/utils/meta'

const about = ref<AboutData | null>(null)
const loading = ref(true)
const failed = ref(false)
const record = ref('')
const recordUrl = ref('')

const logo = computed(
  () => imgSrc(about.value?.site_logo ?? '') || '/assets/images/logo_dark@2x.png',
)

const siteHtml = computed(() => renderMarkdown(about.value?.about_site ?? ''))
const authorHtml = computed(() => renderMarkdown(about.value?.about_author ?? ''))

function renderMarkdown(source: string): string {
  if (!source) return ''
  return DOMPurify.sanitize(marked.parse(source, { async: false }) as string)
}

function onImageError(event: Event): void {
  const image = event.target as HTMLImageElement
  image.src = '/assets/images/logo_dark@2x.png'
}

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const [aboutData, homeData] = await Promise.all([fetchAbout(), fetchHome()])
    about.value = aboutData
    record.value = homeData.config.site_record
    recordUrl.value = homeData.config.site_url
    applySiteMeta(homeData.config)
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="about-page">
    <header class="about-topbar">
      <router-link to="/" class="about-brand" aria-label="返回首页">
        <img :src="logo" alt="桃花源" @error="onImageError" />
      </router-link>
      <nav class="about-nav">
        <router-link to="/">网站导航</router-link>
        <router-link to="/admin">管理后台</router-link>
      </nav>
    </header>

    <main class="about-main">
      <div class="about-hero">
        <span class="eyebrow">ABOUT THIS PLACE</span>
        <h1>缘溪行，忘路之远近</h1>
        <p>一个自己用的网址收藏夹，也欢迎你偶尔来坐坐。</p>
      </div>

      <div v-if="loading" class="about-loading">
        <div class="skeleton-card" />
        <div class="skeleton-card" />
      </div>

      <div v-else-if="failed" class="content-state state-panel">
        <p class="state-title">关于页面没能加载出来</p>
        <p class="state-hint">检查后端是否已经启动，然后重试。</p>
        <button class="primary-button" type="button" @click="load">重新加载</button>
      </div>

      <div v-else class="about-grid">
        <article class="about-panel">
          <span class="panel-index">01</span>
          <h2>关于本站</h2>
          <div class="markdown-body" v-html="siteHtml" />
          <p v-if="!siteHtml" class="panel-empty">站长还没有写介绍。</p>
        </article>

        <article class="about-panel">
          <span class="panel-index">02</span>
          <h2>关于站长</h2>
          <div class="markdown-body" v-html="authorHtml" />
          <p v-if="!authorHtml" class="panel-empty">站长还没有留下自我介绍。</p>
        </article>
      </div>

      <PublicFooter :record="record" :record-url="recordUrl" />
    </main>
  </div>
</template>
