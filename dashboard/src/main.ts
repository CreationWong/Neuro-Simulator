import './assets/main.css'
import './assets/fonts.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

// Locales
import en from './locales/en.json'
import zh from './locales/zh.json'

import App from './App.vue'
import router from './router'

// I18n
const i18n = createI18n({
  legacy: false, // Use Composition API
  locale: navigator.language.startsWith('zh') ? 'zh' : 'en', // Default language
  fallbackLocale: 'en', // Fallback language
  messages: {
    en,
    zh
  }
});

const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)
app.use(i18n)

app.mount('#app')