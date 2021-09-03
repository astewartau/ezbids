import { createApp } from 'vue'

import VueGtag from 'vue-gtag-next'

import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { library } from "@fortawesome/fontawesome-svg-core"
import { faGithub } from "@fortawesome/free-brands-svg-icons"
library.add(faGithub);

import store from './store'

//move to ./types?
//tell typescript about some global properties we are adding
declare module '@vue/runtime-core' {
    export interface ComponentCustomProperties {
      //$http: typeof axios
      $validate: (data: object, rule: object) => boolean
      $store: typeof store
    }
}

const app = createApp(App);
app.use(store)
app.use(ElementPlus)
app.use(VueGtag, {
    property: {
      id: "UA-118407195-1"
    }
});

app.component("font-awesome-icon", FontAwesomeIcon)
app.mount('#app')
