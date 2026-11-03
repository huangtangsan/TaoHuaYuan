/** 把后端的图标来源标识翻译成中文，用于后台提示。 */
const LABELS: Record<string, string> = {
  'link:icon': '站点 icon 声明',
  'link:apple-touch-icon': 'apple-touch-icon',
  'link:mask-icon': 'mask-icon',
  manifest: 'manifest 图标',
  'meta:tile-image': 'Windows 磁贴图',
  'meta:og:image': '分享图',
  'meta:og:image:url': '分享图',
  'meta:twitter:image': '分享图',
  'img:logo': '页面 logo',
  'guess:favicon.ico': 'favicon.ico',
  'guess:dir-favicon.ico': '子目录 favicon.ico',
  'guess:favicon.svg': 'favicon.svg',
  'guess:apple-touch-icon.png': 'apple-touch-icon.png',
  'service:mirror': '图标镜像',
  letter: '首字母占位图',
  default: '默认图',
}

/** 这两个来源都不是站点真实图标，后台按"未找到图标"处理。 */
export function isFallbackIcon(source?: string): boolean {
  return source === 'default' || source === 'letter'
}

export function iconSourceLabel(source?: string): string {
  if (!source) return '未知来源'
  return LABELS[source] ?? source
}
