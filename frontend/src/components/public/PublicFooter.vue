<script setup lang="ts">
const props = defineProps<{ record?: string; recordUrl?: string }>()
const year = new Date().getFullYear()

function backToTop(): void {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <footer class="site-footer">
    <div class="footer-inner">
      <p>
        © {{ year }} 桃花源 · 网址导航
        <span class="footer-sep">/</span>
        Powered by Vue 3 + FastAPI
      </p>
      <p v-if="props.record" class="footer-record">
        <a v-if="props.recordUrl" :href="props.recordUrl" target="_blank" rel="noopener noreferrer">
          {{ props.record }}
        </a>
        <span v-else>{{ props.record }}</span>
      </p>
      <button class="to-top" type="button" @click="backToTop">回到顶部 ↑</button>
    </div>
  </footer>
</template>
