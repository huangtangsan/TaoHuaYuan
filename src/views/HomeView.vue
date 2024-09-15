<template>
  <div class="page-container">
    <div class="sidebar-menu toggle-others fixed">
      <div class="sidebar-menu-inner">
        <header class="logo-env">
          <!-- logo -->
          <div class="logo">
            <a href="javascript:void(0)" class="logo-expanded">
              <img src="../assets/images/logo@2x.png" width="100%" alt="" />
            </a>
            <a href="javascript:void(0)" class="logo-collapsed">
              <img src="../assets/images/logo-collapsed@2x.png" width="40" alt="" />
            </a>
          </div>
          <div class="mobile-menu-toggle visible-xs">
            <a href="javascript:void(0)" data-toggle="user-info-menu">
              <i class="linecons-cog"></i>
            </a>
            <a href="javascript:void(0)" data-toggle="mobile-menu" @click="toggleMainMenu">
              <i class="fa-bars"></i>
            </a>
          </div>
        </header>
        <!-- 侧边栏 -->
        <ul id="main-menu" class="main-menu" :class="{ 'mobile-is-visible': state.showMainMenu }">
          <li v-for="(menu, idx) in items" :key="idx">
            <a :href="'#' + menu.en_name" v-smooth-scroll>
              <i :class="menu.icon"></i>
              <span class="title">{{ menu.name }}</span>
            </a>
            <ul v-if="menu.children">
              <li v-for="(submenu, idx) in menu.children" :key="idx">
                <a :href="'#' + submenu.name" v-smooth-scroll>
                  <span class="title">{{ submenu.name }}</span>
                  <!-- <span v-show="submenu.is_hot" class="label label-pink pull-right hidden-collapsed">Hot</span> -->
                </a>
              </li>
            </ul>
          </li>
          <!-- 关于本站 -->
          <li class="submit-tag">
            <router-link to="/about">
              <i class="linecons-heart"></i>
              <span class="tooltip-blue">关于本站</span>
              <span class="label label-Primary pull-right hidden-collapsed">♥︎</span>
            </router-link>
          </li>
          <!-- 初极狭，才通人，复行数十步，豁然开朗 -->
          <li class="submit-tag">
            <router-link to="/password">
              <i class="linecons-lock"></i>
              <span class="tooltip-blue">不足为外人道也</span>
              <span class="label label-Primary pull-right hidden-collapsed">♥︎</span>
            </router-link>
          </li>
        </ul>
      </div>
    </div>

    <div class="main-content">
      <nav class="navbar user-info-navbar" role="navigation">
        <ul class="user-info-menu left-links list-inline list-unstyled">
          <li class="hidden-sm hidden-xs">
            <a href="javascript:void(0)" data-toggle="sidebar"><i class="fa-bars"></i></a>
            <ul class="dropdown-menu languages">
              <li :class="{active: langItem.key === langList[0].key}" v-for="langItem in langList" :key="langItem.key">
                <a href="javascript:void(0)" @click="lang = langItem">
                  <img :src="langItem.flag" /> {{ langItem.name }}
                </a>
              </li>
            </ul>
          </li>
        </ul>

        <ul class="user-info-menu right-links list-inline list-unstyled">
          <li class="hidden-sm hidden-xs">
            <a href="https://github.com/Anjaxs/WebStack-vue" target="_blank">
              <i class="fa-github"></i> GitHub
            </a>
          </li>
        </ul>
      </nav>

      <div v-for="(item, idx) in items" :key="idx">
        <div :id="item.en_name" v-if="item.web">
          <WebItem :item="item" />
        </div>
        <div :id="item.en_name" v-else v-for="(subItem, idx) in item.children" :key="idx">
          <WebItem :item="subItem" />
        </div>
      </div>

      <Footer></Footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import WebItem from "../components/WebItem.vue";
import Footer from "../components/Footer.vue";
// import Password from "../components/Password.vue";
import itemsData from "../assets/data.json";
import { reactive } from "vue";

const state = reactive({ 
  showMainMenu: false,
});
const toggleMainMenu = () => {
  state.showMainMenu = !state.showMainMenu;
};
let items = itemsData
let lang = {}
let langList =[{key: 'zh', name: '简体中文', flag: './assets/images/flags/flag-cn.png'}]


</script>

<style></style>
