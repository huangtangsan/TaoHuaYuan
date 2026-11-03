<script setup lang="ts">
import { onMounted } from 'vue'

onMounted(() => {
  document.title = '页面没有找到 · 桃花源'
})
</script>

<template>
  <div class="not-found-page">
    <div class="not-found-art" aria-hidden="true">
      <span>4</span>
      <span class="zero">0</span>
      <span>4</span>
    </div>
    <p class="eyebrow">LOST IN THE PEACH BLOSSOM FOREST</p>
    <h1>这条小路走到尽头了</h1>
    <p class="not-found-hint">页面可能已经搬家，或者你输入了一个不存在的地址。</p>
    <div class="not-found-actions">
      <router-link to="/" class="primary-button">回到首页</router-link>
      <router-link to="/about" class="secondary-button">看看关于页</router-link>
    </div>
  </div>
</template>
