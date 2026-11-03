import { client } from './client'

/** 后端把 logo 存成纯 base64（不含 data: 前缀） */
export interface Site {
  id: number
  icon: string
  title: string
  url: string
  category: string
  category_id: number
  description: string
  is_used: boolean
  sort: number
  created_at: string
  updated_at: string
}

export interface SiteListParams {
  page: number
  page_size: number
  search?: string
  category_id?: number | null
}

export interface SiteListResult {
  list: Site[]
  pagination: {
    total: number
    current_page: number
    per_page_count: number
  }
}

export async function listSites(params: SiteListParams): Promise<SiteListResult> {
  const { data } = await client.get<SiteListResult>('/admin/site', { params })
  return { list: data.list ?? [], pagination: data.pagination }
}

export interface SiteCreatePayload {
  category_id: number | null
  /** 多行文本，一行一个 URL */
  url: string
  is_used: boolean
  fail_switch: boolean
}

export interface SiteCreateResult {
  successCount: number
  failCount: number
  failURLs: string[]
  /** 每个 URL 实际使用的图标来源，例如 img:logo / manifest / service:mirror / default */
  iconSources?: Record<string, string>
}

export async function createSites(payload: SiteCreatePayload): Promise<SiteCreateResult> {
  const { data } = await client.post<SiteCreateResult>('/admin/site', payload)
  return data
}

export interface SiteUpdatePayload {
  id: number
  title?: string
  url?: string
  description?: string
  category_id?: number
  sort?: number
  is_used?: boolean
  /** Logo 图片链接，后端会下载并转成 base64 */
  thumb?: string
  /** 直接上传的 logo 文件，优先于 thumb */
  file?: File
}

export async function updateSite(payload: SiteUpdatePayload): Promise<void> {
  const form = new FormData()
  form.append('id', String(payload.id))
  if (payload.title !== undefined) form.append('title', payload.title)
  if (payload.url !== undefined) form.append('url', payload.url)
  if (payload.description !== undefined) form.append('description', payload.description)
  if (payload.category_id !== undefined) form.append('category_id', String(payload.category_id))
  if (payload.sort !== undefined) form.append('sort', String(payload.sort))
  if (payload.is_used !== undefined) form.append('is_used', String(payload.is_used))
  if (payload.thumb) form.append('thumb', payload.thumb)
  if (payload.file) form.append('file', payload.file)

  await client.put(`/admin/site/${payload.id}`, form)
}

export interface SiteSyncResult {
  id: number
  /** 图标来源，default 表示没有可用图标，已回退占位图 */
  icon_source?: string
}

export async function syncSite(id: number): Promise<SiteSyncResult> {
  const { data } = await client.get<SiteSyncResult>(`/admin/site/sync/${id}`)
  return data
}

export interface SitePreviewResult {
  title: string
  description: string
  icon: string
  icon_source: string
}

/** 只抓取不落库，用于后台表单里预览图标 */
export async function previewSite(url: string): Promise<SitePreviewResult> {
  const { data } = await client.get<SitePreviewResult>('/admin/site/preview', { params: { url } })
  return data
}

export async function deleteSite(id: number): Promise<void> {
  await client.delete(`/admin/site/${id}`)
}

/** 导出依赖 cookie 鉴权，交给浏览器直接下载 */
export function exportUrl(params: { search?: string; category_id?: number | null }): string {
  const query = new URLSearchParams()
  if (params.search) query.set('search', params.search)
  if (params.category_id) query.set('category_id', String(params.category_id))
  const suffix = query.toString()
  return `/api/admin/site/export${suffix ? `?${suffix}` : ''}`
}
