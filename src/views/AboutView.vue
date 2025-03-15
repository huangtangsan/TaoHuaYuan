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
        <a href="https://github.com/Anjaxs/WebStack-vue" target="_blank">
           <h2>本站基于WebStack-vue构建，使用Vue3和TS重写。</h2>
        </a>
      </div>
    </nav>

    <div class="page-container">
      <div class="main-content" style="">
        <div class="row">
          <div class="col-md-12">
            <div class="panel panel-default">
              <!-- 关于网站 -->
              <h4 class="text-gray">关于本网站</h4>
              <div class="panel-body">
                <div class="row">
                  <div class="col-sm-12">
                    <blockquote>
                      <p>huangtang专用网络收藏夹</p>
                      <br />
                      <p> 吼吼（ ~_~ ）哈哈</p>
                      <br />
                      <em>wechatID:    bXlodWFuZ3Rhbmc=</em>
                    </blockquote>
                  </div>
                </div>
                <!-- 关于站长 -->
                <h4 class="text-gray">关于开源作者</h4>
                <div class="row">
                  <div class="col-sm-4">
                    <div class="xe-widget xe-conversations box2 label-info"
                         onclick="window.open('http://www.viggoz.com/', '_blank')"
                         data-toggle="tooltip"
                         data-placement="bottom"
                         title=""
                         data-original-title="http://www.viggoz.com/">
                      <div class="xe-comment-entry">
                        <a class="xe-user-img">
                          <img :src="authorImg" class="img-circle" width="40">
                        </a>
                        <div class="xe-comment">
                          <a href="#" class="xe-user-name overflowClip_1">
                            <strong>Designer. Viggo.</strong>
                          </a>
                          <p class="overflowClip_2"> Full-time UI designer with an enduring interest in Coding.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="col-md-8">
                    <div class="row">
                      <div class="col-sm-12">
                        <br />
                        <blockquote>
                          <p>
                            这是一个公益项目，而且是<a href="https://github.com/WebStackPage/WebStackPage.github.io"> 开源 </a>
                            <iframe src="https://ghbtns.com/github-btn.html?user=WebStackPage&repo=WebStackPage.github.io&type=star&count=true"
                                    frameborder="0" scrolling="0" width="100px" height="20px"></iframe> 的。你也可以拿来制作自己的网址导航。如果你有更好的想法，可以通过个人网站
                            <a href="http://www.viggoz.com">
                              <span class="label label-info" data-toggle="tooltip"
                                    data-placement="left" title=""
                                    data-original-title="Hello I am a Tooltip">viggoz.com</span>
                            </a>中的联系方式找到我，欢迎与我交流分享。
                          </p>
                        </blockquote>
                      </div>
                    </div>
                    <br>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <Footer />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Footer from '../components/Footer.vue'
const authorImg: string =  '../assets/images/logos/viggoz.png'
</script>

<style>
</style>
