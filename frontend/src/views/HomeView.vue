<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchHome, type HomeData, type PublicCategory, type PublicSite } from '@/api/public'
import PublicFooter from '@/components/public/PublicFooter.vue'
import SiteCard from '@/components/public/SiteCard.vue'
import { applySiteMeta } from '@/utils/meta'
import { imgSrc } from '@/utils/img'

interface DisplaySection {
  category: PublicCategory
  parent?: PublicCategory
  sites: PublicSite[]
}

const data = ref<HomeData | null>(null)
const loading = ref(true)
const failed = ref(false)
const keyword = ref('')
const sidebarOpen = ref(false)
const activeCategory = ref<number | null>(null)

const config = computed(() => data.value?.config)
const categories = computed(() => data.value?.categories ?? [])
const sites = computed(() => data.value?.sites ?? [])
const siteCount = computed(() => sites.value.length)

const categoryMap = computed(() => new Map(categories.value.map((item) => [item.id, item])))

function matches(site: PublicSite): boolean {
  const term = keyword.value.trim().toLowerCase()
  if (!term) return true
  return [site.title, site.description, site.url].some((value) =>
    value.toLowerCase().includes(term),
  )
}

const filteredByCategory = computed(() => {
  const result = new Map<number, PublicSite[]>()
  for (const site of sites.value) {
    if (!matches(site)) continue
    const list = result.get(site.category_id) ?? []
    list.push(site)
    result.set(site.category_id, list)
  }
  return result
})

const sections = computed<DisplaySection[]>(() =>
  categories.value
    .filter((category) => (filteredByCategory.value.get(category.id)?.length ?? 0) > 0)
    .map((category) => ({
      category,
      parent:
        category.parent_id !== 0 ? categoryMap.value.get(category.parent_id) : undefined,
      sites: filteredByCategory.value.get(category.id) ?? [],
    })),
)

const visibleSectionIds = computed(() => new Set(sections.value.map((item) => item.category.id)))

const navGroups = computed(() =>
  categories.value
    .filter((item) => item.parent_id === 0)
    .map((root) => ({
      root,
      selfVisible: visibleSectionIds.value.has(root.id),
      children: categories.value.filter(
        (child) => child.parent_id === root.id && visibleSectionIds.value.has(child.id),
      ),
    }))
    .filter((group) => group.selfVisible || group.children.length > 0),
)

const displayedCount = computed(() =>
  sections.value.reduce((total, section) => total + section.sites.length, 0),
)

const logo = computed(
  () => imgSrc(config.value?.site_logo ?? '') || '/assets/images/logo@2x.png',
)

