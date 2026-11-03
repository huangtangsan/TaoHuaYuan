<script setup lang="ts">
import { computed } from 'vue'

import type { PublicSite } from '@/api/public'
import { imgSrc } from '@/utils/img'

const props = defineProps<{ site: PublicSite }>()

const icon = computed(() => imgSrc(props.site.icon) || '/assets/images/default-site.svg')

function onImageError(event: Event): void {
  const image = event.target as HTMLImageElement
  if (!image.src.endsWith('/assets/images/default-site.svg')) {
    image.src = '/assets/images/default-site.svg'
  }
}
</script>

<template>
  <a
    class="site-card"
    :href="site.url"
    target="_blank"
    rel="noopener noreferrer"
    :title="site.description || site.title"
  >
    <span class="site-icon-wrap">
      <img :src="icon" class="site-icon" alt="" loading="lazy" @error="onImageError" />
    </span>
    <span class="site-copy">
      <strong class="site-title">{{ site.title }}</strong>
      <span class="site-desc">{{ site.description || '暂时没有简介' }}</span>
    </span>
    <span class="site-arrow" aria-hidden="true">↗</span>
  </a>
</template>
