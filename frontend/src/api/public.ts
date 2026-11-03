import { client } from './client'

export interface PublicConfig {
  id: number
  is_about: boolean
  is_search: boolean
  site_title: string
  site_keyword: string
  site_desc: string
  site_record: string
  site_logo: string
  site_favicon: string
  site_url: string
}

export interface PublicCategory {
  id: number
  parent_id: number
  name: string
  icon: string
  level: number
  sort: number
}

export interface PublicSite {
  id: number
  category_id: number
  title: string
  url: string
  description: string
  icon: string
  sort: number
}

export interface HomeData {
  config: PublicConfig
  categories: PublicCategory[]
  sites: PublicSite[]
}

export interface AboutData {
  about_site: string
  about_author: string
  is_about: boolean
  site_title: string
  site_logo: string
}

export async function fetchHome(): Promise<HomeData> {
  const { data } = await client.get<HomeData>('/home')
  return data
}

export async function fetchAbout(): Promise<AboutData> {
  const { data } = await client.get<AboutData>('/about')
  return data
}