function scrollToCategory(categoryId: number): void {
  activeCategory.value = categoryId
  sidebarOpen.value = false
  const element = document.getElementById(`category-${categoryId}`)
  element?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function onImageError(event: Event): void {
  const image = event.target as HTMLImageElement
  image.src = '/assets/images/logo@2x.png'
}

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    data.value = await fetchHome()
    applySiteMeta(data.value.config)
    activeCategory.value = sections.value[0]?.category.id ?? null
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="public-page">
    <div v-if="sidebarOpen" class="sidebar-scrim" @click="sidebarOpen = false" />

    <aside class="site-sidebar" :class="{ 'is-open': sidebarOpen }">
      <div class="sidebar-brand">
        <router-link to="/" class="brand-link" aria-label="返回首页">
          <img :src="logo" alt="桃花源" class="brand-logo" @error="onImageError" />
        </router-link>
      </div>

      <nav class="sidebar-nav" aria-label="站点分类">
        <div v-for="group in navGroups" :key="group.root.id" class="nav-group">
          <button
            v-if="group.selfVisible"
            type="button"
            class="nav-item"
            :class="{ active: activeCategory === group.root.id }"
            @click="scrollToCategory(group.root.id)"
          >
            <i :class="group.root.icon || 'linecons-folder'" />
            <span>{{ group.root.name }}</span>
            <span class="nav-count">{{ filteredByCategory.get(group.root.id)?.length ?? 0 }}</span>
          </button>
          <div v-else class="nav-section-label">
            <i :class="group.root.icon || 'linecons-folder'" />
            <span>{{ group.root.name }}</span>
          </div>

          <div v-if="group.children.length" class="nav-children">
            <button
              v-for="child in group.children"
              :key="child.id"
              type="button"
              class="nav-child"
              :class="{ active: activeCategory === child.id }"
              @click="scrollToCategory(child.id)"
            >
              <span class="nav-dash" />
              <span>{{ child.name }}</span>
              <span class="nav-count">{{ filteredByCategory.get(child.id)?.length ?? 0 }}</span>
            </button>
          </div>
        </div>

        <div v-if="!navGroups.length && !loading" class="nav-empty">暂无可用分类</div>

        <div class="nav-divider" />
        <router-link v-if="config?.is_about" to="/about" class="nav-item nav-quiet">
          <i class="linecons-heart" />
          <span>关于本站</span>
        </router-link>
        <router-link to="/password" class="nav-item nav-quiet">
          <i class="linecons-lock" />
          <span>不足为外人道也</span>
        </router-link>
      </nav>

      <div class="sidebar-foot">
        <span class="status-dot" />
        <span>{{ siteCount }} 个站点已收录</span>
      </div>
    </aside>

    <main class="public-main">
      <header class="public-toolbar">
        <div class="toolbar-left">
          <button
            class="icon-button menu-button"
            type="button"
            aria-label="打开分类菜单"
            @click="sidebarOpen = true"
          >
            <span class="hamburger" />
          </button>
          <div class="page-heading">
            <span class="eyebrow">TAO HUA YUAN</span>
            <h1>{{ config?.site_title || '桃花源 · 网址导航' }}</h1>
          </div>
        </div>

        <div class="toolbar-right">
          <div v-if="config?.is_search" class="site-search">
            <span class="search-glyph">⌕</span>
            <input v-model="keyword" type="search" placeholder="搜索已收录的网站…" />
            <button v-if="keyword" type="button" class="search-clear" @click="keyword = ''">×</button>
          </div>
          <router-link v-if="config?.is_about" to="/about" class="toolbar-link">关于</router-link>
          <router-link to="/admin" class="toolbar-link toolbar-admin">管理后台</router-link>
        </div>
      </header>

      <div class="main-body">
        <p v-if="config?.site_desc" class="site-intro">{{ config.site_desc }}</p>

        <div v-if="loading" class="content-state">
          <div v-for="index in 6" :key="index" class="skeleton-card" />
        </div>

        <div v-else-if="failed" class="content-state state-panel">
          <p class="state-title">站点数据没能加载出来</p>
          <p class="state-hint">检查后端是否已经启动，然后重试。</p>
          <button class="primary-button" type="button" @click="load">重新加载</button>
        </div>

        <div v-else-if="!sections.length" class="content-state state-panel">
          <p class="state-title">{{ keyword ? '没有匹配的站点' : '还没有配置站点' }}</p>
          <p class="state-hint">
            {{ keyword ? '换一个关键词，或者清空搜索。' : '去管理后台添加分类与网站。' }}
          </p>
          <button v-if="keyword" class="primary-button" type="button" @click="keyword = ''">
            清空搜索
          </button>
          <router-link v-else to="/admin" class="primary-button">打开管理后台</router-link>
        </div>

        <template v-else>
          <div class="result-line">
            <span v-if="keyword">“{{ keyword }}” 找到 {{ displayedCount }} 个站点</span>
            <span v-else>慢慢挑，不着急。共 {{ siteCount }} 个入口。</span>
          </div>

          <section
            v-for="section in sections"
            :id="`category-${section.category.id}`"
            :key="section.category.id"
            class="site-section"
          >
            <div class="section-heading">
              <div class="section-title-wrap">
                <span class="section-icon"><i :class="section.category.icon || 'linecons-tag'" /></span>
                <div>
                  <p v-if="section.parent" class="section-parent">{{ section.parent.name }}</p>
                  <h2>{{ section.category.name }}</h2>
                </div>
              </div>
              <span class="section-count">{{ section.sites.length }}</span>
            </div>

            <div class="site-grid">
              <SiteCard v-for="site in section.sites" :key="site.id" :site="site" />
            </div>
          </section>
        </template>

        <PublicFooter :record="config?.site_record" :record-url="config?.site_url" />
      </div>
    </main>
  </div>
</template>
