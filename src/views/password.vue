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
                  <h3 style="text-align: center">好湿好湿</h3>
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
                            <strong><img src="https://v2.jinrishici.com/one.svg" data-origin="https://v2.jinrishici.com/one.svg" alt="今日诗词"></strong>
                          </a>
                          <p class="overflowClip_2"> no one know my heart</p>
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
                          <strong><img src="https://v2.jinrishici.com/one.svg" data-origin="https://v2.jinrishici.com/one.svg" alt="今日诗词"></strong>
                        </a>
                        <p class="overflowClip_2"> no one know my heart</p>
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
                            <strong><img src="https://v2.jinrishici.com/one.svg" data-origin="https://v2.jinrishici.com/one.svg" alt="今日诗词"></strong>
                          </a>
                          <p class="overflowClip_2"> no one know my heart</p>
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

<script>
import Footer from '../components/Footer.vue'

export default {
  name: "passoword",
  components: {
    Footer
  },
  data() {
    return {
      authorImg: './assets/images/logos/viggoz.png'
    }
  },
  myFunction()
  {
    var x;
    var person = prompt("请输入你的名字", "Harry Potter");
    if (person != null && person != "") {
      x = "你好 " + person + "! 今天感觉如何?";
      document.getElementById("demo").innerHTML = x;
    }
  }
}

</script>


<style>

</style>