import { zhCNMessages } from './messages.zh-CN'
import { enUSMessages } from './messages.en-US'

export const supportedLocales = ['zh-CN', 'en-US'] as const

export type AppLocale = (typeof supportedLocales)[number]

export const messages: Record<AppLocale, Record<string, string>> = {
  'zh-CN': zhCNMessages,
  'en-US': enUSMessages,
}
