<template>
  <div class="boxed-container">
    <nav class="navbar horizontal-menu navbar-fixed-top">
      <div class="navbar-inner">
        <div class="navbar-brand">
          <router-link to="/" class="logo">
            <img src="../assets/images/logo_dark@2x.png" width="100%" alt="" class="hidden-xs">
            <img src="../assets/images/logo@2x.png" width="100%" alt="" class="visible-xs">
          </router-link>
        </div>
        <div class="navbar-mobile-clear"></div>
      </div>
    </nav>

    <div class="page-container">
      <div class="main-content" style="">
        <div class="row">
          <div class="col-md-12">
            <div class="panel panel-default">
              <div class="panel-body">
                <div class="row">
                  <h3 style="text-align: center">初极狭，才通人，复行数十步，豁然开朗</h3>
                  <div class="col-sm-4">
                    <div class="xe-widget xe-conversations box2 label-info"
                         onclick="window.open('http://url.huangtang.link/', '_blank')"
                         data-toggle="tooltip"
                         data-placement="bottom"
                         title=""
                         data-original-title="http://url.huangtang.link/">
                      <div class="xe-comment-entry">
                        <div class="xe-comment">
                          <a href="#" class="xe-user-name overflowClip_1">
                            <img alt="今日诗词" src="https://v2.jinrishici.com/one.svg" style="max-width:100%; display: block; margin: 0 auto;">
                             </a>
                             <p class="overflowClip_2"> I Miss you </p>
                          
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="col-sm-4">
                  <div class="xe-widget xe-conversations box2 label-info"
                       onclick="window.open('http://sss.huangtang.link/', '_blank')"
                       data-toggle="tooltip"
                       data-placement="bottom"
                       title=""
                       data-original-title="http://sss.huangtang.link/">
                    <div class="xe-comment-entry">
                      <div class="xe-comment">
                        <a href="#" class="xe-user-name overflowClip_1">
                          <img alt="今日诗词" src="https://v2.jinrishici.com/one.svg" style="max-width:100%; display: block; margin: 0 auto;">
                        </a>
                        <p class="overflowClip_2"> I Love You </p>
                      </div>
                    </div>
                  </div>
                </div>
                  <div class="col-sm-4">
                    <div class="xe-widget xe-conversations box2 label-info"
                         onclick="window.open('http://go.huangtang.link/', '_blank')"
                         data-toggle="tooltip"
                         data-placement="bottom"
                         title=""
                         data-original-title="http://go.huangtang.link/">
                      <div class="xe-comment-entry">
                        <div class="xe-comment">
                          <a href="#" class="xe-user-name overflowClip_1">
                            <img alt="今日诗词" src="https://v2.jinrishici.com/one.svg" style="max-width:100%; display: block; margin: 0 auto;">
                            </a>
                            <p class="overflowClip_2">You are my sunshine girl</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <Footer/>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

import Footer from './Footer.vue'
let authorImg:string= './assets/images/logos/viggoz.png';

const token = 'L+t60OK7GFFoWFbADuC7bnzm+Uikaz0B';
// const getImg = async () => {
//   try {
//     let res = await fetch('https://v2.jinrishici.com/sentence', {
//       headers: {
//         'X-User-Token': token
//       }
//     });
//     if (!res.ok) {
//       throw new Error('Network response was not ok');
//     }
//     let data = await res.json();
//     console.log(data.data.content);
//     return data.data.content; // 假设 API 返回的数据中有一个 data 字段
//   } catch (error) {
//     console.error('获取图片失败:', error);
//     return null;
//   }
// }

let img1 = ref(null);
let img2 = ref(null);
let img3 = ref(null);


</script>


<style>

</style>