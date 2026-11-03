import { imgSrc } from './img'

export interface MetaConfig {
  site_title: string
  site_keyword: string
  site_desc: string
  site_favicon: string
}

function upsertMeta(selector: string, attrs: Record<string, string>): void {
  let tag = document.head.querySelector<HTMLMetaElement>(selector)
  if (!tag) {
    tag = document.createElement('meta')
    document.head.appendChild(tag)
  }
  Object.entries(attrs).forEach(([key, value]) => tag?.setAttribute(key, value))
}

function updateFavicon(value: string): void {
  const href = imgSrc(value) || '/favicon.ico'
  let link = document.head.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.href = href
}

export function applySiteMeta(config: MetaConfig): void {
  document.title = config.site_title || '桃花源 · 网址导航'
  if (config.site_keyword) {
    upsertMeta('meta[name="keywords"]', { name: 'keywords', content: config.site_keyword })
  }
  if (config.site_desc) {
    upsertMeta('meta[name="description"]', { name: 'description', content: config.site_desc })
  }
  updateFavicon(config.site_favicon)
}
